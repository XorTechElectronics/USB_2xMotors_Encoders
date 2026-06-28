"""
2-Motor USB CDC Control GUI with Encoder Readback and RPM Conversion

Cross-platform (Windows and Linux, including Raspberry Pi) Tkinter GUI
for controlling 2 motors, displaying live encoder counts read back over
the same USB CDC serial connection, and converting those counts to
output-shaft RPM using per-motor settings (pulses-per-revolution and
gear ratio) editable from a Settings window.

Linux / Raspberry Pi setup notes:
    - Install dependencies if needed:
          sudo apt install python3-tk
          pip3 install pyserial
    - Serial port access requires the user to be in the 'dialout' group:
          sudo usermod -aG dialout $USER
      (log out and back in for this to take effect)
    - USB CDC devices typically appear as /dev/ttyACM0 or /dev/ttyUSB0
      (compared to COMx on Windows)

Encoder read protocol:
    9-byte packets: [0xAA, m1_rpm_b0..b3, m2_rpm_b0..b3]
    Firmware sends RPM*10 as signed 32-bit little-endian per motor.

RPM conversion:
    output_shaft_RPM = (delta_counts / (PPR * gear_ratio)) * (60 / elapsed_sec)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import struct
import time
import json
import os
import math

NUM_MOTORS = 2

# Settings file lives next to this script so it travels with it.
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motor_config.json")

# Known (VID, PID) pairs for the motor controller's USB CDC interface.
KNOWN_VID_PID = [
    (0x04D8, 0x0B15),
]

# --- Encoder packet format ---
ENCODER_HEADER      = 0xAA
ENCODER_PACKET_SIZE = 14   # header(1) + M1_rpm(4) + M2_rpm(4) + sync_err(4) + sync_enabled(1)
RAW_VALUE_RANGE     = 4294967296             # 2**32 for int32 wraparound

# How often the GUI checks for newly-arrived encoder data.
POLL_INTERVAL_MS  = 50   # ~20Hz
POLL_INTERVAL_SEC = POLL_INTERVAL_MS / 1000.0

# If no encoder packet arrives for this long, live RPM labels are blanked.
STALE_TIMEOUT_SEC = 0.5

# Reading mode — firmware sends RPM*10 directly.
READING_MODE_ABSOLUTE = "absolute"
READING_MODE_DELTA    = "delta"
READING_MODE_RPM_X10  = "rpm_x10"
READING_MODE          = READING_MODE_RPM_X10


def printHex(data):
    return ' '.join(f'{c:0>2X}' for c in data)


# ----------------------------------------------------------------------
# Per-motor configuration with JSON persistence
# ----------------------------------------------------------------------

DEFAULT_PPR              = 14
DEFAULT_GEAR_RATIO       = 50.0
DEFAULT_MAX_MOTOR_RPM    = 6000.0
DEFAULT_WHEEL_DIAMETER   = 0.0
DEFAULT_KP               = 0.5
DEFAULT_KI               = 0.1
DEFAULT_KD               = 0.05
DEFAULT_INTEGRAL_LIMIT   = 255.0
DEFAULT_MAX_PWM_STEP     = 10
DEFAULT_DEBUG_ENABLED    = False
DEFAULT_ENCODER_INVERTED = False


def default_motor_config():
    return {
        str(m): {
            "ppr":               DEFAULT_PPR,
            "gear_ratio":        DEFAULT_GEAR_RATIO,
            "max_motor_rpm":     DEFAULT_MAX_MOTOR_RPM,
            "wheel_diameter_mm": DEFAULT_WHEEL_DIAMETER,
            "kp":                DEFAULT_KP,
            "ki":                DEFAULT_KI,
            "kd":                DEFAULT_KD,
            "integral_limit":    DEFAULT_INTEGRAL_LIMIT,
            "max_pwm_step":      DEFAULT_MAX_PWM_STEP,
            "debug_enabled":     DEFAULT_DEBUG_ENABLED,
            "encoder_inverted":  DEFAULT_ENCODER_INVERTED,
        }
        for m in range(1, NUM_MOTORS + 1)
    }


def _coerce_positive(value, default):
    try:
        v = float(value)
        return v if v > 0 else default
    except (TypeError, ValueError):
        return default


def _coerce_nonneg(value, default):
    try:
        v = float(value)
        return v if v >= 0 else default
    except (TypeError, ValueError):
        return default


def load_motor_config():
    config = default_motor_config()
    if not os.path.exists(CONFIG_PATH):
        return config
    try:
        with open(CONFIG_PATH, "r") as f:
            loaded = json.load(f)
        for motor_key, defaults in config.items():
            entry = loaded.get(motor_key, {})
            config[motor_key] = {
                "ppr":               _coerce_positive(entry.get("ppr"),               defaults["ppr"]),
                "gear_ratio":        _coerce_positive(entry.get("gear_ratio"),        defaults["gear_ratio"]),
                "max_motor_rpm":     _coerce_positive(entry.get("max_motor_rpm"),     defaults["max_motor_rpm"]),
                "wheel_diameter_mm": _coerce_nonneg  (entry.get("wheel_diameter_mm"), defaults["wheel_diameter_mm"]),
                "kp":                _coerce_nonneg  (entry.get("kp"),                defaults["kp"]),
                "ki":                _coerce_nonneg  (entry.get("ki"),                defaults["ki"]),
                "kd":                _coerce_nonneg  (entry.get("kd"),                defaults["kd"]),
                "integral_limit":    _coerce_positive(entry.get("integral_limit"),    defaults["integral_limit"]),
                "max_pwm_step":      int(_coerce_positive(entry.get("max_pwm_step"),  defaults["max_pwm_step"])),
                "debug_enabled":     bool(entry.get("debug_enabled",                  defaults["debug_enabled"])),
                "encoder_inverted":  bool(entry.get("encoder_inverted",               defaults["encoder_inverted"])),
            }
    except (json.JSONDecodeError, OSError):
        pass
    return config


def save_motor_config(config):
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except OSError:
        return False


# ----------------------------------------------------------------------
# Serial reader thread
# ----------------------------------------------------------------------

DEBUG_HEADER      = 0xBB
DEBUG_PACKET_SIZE = 27  # 0xBB + motor_id + 6×float + uint8 pwm


class SerialReader(threading.Thread):
    def __init__(self, serial_port, data_queue, debug_queues=None):
        super().__init__(daemon=True)
        self.serial_port  = serial_port
        self.data_queue   = data_queue
        self.debug_queues = debug_queues or {}  # {motor_id: queue.Queue}
        self._stop_event  = threading.Event()
        self._buffer      = bytearray()

    def stop(self):
        self._stop_event.set()

    def run(self):
        while not self._stop_event.is_set():
            try:
                if not (self.serial_port and self.serial_port.is_open):
                    time.sleep(0.05)
                    continue
                waiting = self.serial_port.in_waiting
                chunk = self.serial_port.read(waiting if waiting else 1)
                if chunk:
                    self._buffer.extend(chunk)
                    self._try_parse_packets()
                else:
                    time.sleep(0.005)
            except serial.SerialException:
                break
            except Exception:
                self._buffer.clear()
                time.sleep(0.01)

    def _try_parse_packets(self):
        while True:
            if not self._buffer:
                return

            # Look for either known header
            aa_idx = self._buffer.find(bytes([ENCODER_HEADER]))
            bb_idx = self._buffer.find(bytes([DEBUG_HEADER]))

            # Find the nearest valid header
            if aa_idx == -1 and bb_idx == -1:
                self._buffer.clear()
                return

            if aa_idx == -1:
                next_idx = bb_idx
            elif bb_idx == -1:
                next_idx = aa_idx
            else:
                next_idx = min(aa_idx, bb_idx)

            # Discard garbage bytes before the header
            if next_idx > 0:
                del self._buffer[:next_idx]

            header = self._buffer[0]

            if header == ENCODER_HEADER:
                if len(self._buffer) < ENCODER_PACKET_SIZE:
                    return
                packet = bytes(self._buffer[:ENCODER_PACKET_SIZE])
                del self._buffer[:ENCODER_PACKET_SIZE]
                try:
                    # bytes 1-4: M1 RPM*10, 5-8: M2 RPM*10, 9-12: sync_err, 13: sync_on
                    rpm1, rpm2, sync_err = struct.unpack('<3l', packet[1:13])
                    sync_on = packet[13] != 0
                except struct.error:
                    continue
                encoder_values = {1: rpm1, 2: rpm2}
                self.data_queue.put((time.monotonic(), encoder_values,
                                     sync_err, sync_on))

            elif header == DEBUG_HEADER:
                if len(self._buffer) < DEBUG_PACKET_SIZE:
                    return
                packet = bytes(self._buffer[:DEBUG_PACKET_SIZE])
                del self._buffer[:DEBUG_PACKET_SIZE]
                try:
                    motor_id = packet[1]
                    setpoint, measured, error, p_term, i_term, d_term = \
                        struct.unpack('<6f', packet[2:26])
                    pwm = packet[26]
                    debug_data = {
                        "motor_id": motor_id,
                        "setpoint": setpoint,
                        "measured": measured,
                        "error":    error,
                        "p_term":   p_term,
                        "i_term":   i_term,
                        "d_term":   d_term,
                        "pwm":      pwm,
                    }
                    if motor_id in self.debug_queues:
                        self.debug_queues[motor_id].put(debug_data)
                except struct.error:
                    continue
            else:
                # Unknown header byte — discard and keep scanning
                del self._buffer[:1]


# ----------------------------------------------------------------------
# Motor control panel
# ----------------------------------------------------------------------

class Tooltip:
    """Simple hover tooltip for any Tkinter widget."""
    def __init__(self, widget, text):
        self.widget  = widget
        self.text    = text
        self._tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self._tip_window:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self._tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # no window decorations
        tw.wm_geometry(f"+{x}+{y}")
        ttk.Label(tw, text=self.text, justify="left",
                  background="#ffffe0", relief="solid", borderwidth=1,
                  font=("TkDefaultFont", 9),
                  wraplength=280).pack(padx=4, pady=3)

    def _hide(self, event=None):
        if self._tip_window:
            self._tip_window.destroy()
            self._tip_window = None


class MotorControlPanel(ttk.Frame):
    """
    Per-motor control panel with three display tiers:
      1. Motor shaft RPM  (raw from firmware)
      2. Output shaft RPM (÷ gear ratio) with PID setpoint
      3. Velocity m/s     (× wheel circumference) with PID setpoint

    Each tier shows live value + avg/min/max stats.
    Enabling one PID tier automatically disables the other.
    Velocity tier is greyed out when wheel diameter = 0 in Settings.
    """

    RPM_WINDOW_SIZE = 20  # ~2 seconds of smoothing at 10Hz

    def __init__(self, parent, motor_id, send_command_cb, send_config_cb=None):
        super().__init__(parent, relief="groove", borderwidth=2)
        self.motor_id     = motor_id
        self.send_command = send_command_cb
        self.send_config  = send_config_cb
        self.debug_queue  = queue.Queue()

        # Motor state
        self.motor_in1 = 0
        self.motor_in2 = 0
        self.motor_pwm = 0
        self.speed_var = tk.IntVar()

        # PID state
        self.output_pid_enabled   = False
        self.velocity_pid_enabled = False

        # Current config (updated by GUI when settings change)
        self.cfg = {
            "gear_ratio":        DEFAULT_GEAR_RATIO,
            "max_motor_rpm":     DEFAULT_MAX_MOTOR_RPM,
            "wheel_diameter_mm": DEFAULT_WHEEL_DIAMETER,
        }

        # Stats storage per tier
        self._shaft_window  = []; self._shaft_min  = None; self._shaft_max  = None
        self._output_window = []; self._output_min = None; self._output_max = None
        self._vel_window    = []; self._vel_min    = None; self._vel_max    = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        CC = 4
        for c in range(CC):
            self.columnconfigure(c, weight=1)
        row = 0

        # ── Header: Motor title + Tests button ────────────────────────
        header = ttk.Frame(self)
        header.grid(row=row, column=0, columnspan=CC, sticky="ew")
        header.columnconfigure(0, weight=1)
        ttk.Label(header, text=f"Motor {self.motor_id}",
                  font=("TkDefaultFont", 12, "bold"),
                  anchor="center").grid(row=0, column=0, padx=8, pady=6, sticky="ew")
        self.btn_tests = ttk.Button(header, text="Tests ▶",
                                    command=self._open_tests, width=8)
        self.btn_tests.grid(row=0, column=1, padx=(0, 6), pady=4)
        self._tests_window = None
        row += 1

        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=CC, sticky="ew")
        row += 1

        # ── Manual controls ───────────────────────────────────────────
        ttk.Label(self, text="Speed").grid(row=row, column=0, columnspan=CC, pady=(6, 0))
        row += 1

        self.speed_slider = ttk.Scale(
            self, from_=0, to=255, orient="horizontal",
            variable=self.speed_var, command=self.on_speed_change)
        self.speed_slider.grid(row=row, column=0, columnspan=CC, padx=10, sticky="ew")
        row += 1

        self.btn_ccw   = ttk.Button(self, text="CCW",   style="Dir.TButton",   command=self.set_CCW)
        self.btn_cw    = ttk.Button(self, text="CW",    style="Dir.TButton",   command=self.set_CW)
        self.btn_stop  = ttk.Button(self, text="Stop",  style="Stop.TButton",  command=self.stop_motor)
        self.btn_brake = ttk.Button(self, text="Brake", style="Brake.TButton", command=self.brake_motor)
        self.btn_ccw  .grid(row=row, column=0, pady=4, sticky="ew")
        self.btn_cw   .grid(row=row, column=1, pady=4, sticky="ew")
        self.btn_stop .grid(row=row, column=2, pady=4, sticky="ew")
        self.btn_brake.grid(row=row, column=3, pady=4, sticky="ew")
        row += 1

        # ── Tier 1: Motor Shaft RPM ───────────────────────────────────
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=CC, sticky="ew", pady=(8, 4))
        row += 1

        ttk.Label(self, text="MOTOR SHAFT RPM",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=row, column=0, columnspan=CC - 1, sticky="w", padx=6)
        self.direction_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.direction_var,
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=row, column=CC - 1, sticky="e", padx=6)
        row += 1

        self.shaft_rpm_var = tk.StringVar(value="--")
        ttk.Label(self, textvariable=self.shaft_rpm_var,
                  font=("TkDefaultFont", 18, "bold")).grid(
            row=row, column=0, columnspan=CC, pady=(0, 2))
        row += 1

        row = self._build_stats_row(row, CC, "shaft", "steelblue", "firebrick")

        # ── Tier 2: Output Shaft RPM ──────────────────────────────────
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=CC, sticky="ew", pady=(8, 4))
        row += 1

        ttk.Label(self, text="OUTPUT SHAFT RPM",
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=row, column=0, columnspan=CC, sticky="w", padx=6)
        row += 1

        self.output_rpm_var = tk.StringVar(value="--")
        ttk.Label(self, textvariable=self.output_rpm_var,
                  font=("TkDefaultFont", 14, "bold")).grid(
            row=row, column=0, columnspan=CC, pady=(0, 2))
        row += 1

        row = self._build_stats_row(row, CC, "output", "steelblue", "firebrick")

        self.output_sp_var = tk.DoubleVar(value=0.0)
        self.output_sp_slider = ttk.Scale(
            self, from_=0, to=150, orient="horizontal",
            variable=self.output_sp_var, command=self._on_output_sp_slider)
        self.output_sp_slider.grid(
            row=row, column=0, columnspan=CC - 1, padx=(6, 2), sticky="ew")

        self.output_sp_entry_var = tk.StringVar(value="0.0")
        output_sp_entry = ttk.Entry(
            self, textvariable=self.output_sp_entry_var, width=7, justify="center")
        output_sp_entry.grid(row=row, column=CC - 1, padx=(2, 6), sticky="ew")
        output_sp_entry.bind("<Return>",   self._on_output_sp_entry)
        output_sp_entry.bind("<FocusOut>", self._on_output_sp_entry)
        row += 1

        ttk.Label(self, text="RPM setpoint", foreground="gray").grid(
            row=row, column=0, columnspan=CC - 1, sticky="w", padx=6)
        self.btn_output_pid = ttk.Button(
            self, text="Enable PID", command=self.toggle_output_pid)
        self.btn_output_pid.grid(
            row=row, column=CC - 1, padx=6, pady=(2, 4), sticky="ew")
        row += 1

        # ── Tier 3: Velocity ──────────────────────────────────────────
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=CC, sticky="ew", pady=(8, 4))
        row += 1

        self.vel_header_var = tk.StringVar(value="VELOCITY")
        ttk.Label(self, textvariable=self.vel_header_var,
                  font=("TkDefaultFont", 9, "bold")).grid(
            row=row, column=0, columnspan=CC, sticky="w", padx=6)
        row += 1

        self.vel_var = tk.StringVar(value="--")
        ttk.Label(self, textvariable=self.vel_var,
                  font=("TkDefaultFont", 14, "bold")).grid(
            row=row, column=0, columnspan=CC, pady=(0, 2))
        row += 1

        row = self._build_stats_row(row, CC, "vel", "steelblue", "firebrick")

        self.vel_sp_var = tk.DoubleVar(value=0.0)
        self.vel_sp_slider = ttk.Scale(
            self, from_=0, to=5.0, orient="horizontal",
            variable=self.vel_sp_var, command=self._on_vel_sp_slider)
        self.vel_sp_slider.grid(
            row=row, column=0, columnspan=CC - 1, padx=(6, 2), sticky="ew")

        self.vel_sp_entry_var = tk.StringVar(value="0.000")
        vel_sp_entry = ttk.Entry(
            self, textvariable=self.vel_sp_entry_var, width=7, justify="center")
        vel_sp_entry.grid(row=row, column=CC - 1, padx=(2, 6), sticky="ew")
        vel_sp_entry.bind("<Return>",   self._on_vel_sp_entry)
        vel_sp_entry.bind("<FocusOut>", self._on_vel_sp_entry)
        row += 1

        ttk.Label(self, text="m/s setpoint", foreground="gray").grid(
            row=row, column=0, columnspan=CC - 1, sticky="w", padx=6)
        self.btn_vel_pid = ttk.Button(
            self, text="Enable PID", command=self.toggle_velocity_pid)
        self.btn_vel_pid.grid(
            row=row, column=CC - 1, padx=6, pady=(2, 4), sticky="ew")
        row += 1

        self.vel_hint_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.vel_hint_var, foreground="gray").grid(
            row=row, column=0, columnspan=CC, padx=6, pady=(0, 4))
        row += 1

        # ── PID Tuning ───────────────────────────────────────────────
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=CC, sticky="ew", pady=(4, 4))
        row += 1

        self.btn_pid_tune = ttk.Button(
            self, text=f"⚙ PID Tuning — Motor {self.motor_id}",
            command=self._open_pid_tuning)
        self.btn_pid_tune.grid(
            row=row, column=0, columnspan=CC, padx=6, pady=(0, 4), sticky="ew")
        row += 1
        self._pid_tuning_window = None

        # ── Cumulative distance + reset ───────────────────────────────
        ttk.Separator(self, orient="horizontal").grid(
            row=row, column=0, columnspan=CC, sticky="ew", pady=(6, 4))
        row += 1

        ttk.Label(self, text="Distance (m)").grid(
            row=row, column=0, columnspan=CC - 1, sticky="w", padx=6)
        ttk.Button(self, text="Reset Stats", command=self.reset_stats).grid(
            row=row, column=CC - 1, padx=6, sticky="ew")
        row += 1

        self._total_distance_m = 0.0
        self.total_distance_var = tk.StringVar(value="0.000")
        ttk.Label(self, textvariable=self.total_distance_var,
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=row, column=0, columnspan=CC, pady=(0, 4))
        row += 1

        # Status / warning line — general motor status shown at the
        # bottom of the panel so it doesn't disrupt the tier layout.
        self.pid_warning_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.pid_warning_var,
                  foreground="orange").grid(
            row=row, column=0, columnspan=CC, padx=6, pady=(0, 6))

        self._refresh_velocity_state()

    def _build_stats_row(self, row, cols, prefix, min_fg, max_fg):
        f = ttk.Frame(self)
        f.grid(row=row, column=0, columnspan=cols, sticky="ew", padx=4, pady=(0, 2))
        for c in range(3):
            f.columnconfigure(c, weight=1)

        avg_var = tk.StringVar(value="--")
        min_var = tk.StringVar(value="--")
        max_var = tk.StringVar(value="--")
        setattr(self, f"_{prefix}_avg_var", avg_var)
        setattr(self, f"_{prefix}_min_var", min_var)
        setattr(self, f"_{prefix}_max_var", max_var)

        ttk.Label(f, text="Avg", anchor="center").grid(row=0, column=0, sticky="ew")
        ttk.Label(f, text="Min", anchor="center").grid(row=0, column=1, sticky="ew")
        ttk.Label(f, text="Max", anchor="center").grid(row=0, column=2, sticky="ew")
        ttk.Label(f, textvariable=avg_var, anchor="center",
                  font=("TkDefaultFont", 9, "bold")).grid(row=1, column=0, sticky="ew")
        ttk.Label(f, textvariable=min_var, anchor="center",
                  font=("TkDefaultFont", 9, "bold"),
                  foreground=min_fg).grid(row=1, column=1, sticky="ew")
        ttk.Label(f, textvariable=max_var, anchor="center",
                  font=("TkDefaultFont", 9, "bold"),
                  foreground=max_fg).grid(row=1, column=2, sticky="ew")
        return row + 1

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def apply_config(self, cfg):
        self.cfg = cfg
        max_output = cfg["max_motor_rpm"] / max(cfg["gear_ratio"], 0.001)
        self.output_sp_slider.configure(to=max_output)
        wheel = cfg["wheel_diameter_mm"]
        if wheel > 0:
            circ = math.pi * wheel / 1000.0
            max_vel = max_output / 60.0 * circ
            self.vel_sp_slider.configure(to=round(max_vel + 0.5, 1))
        self._refresh_velocity_state()

    def _refresh_velocity_state(self):
        wheel = self.cfg.get("wheel_diameter_mm", 0.0)
        has_wheel = wheel > 0
        state = "normal" if has_wheel else "disabled"
        self.vel_sp_slider.configure(state=state)
        self.btn_vel_pid.configure(state=state)
        if has_wheel:
            self.vel_header_var.set(f"VELOCITY  ({wheel:.0f}mm wheel)")
            self.vel_hint_var.set("")
        else:
            self.vel_header_var.set("VELOCITY")
            self.vel_hint_var.set("Set wheel diameter in Settings to enable")

    # ------------------------------------------------------------------
    # Motor controls — defined once only
    # ------------------------------------------------------------------

    def on_speed_change(self, val):
        self.motor_pwm = int(float(val))
        self.send_command()

    def reset_direction_styles(self):
        self.btn_cw   .configure(style="Dir.TButton")
        self.btn_ccw  .configure(style="Dir.TButton")
        self.btn_stop .configure(style="Stop.TButton")
        self.btn_brake.configure(style="Brake.TButton")

    def set_CCW(self):
        self.motor_in1 = 0; self.motor_in2 = 1
        self.reset_direction_styles()
        self.btn_ccw.configure(style="ActiveDir.TButton")
        self._update_pid_buttons()
        self.send_command()

    def set_CW(self):
        self.motor_in1 = 1; self.motor_in2 = 0
        self.reset_direction_styles()
        self.btn_cw.configure(style="ActiveDir.TButton")
        self._update_pid_buttons()
        self.send_command()

    def stop_motor(self):
        self.motor_in1 = 0; self.motor_in2 = 0
        self.reset_direction_styles()
        self.btn_stop.configure(style="ActiveStop.TButton")
        self._update_pid_buttons()
        self.on_motor_stop()
        self.send_command()

    def brake_motor(self):
        self.motor_in1 = 1; self.motor_in2 = 1
        self.reset_direction_styles()
        self.btn_brake.configure(style="ActiveBrake.TButton")
        self._update_pid_buttons()
        self.on_motor_stop()
        self.send_command()

    def on_motor_stop(self):
        """Called when stop or brake is pressed — GUI hooks this to
        stop Motor 2 when sync is active."""
        pass  # overridden by MotorControlGUI after panel creation

    # ------------------------------------------------------------------
    # PID setpoint controls
    # ------------------------------------------------------------------

    def _output_sp_rpm(self):
        try:
            return float(self.output_sp_entry_var.get())
        except ValueError:
            return 0.0

    def _vel_sp_ms(self):
        try:
            return float(self.vel_sp_entry_var.get())
        except ValueError:
            return 0.0

    def on_setpoint_change(self):
        """Called when this panel's setpoint changes — GUI hooks this
        to mirror Motor 1 setpoint to Motor 2 when sync is active."""
        pass  # overridden by MotorControlGUI after panel creation

    def motor_shaft_setpoint(self):
        """Return motor shaft RPM setpoint for firmware.
        Converts from whichever tier's PID is active.
        Always returns a non-negative float."""
        gear  = self.cfg.get("gear_ratio", 1.0)
        wheel = self.cfg.get("wheel_diameter_mm", 0.0)

        if self.output_pid_enabled:
            sp = self._output_sp_rpm() * gear
            sp = max(0.0, sp)
            print(f"M{self.motor_id} output PID: {self._output_sp_rpm():.1f} output RPM -> {sp:.1f} motor shaft RPM")
            return sp

        if self.velocity_pid_enabled and wheel > 0:
            circ = math.pi * wheel / 1000.0
            if circ <= 0:
                return 0.0
            vel = self._vel_sp_ms()
            output_rpm = vel / circ * 60.0
            sp = max(0.0, output_rpm * gear)
            print(f"M{self.motor_id} velocity PID: {vel:.3f} m/s -> {output_rpm:.1f} output RPM -> {sp:.1f} motor shaft RPM")
            return sp

        return 0.0

    def _on_output_sp_slider(self, val):
        v = round(float(val), 1)
        self.output_sp_entry_var.set(f"{v:.1f}")
        self.output_sp_var.set(v)
        self.on_setpoint_change()
        if self.output_pid_enabled:
            self.velocity_pid_enabled = False
            self._update_pid_buttons()
            self.send_command()

    def _on_output_sp_entry(self, event=None):
        try:
            v = float(self.output_sp_entry_var.get())
            v = max(0.0, min(v, self.output_sp_slider.cget("to")))
            self.output_sp_entry_var.set(f"{v:.1f}")
            self.output_sp_var.set(v)
            self.on_setpoint_change()
            if self.output_pid_enabled:
                self.velocity_pid_enabled = False
                self._update_pid_buttons()
                self.send_command()
        except ValueError:
            pass

    def _on_vel_sp_slider(self, val):
        v = float(val)
        self.vel_sp_entry_var.set(f"{v:.3f}")
        self.vel_sp_var.set(v)
        self.on_setpoint_change()
        if self.velocity_pid_enabled:
            self.output_pid_enabled = False
            self._update_pid_buttons()
            self.send_command()

    def _on_vel_sp_entry(self, event=None):
        try:
            v = float(self.vel_sp_entry_var.get())
            v = max(0.0, min(v, self.vel_sp_slider.cget("to")))
            self.vel_sp_entry_var.set(f"{v:.3f}")
            self.vel_sp_var.set(v)
            self.on_setpoint_change()
            if self.velocity_pid_enabled:
                self.output_pid_enabled = False
                self._update_pid_buttons()
                self.send_command()
        except ValueError:
            pass

    def toggle_output_pid(self):
        self.output_pid_enabled = not self.output_pid_enabled
        if self.output_pid_enabled:
            self.velocity_pid_enabled = False
        else:
            self.speed_var.set(128)
            self.motor_pwm = 128
        self._update_pid_buttons()
        self.on_pid_change()
        self.send_command()

    def toggle_velocity_pid(self):
        self.velocity_pid_enabled = not self.velocity_pid_enabled
        if self.velocity_pid_enabled:
            self.output_pid_enabled = False
        else:
            self.speed_var.set(128)
            self.motor_pwm = 128
        self._update_pid_buttons()
        self.on_pid_change()
        self.send_command()

    def on_pid_change(self):
        """Called when PID is enabled/disabled — GUI hooks this to
        lock direction controls during sync."""
        pass  # overridden by MotorControlGUI after panel creation

    def _open_tests(self):
        """Open (or refocus) the motor tests window for this motor."""
        if (self._tests_window is not None and
                self._tests_window.winfo_exists()):
            self._tests_window.lift()
            self._tests_window.focus_set()
            return
        self._tests_window = MotorTestsWindow(
            self.winfo_toplevel(), self)

    def _open_pid_tuning(self):
        """Open (or refocus) the PID tuning window for this motor."""
        if (self._pid_tuning_window is not None and
                self._pid_tuning_window.winfo_exists()):
            self._pid_tuning_window.lift()
            self._pid_tuning_window.focus_set()
            return
        self._pid_tuning_window = PIDTuningWindow(
            self.winfo_toplevel(), self)

    def _update_pid_buttons(self):
        # Output PID button — green when active
        if self.output_pid_enabled:
            self.btn_output_pid.configure(
                text="Disable PID", style="ActiveDir.TButton")
        else:
            self.btn_output_pid.configure(
                text="Enable PID", style="TButton")

        # Velocity PID button — green when active
        if self.velocity_pid_enabled:
            self.btn_vel_pid.configure(
                text="Disable PID", style="ActiveDir.TButton")
        else:
            self.btn_vel_pid.configure(
                text="Enable PID", style="TButton")

        # Direction warning — shown whenever any PID is active
        # but no direction has been set (in1=0 and in2=0 = coast)
        pid_active = self.output_pid_enabled or self.velocity_pid_enabled
        no_direction = (self.motor_in1 == 0 and self.motor_in2 == 0)
        if pid_active and no_direction:
            self.pid_warning_var.set("⚠ Set direction (CW/CCW) to start PID")
        else:
            self.pid_warning_var.set("")

    # ------------------------------------------------------------------
    # Display update
    # ------------------------------------------------------------------

    def clear_live_rpm(self):
        self.shaft_rpm_var.set("--")
        self.output_rpm_var.set("--")
        self.vel_var.set("--")
        self.direction_var.set("")

    def reset_stats(self):
        for prefix in ("shaft", "output", "vel"):
            getattr(self, f"_{prefix}_window").clear()
            setattr(self, f"_{prefix}_min", None)
            setattr(self, f"_{prefix}_max", None)
            getattr(self, f"_{prefix}_avg_var").set("--")
            getattr(self, f"_{prefix}_min_var").set("--")
            getattr(self, f"_{prefix}_max_var").set("--")
        self._total_distance_m = 0.0
        self.total_distance_var.set("0.000")

    def reset_total_count(self):
        """Called on reconnect — resets distance accumulator."""
        self._total_distance_m = 0.0
        self.total_distance_var.set("0.000")

    def _update_stats(self, prefix, value):
        window = getattr(self, f"_{prefix}_window")
        window.append(value)
        if len(window) > self.RPM_WINDOW_SIZE:
            window.pop(0)
        mn = getattr(self, f"_{prefix}_min")
        mx = getattr(self, f"_{prefix}_max")
        mn = value if mn is None else min(mn, value)
        mx = value if mx is None else max(mx, value)
        setattr(self, f"_{prefix}_min", mn)
        setattr(self, f"_{prefix}_max", mx)
        avg = sum(window) / len(window)
        fmt = ".3f" if prefix == "vel" else ".1f"
        getattr(self, f"_{prefix}_avg_var").set(f"{avg:{fmt}}")
        getattr(self, f"_{prefix}_min_var").set(f"{mn:{fmt}}")
        getattr(self, f"_{prefix}_max_var").set(f"{mx:{fmt}}")

    def update_rpm(self, motor_shaft_rpm, gear_ratio, wheel_diameter_mm):
        rpm_abs = abs(motor_shaft_rpm)

        if motor_shaft_rpm > 0:
            self.direction_var.set("CW")
        elif motor_shaft_rpm < 0:
            self.direction_var.set("CCW")
        else:
            self.direction_var.set("stopped")

        # Tier 1 — motor shaft RPM
        self.shaft_rpm_var.set(f"{rpm_abs:.1f}")
        if rpm_abs > 0:
            self._update_stats("shaft", rpm_abs)

        # Tier 2 — output shaft RPM
        if gear_ratio > 0:
            output_rpm = rpm_abs / gear_ratio
            self.output_rpm_var.set(f"{output_rpm:.1f}")
            if rpm_abs > 0:
                self._update_stats("output", output_rpm)
        else:
            self.output_rpm_var.set("--")

        # Tier 3 — velocity and cumulative distance
        if wheel_diameter_mm > 0 and gear_ratio > 0:
            circ = math.pi * wheel_diameter_mm / 1000.0
            output_rpm = rpm_abs / gear_ratio
            vel = output_rpm / 60.0 * circ
            self.vel_var.set(f"{vel:.3f} m/s")
            if rpm_abs > 0:
                self._update_stats("vel", vel)
                # Accumulate distance: velocity × time per packet (100ms = 0.1s)
                self._total_distance_m += vel * 0.1
                self.total_distance_var.set(f"{self._total_distance_m:.3f}")
        else:
            self.vel_var.set("-- m/s")

    def update_encoder(self, delta_counts, ppr, gear_ratio, elapsed_sec):
        """Legacy absolute/delta mode update — kept for fallback."""
        counts_per_rev = ppr * gear_ratio
        if counts_per_rev <= 0:
            return
        revs = delta_counts / counts_per_rev
        rpm  = abs(revs) * (60.0 / elapsed_sec)
        sign = 1 if delta_counts >= 0 else -1
        self.update_rpm(rpm * sign, gear_ratio,
                        self.cfg.get("wheel_diameter_mm", 0.0))


# ----------------------------------------------------------------------
# Settings window
# ----------------------------------------------------------------------

class Sparkline(tk.Canvas):
    """Simple canvas-based sparkline for error history.
    Red above zero (positive error), blue below (negative error),
    dashed grey zero line. Works on Windows and Pi with no extra libs."""

    def __init__(self, parent, width=280, height=55, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg="#1e1e1e", highlightthickness=1,
                         highlightbackground="#444", **kwargs)
        self.w = width
        self.h = height

    def update(self, values):
        self.delete("all")
        if len(values) < 2:
            return
        mid = self.h // 2
        # Zero line
        self.create_line(0, mid, self.w, mid,
                         fill="#555", dash=(3, 4))
        scale = max(abs(v) for v in values)
        if scale == 0:
            self.create_text(self.w // 2, mid, text="stable",
                             fill="#888", font=("TkDefaultFont", 8))
            return
        n = len(values)
        pts = []
        for i, v in enumerate(values):
            x = int(i / (n - 1) * (self.w - 2)) + 1
            y = int(mid - (v / scale) * (mid - 4))
            y = max(2, min(self.h - 2, y))
            pts.extend([x, y])

        for i in range(0, len(pts) - 2, 2):
            x1, y1 = pts[i],   pts[i + 1]
            x2, y2 = pts[i + 2], pts[i + 3]
            v = values[i // 2]
            colour = "#cc4444" if v > 0 else ("#4488cc" if v < 0 else "#888")
            self.create_line(x1, y1, x2, y2, fill=colour, width=2)


class PIDTuningWindow(tk.Toplevel):
    """
    Per-motor PID tuning window showing:
    - Editable Kp/Ki/Kd/Integral Limit/PWM Slew Rate with explicit Apply
    - Live PID state from firmware debug packets (setpoint, measured, error)
    - P/I/D contribution bars showing what's driving PWM
    - 50-sample error sparkline
    - Suggestion engine based on recent history
    - Debug enable/disable (sends via config packet byte 20/21)
    """

    HISTORY_SIZE = 50  # ~5 seconds at 10Hz

    def __init__(self, parent, panel):
        super().__init__(parent)
        self.panel  = panel
        self.title(f"PID Tuning — Motor {panel.motor_id}")
        self.resizable(False, False)
        self.transient(parent)

        # History for suggestion engine
        self._history  = []
        self._run_start = None  # list of dicts from debug packets

        self._build_ui()
        self._enable_debug(True)

        # Poll debug queue
        self.after(100, self._poll_debug_queue)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        # ── Gains ─────────────────────────────────────────────────────
        gains_frame = ttk.LabelFrame(container, text="Gains")
        gains_frame.pack(fill="x", **pad)

        cfg = self.panel.cfg
        motor_key = str(self.panel.motor_id)

        fields = [
            ("Kp",             "kp",             "0.05"),
            ("Ki",             "ki",             "0.02"),
            ("Kd",             "kd",             "0.00"),
            ("Integral Limit", "integral_limit", "10000"),
            ("PWM Slew Rate",  "max_pwm_step",   "10"),
        ]

        self._gain_vars = {}
        for col, (label, key, fallback) in enumerate(fields):
            ttk.Label(gains_frame, text=label, anchor="center").grid(
                row=0, column=col, padx=6, pady=(4, 0), sticky="ew")
            val = self.panel.cfg.get(key, fallback)
            var = tk.StringVar(value=f"{val:g}" if isinstance(val, (int, float)) else str(val))
            ttk.Entry(gains_frame, textvariable=var, width=8,
                      justify="center").grid(
                row=1, column=col, padx=6, pady=(0, 4))
            self._gain_vars[key] = var
            gains_frame.columnconfigure(col, weight=1)

        self._gains_error_var = tk.StringVar(value="")
        ttk.Label(gains_frame, textvariable=self._gains_error_var,
                  foreground="red").grid(
            row=2, column=0, columnspan=len(fields), pady=(0, 2))

        ttk.Button(gains_frame, text="Apply Gains",
                   command=self._apply_gains).grid(
            row=3, column=0, columnspan=len(fields), pady=(0, 6))

        # ── Live PID state ────────────────────────────────────────────
        live_frame = ttk.LabelFrame(container, text="Live PID State")
        live_frame.pack(fill="x", **pad)
        live_frame.columnconfigure(1, weight=1)
        live_frame.columnconfigure(3, weight=1)

        self._live_vars = {}
        live_fields = [
            ("Setpoint",  "setpoint", "-- RPM",   0, 0),
            ("Measured",  "measured", "-- RPM",   0, 2),
            ("Error",     "error",    "--",        1, 0),
            ("PWM",       "pwm",      "-- / 255",  1, 2),
        ]
        for label, key, default, row, col in live_fields:
            ttk.Label(live_frame, text=label + ":").grid(
                row=row, column=col, sticky="e", padx=(8, 2), pady=3)
            var = tk.StringVar(value=default)
            ttk.Label(live_frame, textvariable=var,
                      font=("TkDefaultFont", 10, "bold")).grid(
                row=row, column=col + 1, sticky="w", padx=(0, 8))
            self._live_vars[key] = var

        # ── Contribution bars ─────────────────────────────────────────
        bars_frame = ttk.LabelFrame(container, text="PID Contribution")
        bars_frame.pack(fill="x", **pad)
        bars_frame.columnconfigure(1, weight=1)

        self._bar_vars  = {}
        self._bar_canvases = {}
        for row_idx, (label, key, colour) in enumerate([
            ("P", "p_term", "#4488cc"),
            ("I", "i_term", "#44aa44"),
            ("D", "d_term", "#cc8844"),
            ("PWM", "pwm",  "#888888"),
        ]):
            ttk.Label(bars_frame, text=label, width=4, anchor="e").grid(
                row=row_idx, column=0, padx=(6, 2), pady=2)
            c = tk.Canvas(bars_frame, height=18, bg="#1e1e1e",
                          highlightthickness=0)
            c.grid(row=row_idx, column=1, sticky="ew", padx=(0, 4), pady=2)
            val_var = tk.StringVar(value="--")
            ttk.Label(bars_frame, textvariable=val_var, width=14,
                      anchor="w").grid(row=row_idx, column=2, padx=(0, 6))
            self._bar_canvases[key] = (c, colour)
            self._bar_vars[key] = val_var

        # ── Sparkline ─────────────────────────────────────────────────
        spark_frame = ttk.LabelFrame(
            container, text=f"Error History  ({self.HISTORY_SIZE} samples / 5s)")
        spark_frame.pack(fill="x", **pad)
        self._sparkline = Sparkline(spark_frame, width=380, height=60)
        self._sparkline.pack(padx=6, pady=6)

        # ── Run timer ─────────────────────────────────────────────────
        timer_frame = ttk.Frame(container)
        timer_frame.pack(fill="x", padx=8)
        self._run_start = None
        self._timer_var = tk.StringVar(value="Run time: --")
        ttk.Label(timer_frame, textvariable=self._timer_var,
                  foreground="gray").pack(side="left")
        ttk.Button(timer_frame, text="Reset Timer",
                   command=self._reset_timer).pack(side="right")

        # ── Suggestions ───────────────────────────────────────────────
        sugg_frame = ttk.LabelFrame(container, text="Tuning Suggestions")
        sugg_frame.pack(fill="x", **pad)
        sugg_frame.columnconfigure(0, weight=1)

        # Up to 4 suggestion rows: text label + optional Apply button
        self._sugg_rows = []
        for row_idx in range(4):
            text_var = tk.StringVar(value="")
            lbl = ttk.Label(sugg_frame, textvariable=text_var,
                            wraplength=300, justify="left")
            lbl.grid(row=row_idx, column=0, sticky="w", padx=8, pady=2)
            # Each button holds its own action reference directly,
            # updated when suggestions change — avoids race condition
            # where _update_suggestions rebuilds _sugg_rows between
            # the user clicking and the command firing.
            action_holder = [None]  # mutable container for current action
            btn = ttk.Button(sugg_frame, text="Apply",
                             command=lambda h=action_holder: h[0]() if h[0] else None)
            btn.grid(row=row_idx, column=1, padx=(4, 8), pady=2)
            btn.grid_remove()
            self._sugg_rows.append((text_var, btn, action_holder))

        # ── Bottom buttons ────────────────────────────────────────────
        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=(6, 0))
        ttk.Button(btn_frame, text="Apply Gains",
                   command=self._apply_gains).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Save Gains",
                   command=self._save_gains).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Export CSV",
                   command=self._export_csv).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Close",
                   command=self._on_close).pack(side="left", padx=5)

    # ------------------------------------------------------------------
    # Debug enable/disable
    # ------------------------------------------------------------------

    def _enable_debug(self, enabled):
        if self.panel.send_config:
            self.panel.send_config(self.panel.motor_id, debug_enabled=enabled)

    # ------------------------------------------------------------------
    # Gains apply / save
    # ------------------------------------------------------------------

    def _parse_gains(self):
        """Parse gain fields, return dict or None on error."""
        result = {}
        validations = {
            "kp":             ("Kp",             "nonneg"),
            "ki":             ("Ki",             "nonneg"),
            "kd":             ("Kd",             "nonneg"),
            "integral_limit": ("Integral Limit", "positive"),
            "max_pwm_step":   ("PWM Slew Rate",  "positive_int"),
        }
        for key, (label, rule) in validations.items():
            try:
                v = float(self._gain_vars[key].get())
                if rule == "positive" and v <= 0:
                    raise ValueError
                if rule == "positive_int" and (v <= 0 or v != int(v)):
                    raise ValueError
                if rule == "nonneg" and v < 0:
                    raise ValueError
                result[key] = int(v) if rule == "positive_int" else v
            except ValueError:
                self._gains_error_var.set(
                    f"{label}: must be a {'positive integer' if rule == 'positive_int' else 'valid number'}.")
                return None
        self._gains_error_var.set("")
        return result

    def _apply_gains(self):
        """Send updated gains to firmware immediately without saving to disk."""
        gains = self._parse_gains()
        if gains is None:
            return
        # Update panel's local cfg
        merged = dict(self.panel.cfg)
        merged.update(gains)
        self.panel.cfg = merged

        # Also update the GUI's master motor_config so send_motor_config
        # reads the new values (it reads from motor_config, not panel.cfg)
        app = self._get_app()
        if app:
            motor_key = str(self.panel.motor_id)
            app.motor_config[motor_key].update(gains)

        if self.panel.send_config:
            self.panel.send_config(self.panel.motor_id, debug_enabled=True)

    def _save_gains(self):
        """Apply gains and persist to motor_config.json."""
        gains = self._parse_gains()
        if gains is None:
            return
        motor_key = str(self.panel.motor_id)
        # Get the GUI's motor_config via the top-level app reference
        app = self._get_app()
        if app:
            app.motor_config[motor_key].update(gains)
            save_motor_config(app.motor_config)
            self.panel.apply_config(app.motor_config[motor_key])
            if self.panel.send_config:
                self.panel.send_config(self.panel.motor_id, debug_enabled=True)
            self._gains_error_var.set("✓ Saved")
            self.after(2000, lambda: self._gains_error_var.set(""))

    def _get_app(self):
        """Walk up the widget tree to find MotorControlGUI instance."""
        w = self.master
        while w is not None:
            if isinstance(w, tk.Tk):
                # MotorControlGUI stores itself as app on root
                return getattr(w, '_app', None)
            w = getattr(w, 'master', None)
        return None

    # ------------------------------------------------------------------
    # Debug queue polling and display update
    # ------------------------------------------------------------------

    def _reset_timer(self):
        self._run_start = time.monotonic()
        self._timer_var.set("Run time: 0s")

    def _poll_debug_queue(self):
        if not self.winfo_exists():
            return
        try:
            while True:
                data = self.panel.debug_queue.get_nowait()
                self._history.append(data)
                if len(self._history) > self.HISTORY_SIZE:
                    self._history.pop(0)
                # Start run timer on first packet with active PWM
                if self._run_start is None and data.get("pwm", 0) > 0:
                    self._run_start = time.monotonic()
        except queue.Empty:
            pass

        # Update run timer
        if self._run_start is not None:
            elapsed = time.monotonic() - self._run_start
            mins = int(elapsed // 60)
            secs = int(elapsed % 60)
            self._timer_var.set(
                f"Run time: {mins}m {secs:02d}s" if mins > 0 else f"Run time: {secs}s")

        if self._history:
            self._update_display(self._history[-1])
            self._update_sparkline()
            self._update_suggestions()

        self.after(100, self._poll_debug_queue)

    def _update_display(self, data):
        sp  = data["setpoint"]
        mea = data["measured"]
        err = data["error"]
        pwm = data["pwm"]
        p   = data["p_term"]
        i   = data["i_term"]
        d   = data["d_term"]

        self._live_vars["setpoint"].set(f"{sp:.1f} RPM")
        self._live_vars["measured"].set(f"{mea:.1f} RPM")
        self._live_vars["error"   ].set(f"{err:+.1f} RPM")
        self._live_vars["pwm"     ].set(f"{pwm} / 255")

        total = abs(p) + abs(i) + abs(d)

        for key, (canvas, colour) in self._bar_canvases.items():
            canvas.delete("all")
            w = canvas.winfo_width() or 280
            h = canvas.winfo_height() or 18

            if key == "pwm":
                ratio = pwm / 255.0
                val   = pwm
                label = f"{val}  ({ratio*100:.0f}%)"
            else:
                val = {"p_term": p, "i_term": i, "d_term": d}[key]
                ratio = abs(val) / 255.0
                pct   = (abs(val) / total * 100) if total > 0 else 0
                label = f"{val:+.1f}  ({pct:.0f}%)"

            bar_w = int(ratio * (w - 2))
            if bar_w > 0:
                canvas.create_rectangle(1, 1, bar_w, h - 1,
                                        fill=colour, outline="")
            self._bar_vars[key].set(label)

    def _update_sparkline(self):
        errors = [d["error"] for d in self._history]
        self._sparkline.update(errors)

    def _update_suggestions(self):
        """Analyse recent history and populate suggestion rows with
        specific recommended values and one-click Apply buttons."""
        # Clear all rows
        for var, btn, action_holder in self._sugg_rows:
            var.set("")
            btn.grid_remove()
            action_holder[0] = None
        self._sugg_rows[0][0].set("") if self._sugg_rows else None

        if len(self._history) < 5:
            self._sugg_rows[0][0].set("⏳ Collecting data...")
            return

        errors  = [d["error"]  for d in self._history]
        pwms    = [d["pwm"]    for d in self._history]
        i_terms = [d["i_term"] for d in self._history]
        p_terms = [d["p_term"] for d in self._history]
        sp      = self._history[-1]["setpoint"]

        try:
            kp  = float(self._gain_vars["kp"].get()             or 0)
            ki  = float(self._gain_vars["ki"].get()             or 0)
            kd  = float(self._gain_vars["kd"].get()             or 0)
            lim = float(self._gain_vars["integral_limit"].get() or 255)
        except ValueError:
            return

        suggestions = []  # list of (text, action_or_None)

        # Oscillation
        sign_changes = sum(1 for j in range(1, len(errors))
                           if errors[j] * errors[j-1] < 0)
        if sign_changes >= 6:
            new_kp = round(kp * 0.7, 4)
            suggestions.append((
                f"⚠ Oscillating ({sign_changes} sign changes) — reduce Kp 30%  →  Kp = {new_kp}",
                lambda v=new_kp: self._set_gain("kp", v)
            ))

        # PWM saturated
        elif all(p >= 250 for p in pwms[-10:]):
            suggestions.append((
                "⚠ PWM saturated — setpoint may exceed motor's physical capability",
                None
            ))

        # Steady undershoot
        elif all(e > 0 for e in errors) and sp > 0 and errors[-1] > sp * 0.05:
            if i_terms and abs(i_terms[-1]) >= lim * 0.95:
                new_lim = round(lim * 2.0)
                suggestions.append((
                    f"⚠ Integral at limit — increase Integral Limit  →  {new_lim:.0f}",
                    lambda v=new_lim: self._set_gain("integral_limit", v)
                ))
            else:
                new_ki = round(ki * 1.5, 5)
                suggestions.append((
                    f"ℹ Steady undershoot — increase Ki  →  Ki = {new_ki}",
                    lambda v=new_ki: self._set_gain("ki", v)
                ))

        # Steady overshoot
        elif all(e < 0 for e in errors) and sp > 0 and abs(errors[-1]) > sp * 0.05:
            new_ki = round(ki * 0.7, 5)
            suggestions.append((
                f"ℹ Steady overshoot — reduce Ki  →  Ki = {new_ki}",
                lambda v=new_ki: self._set_gain("ki", v)
            ))

        # P term contributing little
        avg_p = sum(abs(v) for v in p_terms) / len(p_terms) if p_terms else 0
        avg_i = sum(abs(v) for v in i_terms) / len(i_terms) if i_terms else 0
        if avg_i > 0 and avg_p < avg_i * 0.05 and sign_changes < 6:
            new_kp = round(kp * 1.3, 4)
            suggestions.append((
                f"ℹ P term contributing little — increase Kp  →  Kp = {new_kp}",
                lambda v=new_kp: self._set_gain("kp", v)
            ))

        # Stable
        if sp > 0 and all(abs(e) < sp * 0.02 for e in errors):
            suggestions.append((
                "✓ Stable — error within 2%  Consider clicking Save Gains",
                None
            ))

        # Converging
        if len(errors) >= 10 and not suggestions:
            recent = errors[-5:]
            older  = errors[-10:-5]
            if sum(abs(e) for e in recent) < sum(abs(e) for e in older):
                suggestions.append(("ℹ Converging — wait for settle", None))

        if not suggestions:
            suggestions.append(("ℹ Monitoring...", None))

        # Populate rows — update action_holder in place so button
        # commands always reference the current action even if
        # _update_suggestions runs again before the click fires.
        for i, (var, btn, action_holder) in enumerate(self._sugg_rows):
            if i < len(suggestions):
                text, action = suggestions[i]
                var.set(text)
                action_holder[0] = action
                if action is not None:
                    btn.grid()
                else:
                    btn.grid_remove()
            else:
                var.set("")
                action_holder[0] = None
                btn.grid_remove()

    def _set_gain(self, key, value):
        """Set a gain field to a specific value and apply immediately.
        Updates the field visually and confirms with a brief status message."""
        fmt = ".0f" if key in ("integral_limit", "max_pwm_step") else "g"
        self._gain_vars[key].set(f"{value:{fmt}}")
        self._apply_gains()
        # Brief confirmation so user can see the field was updated
        self._gains_error_var.set(f"✓ Applied {key} = {value:{fmt}}")
        self.after(2000, lambda: self._gains_error_var.set(""))

    def _export_csv(self):
        """Save the current debug history to a timestamped CSV file."""
        if not self._history:
            messagebox.showinfo("Export", "No data to export yet.")
            return
        import csv
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            f"pid_debug_m{self.panel.motor_id}_{ts}.csv")
        try:
            with open(filename, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[
                    "motor_id", "setpoint", "measured", "error",
                    "p_term", "i_term", "d_term", "pwm"])
                writer.writeheader()
                writer.writerows(self._history)
            messagebox.showinfo(
                "Export", f"Saved {len(self._history)} samples:\n{filename}")
        except OSError as e:
            messagebox.showerror("Export Error", str(e))

    def _on_close(self):
        self._enable_debug(False)
        self.destroy()



class StepResponseWindow(tk.Toplevel):
    """
    Step response test — spins motor from stopped to 75% max RPM
    with PID enabled, records 50 samples (5 seconds), plots the
    response curve and suggests PID gain adjustments.
    """
    SAMPLES  = 50
    TEST_PCT = 0.75

    def __init__(self, parent, panel):
        super().__init__(parent)
        self.panel  = panel
        self.title(f"Motor {panel.motor_id} — Step Response Test")
        self.resizable(False, False)
        self.transient(parent)
        self._samples  = []
        self._setpoint = 0.0
        self._running  = False
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        ttk.Label(container,
                  text=f"Runs Motor {self.panel.motor_id} from stopped to "
                       f"{int(self.TEST_PCT*100)}% of max RPM with PID enabled.\n"
                       f"Records {self.SAMPLES} samples (~5 seconds) then stops automatically.",
                  justify="left", foreground="gray").pack(anchor="w")

        ctrl = ttk.Frame(container)
        ctrl.pack(fill="x", pady=(6, 0))
        self.btn_run = ttk.Button(ctrl, text="▶  Run Test", command=self._run_test)
        self.btn_run.pack(side="left")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(ctrl, textvariable=self.status_var,
                  foreground="gray").pack(side="left", padx=10)

        plot_frame = ttk.LabelFrame(container, text="Response Curve")
        plot_frame.pack(fill="x", pady=(8, 0))
        self.canvas = tk.Canvas(plot_frame, width=460, height=200,
                                bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack(padx=6, pady=6)

        mf = ttk.LabelFrame(container, text="Metrics")
        mf.pack(fill="x", pady=(8, 0))
        self._metric_vars = {}
        for col, (key, label) in enumerate([
            ("rise_time",    "Rise Time"),
            ("overshoot",    "Overshoot"),
            ("settling",     "Settling Time"),
            ("steady_err",   "Steady Error"),
            ("oscillations", "Oscillations"),
        ]):
            f = ttk.Frame(mf)
            f.grid(row=0, column=col, padx=8, pady=4, sticky="ew")
            mf.columnconfigure(col, weight=1)
            ttk.Label(f, text=label, font=("TkDefaultFont", 8),
                      foreground="gray", anchor="center").pack()
            var = tk.StringVar(value="--")
            ttk.Label(f, textvariable=var, font=("TkDefaultFont", 10, "bold"),
                      anchor="center").pack()
            self._metric_vars[key] = var

        sf = ttk.LabelFrame(container, text="Suggestions")
        sf.pack(fill="x", pady=(8, 0))
        sf.columnconfigure(0, weight=1)
        self._sugg_rows = []
        for i in range(3):
            var = tk.StringVar(value="")
            lbl = ttk.Label(sf, textvariable=var, justify="left", wraplength=360)
            lbl.grid(row=i, column=0, sticky="w", padx=8, pady=2)
            ah = [None]
            btn = ttk.Button(sf, text="Apply",
                             command=lambda h=ah: h[0]() if h[0] else None)
            btn.grid(row=i, column=1, padx=(4, 8), pady=2)
            btn.grid_remove()
            self._sugg_rows.append((var, btn, ah))

        bf = ttk.Frame(container)
        bf.pack(pady=(8, 0))
        ttk.Button(bf, text="Export CSV", command=self._export_csv).pack(side="left", padx=5)
        ttk.Button(bf, text="Close", command=self._on_close).pack(side="left", padx=5)

    def _run_test(self):
        app = self._get_app()
        print(f"StepTest _run_test: app={app}, connected={app.serial_port.is_open if app and app.serial_port else False}")
        if not app or not app.serial_port or not app.serial_port.is_open:
            self.status_var.set("Not connected")
            return
        cfg = self.panel.cfg
        max_rpm = cfg.get("max_motor_rpm", DEFAULT_MAX_MOTOR_RPM)
        self._setpoint = max_rpm * self.TEST_PCT
        self._samples  = []
        self._running  = True
        self.btn_run.configure(state="disabled", text="Running...")
        self.status_var.set("Starting motor...")
        self.canvas.delete("all")
        for var, btn, _ in self._sugg_rows:
            var.set(""); btn.grid_remove()
        for var in self._metric_vars.values():
            var.set("--")

        panel = self.panel
        panel.motor_in1 = 1; panel.motor_in2 = 0
        panel.motor_pwm = 0
        panel.reset_direction_styles()
        panel.btn_cw.configure(style="ActiveDir.TButton")
        panel.output_pid_enabled   = True
        panel.velocity_pid_enabled = False
        gear = cfg.get("gear_ratio", 1.0)
        output_sp = self._setpoint / gear if gear > 0 else self._setpoint
        panel.output_sp_var.set(output_sp)
        panel.output_sp_entry_var.set(f"{output_sp:.1f}")
        panel._update_pid_buttons()
        if panel.send_config:
            panel.send_config(panel.motor_id, debug_enabled=True)
        print(f"StepTest sending: motor_in1={panel.motor_in1} motor_in2={panel.motor_in2} pid={panel.output_pid_enabled} sp={panel.output_sp_entry_var.get()}")
        app.send_command()
        self.status_var.set(f"Recording... (0/{self.SAMPLES})")
        self.after(100, self._collect_sample)

    def _collect_sample(self):
        if not self._running:
            return
        latest = None
        try:
            while True:
                latest = self.panel.debug_queue.get_nowait()
        except queue.Empty:
            pass
        if latest:
            self._samples.append(latest.get("measured", 0.0))
            self.status_var.set(f"Recording... ({len(self._samples)}/{self.SAMPLES})")
            self._draw_live()
        if len(self._samples) >= self.SAMPLES:
            self._finish_test()
            return
        self.after(100, self._collect_sample)

    def _finish_test(self):
        self._running = False
        panel = self.panel
        app   = self._get_app()
        panel.motor_in1 = 0; panel.motor_in2 = 0
        panel.motor_pwm = 0
        panel.output_pid_enabled   = False
        panel.velocity_pid_enabled = False
        panel.reset_direction_styles()
        panel.btn_stop.configure(style="ActiveStop.TButton")
        panel._update_pid_buttons()
        if panel.send_config:
            panel.send_config(panel.motor_id, debug_enabled=False)
        if app:
            app.send_command()
        self.btn_run.configure(state="normal", text="▶  Run Test")
        self.status_var.set(f"Complete — {len(self._samples)} samples")
        self._draw_final()
        self._analyse()

    # ------------------------------------------------------------------
    # Plot
    # ------------------------------------------------------------------

    def _axes(self):
        W, H = 460, 200
        P = {"l": 44, "r": 10, "t": 10, "b": 25}
        pw = W - P["l"] - P["r"]
        ph = H - P["t"] - P["b"]
        max_rpm = self.panel.cfg.get("max_motor_rpm", DEFAULT_MAX_MOTOR_RPM)
        for i in range(5):
            y = P["t"] + int(ph * i / 4)
            self.canvas.create_line(P["l"], y, W - P["r"], y,
                                    fill="#333", dash=(2, 4))
            self.canvas.create_text(P["l"] - 4, y,
                                    text=f"{max_rpm*(1-i/4):.0f}",
                                    fill="#888", anchor="e",
                                    font=("TkDefaultFont", 7))
        for i in range(6):
            x = P["l"] + int(pw * i / 5)
            self.canvas.create_line(x, P["t"], x, H - P["b"],
                                    fill="#333", dash=(2, 4))
            self.canvas.create_text(x, H - P["b"] + 8,
                                    text=f"{i}s", fill="#888",
                                    font=("TkDefaultFont", 7))
        sp_y = P["t"] + int(ph * (1 - self._setpoint / max_rpm))
        self.canvas.create_line(P["l"], sp_y, W - P["r"], sp_y,
                                fill="#4488cc", dash=(4, 4))
        self.canvas.create_text(W - P["r"] - 2, sp_y - 6,
                                text="SP", fill="#4488cc",
                                font=("TkDefaultFont", 7), anchor="e")
        band = self._setpoint * 0.05
        for rpm in [self._setpoint + band, self._setpoint - band]:
            y = P["t"] + int(ph * (1 - max(0, rpm) / max_rpm))
            if P["t"] <= y <= H - P["b"]:
                self.canvas.create_line(P["l"], y, W - P["r"], y,
                                        fill="#446644", dash=(2, 6))
        return P, pw, ph, W, H, max_rpm

    def _to_y(self, rpm, max_rpm, P, ph):
        return P["t"] + int(ph * (1 - max(0, min(rpm, max_rpm)) / max_rpm))

    def _draw_live(self):
        self.canvas.delete("all")
        if not self._samples:
            return
        P, pw, ph, W, H, max_rpm = self._axes()
        n = self.SAMPLES
        pts = [(P["l"] + int(pw * i / (n-1)),
                self._to_y(r, max_rpm, P, ph)) for i, r in enumerate(self._samples)]
        sp = self._setpoint
        for i in range(1, len(pts)):
            x1, y1 = pts[i-1]; x2, y2 = pts[i]
            colour = "#cc4444" if self._samples[i] > sp * 1.05 else "#4488cc"
            self.canvas.create_line(x1, y1, x2, y2, fill=colour, width=2)

    def _draw_final(self):
        self.canvas.delete("all")
        if not self._samples:
            return
        P, pw, ph, W, H, max_rpm = self._axes()
        n  = self.SAMPLES
        sp = self._setpoint
        band = sp * 0.05
        samples = self._samples
        pts = [(P["l"] + int(pw * i / (n-1)),
                self._to_y(r, max_rpm, P, ph)) for i, r in enumerate(samples)]
        crossed = False
        for i in range(1, len(pts)):
            x1, y1 = pts[i-1]; x2, y2 = pts[i]
            r = samples[i]
            if r >= sp * 0.9: crossed = True
            colour = ("#cc4444" if r > sp * 1.05 else
                      "#44aa44" if crossed and abs(r - sp) <= band else
                      "#4488cc")
            self.canvas.create_line(x1, y1, x2, y2, fill=colour, width=2)
        # Peak marker
        peak_i = samples.index(max(samples))
        px, py = pts[peak_i]
        self.canvas.create_oval(px-4, py-4, px+4, py+4,
                                fill="#cc4444", outline="")
        self.canvas.create_text(px, py-10, text=f"{samples[peak_i]:.0f}",
                                fill="#cc4444", font=("TkDefaultFont", 7))
        # Rise time marker
        rise_i = next((i for i, r in enumerate(samples) if r >= sp*0.9), None)
        if rise_i:
            rx, ry = pts[rise_i]
            self.canvas.create_oval(rx-4, ry-4, rx+4, ry+4,
                                    fill="#4488cc", outline="")

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def _analyse(self):
        samples = self._samples
        sp      = self._setpoint
        band    = sp * 0.05
        n       = len(samples)
        if n < 5 or sp <= 0:
            return
        rise_i = next((i for i, r in enumerate(samples) if r >= sp * 0.9), None)
        rise_s = rise_i * 0.1 if rise_i is not None else None
        peak   = max(samples)
        overshoot = max(0.0, (peak - sp) / sp * 100)
        settling_i = None
        if rise_i is not None:
            for i in range(rise_i, n):
                if abs(samples[i] - sp) > band:
                    settling_i = i
        settling_s = (settling_i + 1) * 0.1 if settling_i else rise_s
        steady_err = abs(sp - sum(samples[-10:]) / 10) if n >= 10 else None
        if rise_i is not None:
            diffs = [s - sp for s in samples[rise_i:]]
            osc = sum(1 for i in range(1, len(diffs)) if diffs[i] * diffs[i-1] < 0)
        else:
            osc = 0

        self._metric_vars["rise_time"].set(
            f"{rise_s:.1f}s" if rise_s is not None else "No rise")
        self._metric_vars["overshoot"].set(f"{overshoot:.1f}%")
        self._metric_vars["settling"].set(
            f"{settling_s:.1f}s" if settling_s is not None else "--")
        self._metric_vars["steady_err"].set(
            f"{steady_err:.0f} RPM" if steady_err is not None else "--")
        self._metric_vars["oscillations"].set(str(osc))

        try:
            kp = float(self.panel.cfg.get("kp", 0.05))
            ki = float(self.panel.cfg.get("ki", 0.02))
            kd = float(self.panel.cfg.get("kd", 0.0))
        except (ValueError, TypeError):
            kp, ki, kd = 0.05, 0.02, 0.0

        suggestions = []
        if rise_i is None:
            new_kp = round(kp * 2, 4)
            suggestions.append((
                "⚠ Motor did not reach setpoint — increase Kp",
                lambda v=new_kp: self._apply_gain("kp", v)))
        elif osc >= 3:
            new_kp = round(kp * 0.7, 4)
            suggestions.append((
                f"⚠ Oscillating ({osc} cycles) — reduce Kp 30%  →  Kp = {new_kp}",
                lambda v=new_kp: self._apply_gain("kp", v)))
        elif overshoot > 20:
            new_kp = round(kp * 0.8, 4)
            suggestions.append((
                f"⚠ Overshoot {overshoot:.1f}% — reduce Kp 20%  →  Kp = {new_kp}",
                lambda v=new_kp: self._apply_gain("kp", v)))
        elif overshoot > 5 and kd < 0.001:
            new_kd = round(kp * 0.1, 5)
            suggestions.append((
                f"ℹ Overshoot {overshoot:.1f}% — add Kd to damp  →  Kd = {new_kd}",
                lambda v=new_kd: self._apply_gain("kd", v)))
        if rise_s is not None and rise_s > 2.0 and osc < 3:
            new_kp = round(kp * 1.3, 4)
            suggestions.append((
                f"ℹ Slow rise ({rise_s:.1f}s) — increase Kp  →  Kp = {new_kp}",
                lambda v=new_kp: self._apply_gain("kp", v)))
        if steady_err is not None and steady_err > sp * 0.05:
            new_ki = round(ki * 1.5, 5)
            suggestions.append((
                f"ℹ Steady error {steady_err:.0f} RPM — increase Ki  →  Ki = {new_ki}",
                lambda v=new_ki: self._apply_gain("ki", v)))
        if (rise_s is not None and rise_s < 1.0 and overshoot < 5
                and osc < 2 and steady_err is not None and steady_err < sp * 0.05):
            suggestions.append(("✓ Well tuned — consider saving gains", None))
        if not suggestions:
            suggestions.append(
                ("ℹ Response looks reasonable — fine-tune in PID Tuning window", None))

        for i, (var, btn, ah) in enumerate(self._sugg_rows):
            if i < len(suggestions):
                text, action = suggestions[i]
                var.set(text); ah[0] = action
                btn.grid() if action else btn.grid_remove()
            else:
                var.set(""); ah[0] = None; btn.grid_remove()

    def _apply_gain(self, key, value):
        app = self._get_app()
        if not app:
            return
        motor_key = str(self.panel.motor_id)
        app.motor_config[motor_key][key] = value
        self.panel.cfg[key] = value
        if self.panel.send_config:
            self.panel.send_config(self.panel.motor_id, debug_enabled=False)
        self.status_var.set(f"Applied {key} = {value} — run again to verify")

    def _export_csv(self):
        if not self._samples:
            messagebox.showinfo("Export", "No data to export yet.")
            return
        import csv
        ts = time.strftime("%Y%m%d_%H%M%S")
        fn = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          f"step_response_m{self.panel.motor_id}_{ts}.csv")
        try:
            with open(fn, "w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["sample", "time_s", "rpm", "setpoint"])
                for i, rpm in enumerate(self._samples):
                    w.writerow([i, f"{i*0.1:.1f}", f"{rpm:.1f}",
                                f"{self._setpoint:.1f}"])
            messagebox.showinfo("Export",
                f"Saved {len(self._samples)} samples:\n{fn}")
        except OSError as e:
            messagebox.showerror("Export Error", str(e))

    def _get_app(self):
        """Walk up widget tree to find MotorControlGUI stored on root Tk."""
        try:
            root = self.winfo_toplevel()
            # winfo_toplevel on a Toplevel returns itself — keep going via master
            w = self
            while w is not None:
                if isinstance(w, tk.Tk):
                    return getattr(w, '_app', None)
                w = getattr(w, 'master', None)
        except Exception:
            pass
        return None

    def _on_close(self):
        self._running = False
        self.destroy()


class MotorTestsWindow(tk.Toplevel):
    """Motor test suite window."""

    def __init__(self, parent, panel):
        super().__init__(parent)
        self.panel = panel
        self.title(f"Motor {panel.motor_id} — Tests")
        self.resizable(False, False)
        self.transient(parent)
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build_ui(self):
        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)
        ttk.Label(container, text=f"Motor {self.panel.motor_id} — Test Suite",
                  font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0, 10))

        self._enc_card = self._build_card(container,
            "Encoder Direction",
            "Spins the motor CW briefly and checks whether the encoder\n"
            "counts in the correct direction. Automatically sets the\n"
            "encoder inversion flag in Settings if needed.",
            self._run_encoder_test)

        self._step_card = self._build_card(container,
            "Step Response",
            "Enables PID at 75% of max motor RPM from a standing start\n"
            "and records the response for 5 seconds. Plots the curve\n"
            "and suggests PID gain adjustments.",
            self._run_step_test)

        ttk.Button(container, text="Close",
                   command=self.destroy).pack(pady=(10, 0))

    def _build_card(self, parent, title, description, run_cmd):
        card = ttk.LabelFrame(parent, text=title, padding=8)
        card.pack(fill="x", pady=(0, 8))
        card.columnconfigure(0, weight=1)
        ttk.Label(card, text=description, justify="left",
                  foreground="gray").grid(row=0, column=0, sticky="w")
        btn = ttk.Button(card, text="▶  Run", width=10,
                         command=lambda: run_cmd(card))
        btn.grid(row=0, column=1, padx=(12, 0), sticky="ne")
        rv = tk.StringVar(value="")
        rl = ttk.Label(card, textvariable=rv, justify="left", wraplength=380)
        rl.grid(row=1, column=0, columnspan=2, sticky="w", pady=(6, 0))
        rl.grid_remove()
        card._btn = btn; card._result_var = rv; card._result_lbl = rl
        return card

    def _set_result(self, card, text, colour="black"):
        card._result_var.set(text)
        card._result_lbl.configure(foreground=colour)
        card._result_lbl.grid()

    def _run_encoder_test(self, card):
        app = self._get_app()
        if not app or not app.serial_port or not app.serial_port.is_open:
            self._set_result(card, "✗ Not connected", "red")
            return
        card._btn.configure(state="disabled", text="Running...")
        self._set_result(card, "⏳ Spinning motor CW...", "gray")
        self.update()
        panel = self.panel
        panel.motor_in1 = 1; panel.motor_in2 = 0
        panel.motor_pwm = 120
        panel.reset_direction_styles()
        panel.btn_cw.configure(style="ActiveDir.TButton")
        app.send_command()
        self.after(800, lambda: self._check_encoder(card, app, panel))

    def _check_encoder(self, card, app, panel):
        direction = panel.direction_var.get()
        rpm_text  = panel.shaft_rpm_var.get()
        panel.motor_in1 = 0; panel.motor_in2 = 0
        panel.motor_pwm = 0
        panel.reset_direction_styles()
        panel.btn_stop.configure(style="ActiveStop.TButton")
        app.send_command()
        card._btn.configure(state="normal", text="▶  Run")
        try:
            rpm = float(rpm_text)
        except ValueError:
            rpm = 0.0
        if rpm < 50:
            self._set_result(card,
                "✗ Motor did not spin — check wiring and motor enable", "red")
            return
        motor_key = str(panel.motor_id)
        if direction == "CW":
            app.motor_config[motor_key]["encoder_inverted"] = False
            panel.cfg["encoder_inverted"] = False
            save_motor_config(app.motor_config)
            if panel.send_config:
                panel.send_config(panel.motor_id, debug_enabled=False)
            self._set_result(card,
                f"✓ Encoder direction correct  ({rpm:.0f} RPM CW)\n"
                f"  encoder_inverted set to False and saved", "green")
        else:
            app.motor_config[motor_key]["encoder_inverted"] = True
            panel.cfg["encoder_inverted"] = True
            save_motor_config(app.motor_config)
            if panel.send_config:
                panel.send_config(panel.motor_id, debug_enabled=False)
            self._set_result(card,
                f"⚠ Encoder inverted  ({rpm:.0f} RPM showed as {direction})\n"
                f"  encoder_inverted automatically set to True and saved", "orange")

    def _run_step_test(self, card):
        StepResponseWindow(self.winfo_toplevel(), self.panel)

    def _get_app(self):
        """Walk up widget tree to find MotorControlGUI stored on root Tk."""
        try:
            root = self.winfo_toplevel()
            # winfo_toplevel on a Toplevel returns itself — keep going via master
            w = self
            while w is not None:
                if isinstance(w, tk.Tk):
                    return getattr(w, '_app', None)
                w = getattr(w, 'master', None)
        except Exception:
            pass
        return None



class SettingsWindow(tk.Toplevel):
    FIELDS = [
        ("ppr",              "PPR",             "Encoder lines/gaps per motor shaft revolution (datasheet value)", "positive"),
        ("gear_ratio",       "Gear Ratio",      "Motor shaft revs per output shaft rev (1.0 = no gearbox)",       "positive"),
        ("max_motor_rpm",    "Max Motor RPM",   "Sets setpoint slider range",                                      "positive"),
        ("wheel_diameter_mm","Wheel Dia (mm)",  "Output shaft wheel diameter. 0 = no wheel",                      "nonneg"),
    ]

    def __init__(self, parent, current_config, on_save):
        super().__init__(parent)
        self.title("Motor Settings")
        self.resizable(False, False)
        self.on_save = on_save
        self.transient(parent)
        self.entries = {}
        self._current_config = current_config  # preserved for merge on save

        container = ttk.Frame(self, padding=12)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Motor Configuration",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=NUM_MOTORS + 2, pady=(0, 10), sticky="w")

        ttk.Label(container, text="Setting", anchor="w").grid(
            row=1, column=0, padx=(0, 10), pady=2, sticky="w")
        for idx, motor_id in enumerate(range(1, NUM_MOTORS + 1)):
            ttk.Label(container, text=f"Motor {motor_id}", anchor="center",
                      font=("TkDefaultFont", 9, "bold")).grid(
                row=1, column=idx + 1, padx=5, pady=2, sticky="ew")

        for f_idx, (key, label, hint, _) in enumerate(self.FIELDS):
            r = f_idx + 2
            ttk.Label(container, text=label, anchor="w").grid(
                row=r, column=0, padx=(0, 10), pady=3, sticky="w")
            for idx, motor_id in enumerate(range(1, NUM_MOTORS + 1)):
                motor_key = str(motor_id)
                if motor_key not in self.entries:
                    self.entries[motor_key] = {}
                default = default_motor_config()[motor_key][key]
                val = current_config.get(motor_key, {}).get(key, default)
                var = tk.StringVar(value=f"{val:g}" if isinstance(val, float) else str(val))
                entry = ttk.Entry(container, textvariable=var, width=10, justify="center")
                entry.grid(row=r, column=idx + 1, padx=5, pady=3)
                self.entries[motor_key][key] = var
            ttk.Label(container, text=hint, foreground="gray",
                      font=("TkDefaultFont", 8)).grid(
                row=r, column=NUM_MOTORS + 1, padx=(8, 0), sticky="w")

        last_row = len(self.FIELDS) + 2

        # Encoder inversion — checkbox per motor
        ttk.Label(container, text="Encoder Inverted", anchor="w").grid(
            row=last_row, column=0, padx=(0, 10), pady=3, sticky="w")
        self._invert_vars = {}
        for idx, motor_id in enumerate(range(1, NUM_MOTORS + 1)):
            motor_key = str(motor_id)
            val = current_config.get(motor_key, {}).get(
                "encoder_inverted", default_motor_config()[motor_key]["encoder_inverted"])
            var = tk.BooleanVar(value=bool(val))
            ttk.Checkbutton(container, variable=var).grid(
                row=last_row, column=idx + 1, padx=5, pady=3)
            self._invert_vars[motor_key] = var
        ttk.Label(container, text="Invert encoder direction if CW shows as CCW",
                  foreground="gray", font=("TkDefaultFont", 8)).grid(
            row=last_row, column=NUM_MOTORS + 1, padx=(8, 0), sticky="w")
        last_row += 1

        self.error_var = tk.StringVar(value="")
        ttk.Label(container, textvariable=self.error_var, foreground="red").grid(
            row=last_row, column=0, columnspan=NUM_MOTORS + 2, pady=(6, 0))

        btn_frame = ttk.Frame(container)
        btn_frame.grid(row=last_row + 1, column=0,
                       columnspan=NUM_MOTORS + 2, pady=(8, 0))
        ttk.Button(btn_frame, text="Save",   command=self._save  ).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _save(self):
        new_config = {}
        for motor_key in self.entries:
            # Start from existing full config so PID gains and other fields
            # not shown in Settings (saved by PIDTuningWindow) are preserved
            cfg = dict(self._current_config.get(
                motor_key, default_motor_config()[motor_key]))

            for key, label, hint, coerce in self.FIELDS:
                raw = self.entries[motor_key][key].get()
                try:
                    v = float(raw)
                    if coerce == "positive" and v <= 0:
                        raise ValueError
                    if coerce == "nonneg"   and v <  0:
                        raise ValueError
                    cfg[key] = v
                except ValueError:
                    rule = "positive number" if coerce == "positive" else "non-negative number"
                    self.error_var.set(f"Motor {motor_key} — {label}: must be a {rule}.")
                    return
            # Add boolean fields
            cfg["encoder_inverted"] = self._invert_vars[motor_key].get()
            new_config[motor_key] = cfg
        if save_motor_config(new_config):
            self.on_save(new_config)
            self.destroy()
        else:
            self.error_var.set(f"Failed to write {CONFIG_PATH}. Check permissions.")


# ----------------------------------------------------------------------
# Main GUI controller
# ----------------------------------------------------------------------

class MotorControlGUI:
    MAX_PACKETS_PER_TICK = 20

    def __init__(self, root):
        self.root = root
        self.root.title("XorTech ::: 2-Motors with Encoders USB CDC Controller")
        self.serial_port    = None
        self.serial_reader  = None
        self.encoder_queue  = queue.Queue()
        self.motor_config   = load_motor_config()
        self.settings_window = None

        self._last_raw_value    = {m: None for m in range(1, NUM_MOTORS + 1)}
        self._last_packet_time  = {m: None for m in range(1, NUM_MOTORS + 1)}
        self._sync_enabled      = False

        # --- Connection controls ---
        detect_frame = ttk.Frame(root)
        detect_frame.pack(pady=5)
        ttk.Button(detect_frame, text="Auto-Detect",   command=self.detect_usb_device).pack(side="left", padx=5)
        self.port_var   = tk.StringVar()
        self.port_combo = ttk.Combobox(detect_frame, textvariable=self.port_var, width=22, state="readonly")
        self.port_combo.pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Refresh Ports", command=self.refresh_ports).pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Connect",       command=self.connect_selected_port).pack(side="left", padx=5)

        self.status_label = ttk.Label(root, text="Status: Not connected")
        self.status_label.pack(pady=(2, 0))

        # --- Shared motor toolbar — Settings only ---
        toolbar_frame = ttk.Frame(root)
        toolbar_frame.pack(padx=10, pady=(4, 0), fill="x")
        ttk.Button(toolbar_frame, text="⚙ Settings...",
                   command=self.open_settings).pack(side="left", padx=5)

        self.refresh_ports()

        # Motor panels — Motor 1 | Sync column | Motor 2
        self.motor_frames = []
        motors_frame = ttk.Frame(root)
        motors_frame.pack(padx=10, pady=(4, 10), fill="both", expand=True)
        motors_frame.columnconfigure(0, weight=1)
        motors_frame.columnconfigure(1, weight=0)  # sync column — fixed width
        motors_frame.columnconfigure(2, weight=1)

        for i in range(1, NUM_MOTORS + 1):
            col = 0 if i == 1 else 2
            panel = MotorControlPanel(motors_frame, i, self.send_command,
                                      send_config_cb=self.send_motor_config)
            panel.grid(row=0, column=col, padx=6, pady=6, sticky="nsew")
            cfg = self.motor_config.get(str(i), default_motor_config()[str(i)])
            panel.apply_config(cfg)
            self.motor_frames.append(panel)

        # Sync column — fixed width, centred between the two motor panels
        sync_col = ttk.Frame(motors_frame, width=80)
        sync_col.grid(row=0, column=1, padx=4, pady=6, sticky="ns")
        sync_col.grid_propagate(False)  # prevent content from resizing the column
        sync_col.rowconfigure(0, weight=1)
        sync_col.rowconfigure(4, weight=1)

        self.sync_status_var = tk.StringVar(value="")  # kept for internal state

        self.btn_sync = ttk.Button(sync_col, text="Motor\nSync",
                                   command=self.toggle_sync, state="disabled",
                                   width=8, style="Sync.TButton")
        self.btn_sync.grid(row=1, column=0, pady=4)
        Tooltip(self.btn_sync,
                "Synchronise both motors using encoder\n"
                "count tracking.\n\n"
                "How to use:\n"
                "  1. Stop both motors, disable both PIDs\n"
                "  2. Click Motor Sync to enable\n"
                "  3. Set direction on each motor (CW/CCW)\n"
                "  4. Set velocity setpoint on Motor 1\n"
                "  5. Click Enable PID on Motor 1\n\n"
                "Motor 2 will track Motor 1 automatically.\n"
                "Directions can differ (e.g. for a rover).")

        self.sync_error_title = ttk.Label(sync_col, text="Encoder Error",
                  font=("TkDefaultFont", 8), anchor="center",
                  width=12)
        self.sync_error_title.grid(row=2, column=0, pady=(8, 0))
        self.sync_error_var = tk.StringVar(value="--")
        self.sync_error_label = ttk.Label(sync_col, textvariable=self.sync_error_var,
                  font=("TkDefaultFont", 9, "bold"), anchor="center",
                  foreground="gray", width=12)
        self.sync_error_label.grid(row=3, column=0)
        # Hidden until sync is active
        self.sync_error_title.grid_remove()
        self.sync_error_label.grid_remove()

        # When Motor 1 setpoint changes and sync is active, mirror to Motor 2
        def _m1_setpoint_changed():
            if self._sync_enabled and len(self.motor_frames) >= 2:
                self._apply_sync_to_motor2()
        self.motor_frames[0].on_setpoint_change = _m1_setpoint_changed

        # When Motor 1 PID enables/disables during sync, lock/unlock direction controls
        def _m1_pid_changed():
            if self._sync_enabled:
                m1 = self.motor_frames[0]
                m2 = self.motor_frames[1]
                pid_active = m1.output_pid_enabled or m1.velocity_pid_enabled
                state = "disabled" if pid_active else "normal"
                for panel in [m1, m2]:
                    panel.btn_cw   .configure(state=state)
                    panel.btn_ccw  .configure(state=state)
                    panel.btn_stop .configure(state="normal")  # stop always available
                    panel.btn_brake.configure(state=state)
                    panel.speed_slider.configure(state=state)
        self.motor_frames[0].on_pid_change = _m1_pid_changed
        def _m1_motor_stopped():
            if self._sync_enabled and len(self.motor_frames) >= 2:
                m2 = self.motor_frames[1]
                m2.motor_in1 = 0
                m2.motor_in2 = 0
                m2.output_pid_enabled   = False
                m2.velocity_pid_enabled = False
                m2.reset_direction_styles()
                m2.btn_stop.configure(style="ActiveStop.TButton")
                m2._update_pid_buttons()
                # Disable sync — clean state for next run
                self._sync_enabled = False
                self._restore_motor2_controls()
                self._update_sync_button()
        self.motor_frames[0].on_motor_stop = _m1_motor_stopped

        self.root.after(POLL_INTERVAL_MS, self._poll_encoder_queue)

    def toggle_sync(self):
        self._sync_enabled = not self._sync_enabled
        if self._sync_enabled:
            # Sync just enabled — grey out Motor 2 PID controls
            # and mirror Motor 1's setpoint to Motor 2
            self._apply_sync_to_motor2()
        else:
            # Sync disabled — restore Motor 2 controls
            self._restore_motor2_controls()
        self._update_sync_button()
        self.send_command()

    def _apply_sync_to_motor2(self):
        """When sync enables, copy Motor 1's setpoint and PID state
        to Motor 2 and lock controls on both motors."""
        m1 = self.motor_frames[0]
        m2 = self.motor_frames[1]

        # Mirror Motor 1's PID mode and setpoint to Motor 2
        m2.output_pid_enabled   = m1.output_pid_enabled
        m2.velocity_pid_enabled = m1.velocity_pid_enabled
        m2.output_sp_var.set(m1.output_sp_var.get())
        m2.output_sp_entry_var.set(m1.output_sp_entry_var.get())
        m2.vel_sp_var.set(m1.vel_sp_var.get())
        m2.vel_sp_entry_var.set(m1.vel_sp_entry_var.get())
        m2._update_pid_buttons()

        # Lock Motor 2 setpoint and PID controls
        m2.output_sp_slider.configure(state="disabled")
        m2.vel_sp_slider.configure(state="disabled")
        m2.btn_output_pid.configure(state="disabled")
        m2.btn_vel_pid.configure(state="disabled")

        # Lock direction and speed controls on BOTH motors during sync
        # only once PID is active — before PID starts, direction can still
        # be set (motors aren't moving yet so it's safe)
        m1_pid_active = m1.output_pid_enabled or m1.velocity_pid_enabled
        if m1_pid_active:
            for panel in [m1, m2]:
                panel.btn_cw   .configure(state="disabled")
                panel.btn_ccw  .configure(state="disabled")
                panel.btn_stop .configure(state="disabled")
                panel.btn_brake.configure(state="disabled")
                panel.speed_slider.configure(state="disabled")

    def _restore_motor2_controls(self):
        """Restore all controls when sync is disabled."""
        m1 = self.motor_frames[0]
        m2 = self.motor_frames[1]

        # Restore Motor 2 setpoint and PID controls
        m2.output_sp_slider.configure(state="normal")
        m2.btn_output_pid.configure(state="normal")
        m2._refresh_velocity_state()

        # Restore direction and speed controls on both motors
        for panel in [m1, m2]:
            panel.btn_cw   .configure(state="normal")
            panel.btn_ccw  .configure(state="normal")
            panel.btn_stop .configure(state="normal")
            panel.btn_brake.configure(state="normal")
            panel.speed_slider.configure(state="normal")

    def _update_sync_button(self):
        """Sync is available when both motors are stopped (coast)
        and both PIDs are disabled — clean starting condition."""
        connected = self.serial_port and self.serial_port.is_open

        both_stopped = all(
            p.motor_in1 == 0 and p.motor_in2 == 0
            for p in self.motor_frames)
        both_pid_off = all(
            not p.output_pid_enabled and not p.velocity_pid_enabled
            for p in self.motor_frames)

        # Can enable sync when stopped and PIDs off, or when already synced
        can_sync = connected and (both_stopped and both_pid_off or self._sync_enabled)

        self.btn_sync.configure(state="normal" if can_sync else "disabled")

        if not can_sync and self._sync_enabled:
            # Lost sync condition — disable cleanly
            self._sync_enabled = False
            self._restore_motor2_controls()

        if self._sync_enabled:
            self.btn_sync.configure(text="Motor\nSync", style="ActiveSync.TButton")
            self.sync_error_title.grid()
            self.sync_error_label.grid()
        else:
            self.btn_sync.configure(text="Motor\nSync", style="Sync.TButton")
            self.sync_error_var.set("--")
            self.sync_error_title.grid_remove()
            self.sync_error_label.grid_remove()

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def open_settings(self):
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_set()
            return
        self.settings_window = SettingsWindow(
            self.root, self.motor_config, self._on_settings_saved)

    def _on_settings_saved(self, new_config):
        self.motor_config = new_config
        for panel in self.motor_frames:
            cfg = new_config.get(str(panel.motor_id),
                                 default_motor_config()[str(panel.motor_id)])
            panel.apply_config(cfg)
        self.send_all_config()

    # ------------------------------------------------------------------
    # Port discovery / connection
    # ------------------------------------------------------------------

    def refresh_ports(self):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            vid = f"{port.vid:04X}" if port.vid is not None else "----"
            pid = f"{port.pid:04X}" if port.pid is not None else "----"
            print(f"{port.device}: VID={vid} PID={pid} desc='{port.description}'")
        self.port_combo['values'] = [p.device for p in ports]
        if ports and not self.port_var.get():
            self.port_var.set(ports[0].device)
        elif not ports:
            self.port_var.set("")

    def find_usb_cdc_device(self, keyword="USB Serial"):
        ports = serial.tools.list_ports.comports()
        for port in ports:
            if (port.vid, port.pid) in KNOWN_VID_PID:
                return port.device
        cdc_keywords = (keyword.lower(), "xortech", "dualmotor", "cdc", "acm")
        for port in ports:
            description = (port.description or "").lower()
            if any(k in description for k in cdc_keywords):
                return port.device
        return None

    def detect_usb_device(self):
        device = self.find_usb_cdc_device()
        if device:
            self.port_var.set(device)
            self.open_serial_port(device)
        else:
            self.status_label.config(text="Status: No USB CDC device found")
            messagebox.showwarning(
                "Device Not Found",
                "No USB CDC device detected automatically.\n"
                "Select a port from the dropdown and click Connect.")

    def connect_selected_port(self):
        device = self.port_var.get()
        if not device:
            messagebox.showwarning("No Port Selected", "Please select a serial port.")
            return
        self.open_serial_port(device)

    def open_serial_port(self, device):
        try:
            self._stop_reader()
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.serial_port = serial.Serial(device, baudrate=115200, timeout=0)
            self.status_label.config(text=f"Connected to {device}")
            self._last_raw_value   = {m: None for m in range(1, NUM_MOTORS + 1)}
            self._last_packet_time = {m: None for m in range(1, NUM_MOTORS + 1)}
            for panel in self.motor_frames:
                panel.reset_total_count()
            self.serial_reader = SerialReader(
                self.serial_port, self.encoder_queue,
                debug_queues={panel.motor_id: panel.debug_queue
                              for panel in self.motor_frames})
            self.serial_reader.start()

            # Reset firmware to a known stopped state so it matches
            # the GUI's freshly initialised panel defaults.
            stop_packet = bytes([0x55, 0x03,
                                 0x00, 0x00,  # M1 coast, PWM 0
                                 0x00, 0x00,  # M2 coast, PWM 0
                                 0x00,        # ctrl flags: all off
                                 0x00, 0x00,  # M1 setpoint 0
                                 0x00, 0x00]) # M2 setpoint 0
            self.serial_port.write(stop_packet)

            self.root.after(200, self.send_all_config)
        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Failed to open {device}:\n{e}")
            self.status_label.config(text="Status: Not connected")

    def _stop_reader(self):
        if self.serial_reader and self.serial_reader.is_alive():
            self.serial_reader.stop()
            self.serial_reader.join(timeout=1)
        self.serial_reader = None

    # ------------------------------------------------------------------
    # Encoder polling
    # ------------------------------------------------------------------

    def _poll_encoder_queue(self):
        packets = []
        try:
            while len(packets) < self.MAX_PACKETS_PER_TICK:
                packets.append(self.encoder_queue.get_nowait())
        except queue.Empty:
            pass

        for latest_ts, latest, sync_err, sync_on in packets:
            # Update sync error display
            if sync_on:
                self.sync_error_var.set(f"{sync_err:+d}")
            else:
                self.sync_error_var.set("--")

            # Also refresh sync button state in case PID was enabled/disabled
            self._update_sync_button()

            for panel in self.motor_frames:
                if panel.motor_id not in latest:
                    continue
                raw_value = latest[panel.motor_id]
                motor_id  = panel.motor_id

                if READING_MODE == READING_MODE_RPM_X10:
                    motor_shaft_rpm = raw_value / 10.0
                    self._last_packet_time[motor_id] = latest_ts
                    panel.update_rpm(motor_shaft_rpm,
                                     panel.cfg.get("gear_ratio",        DEFAULT_GEAR_RATIO),
                                     panel.cfg.get("wheel_diameter_mm", 0.0))

                elif READING_MODE == READING_MODE_ABSOLUTE:
                    previous = self._last_raw_value[motor_id]
                    self._last_raw_value[motor_id] = raw_value
                    if previous is None:
                        self._last_packet_time[motor_id] = latest_ts
                        continue
                    delta_counts = raw_value - previous
                    if delta_counts > RAW_VALUE_RANGE // 2:
                        delta_counts -= RAW_VALUE_RANGE
                    elif delta_counts < -RAW_VALUE_RANGE // 2:
                        delta_counts += RAW_VALUE_RANGE
                    last_t = self._last_packet_time[motor_id]
                    elapsed_sec = (latest_ts - last_t
                                   if last_t is not None and latest_ts > last_t
                                   else POLL_INTERVAL_SEC)
                    self._last_packet_time[motor_id] = latest_ts
                    cfg = self.motor_config.get(str(motor_id), default_motor_config()[str(motor_id)])
                    panel.update_encoder(delta_counts, cfg["ppr"], cfg["gear_ratio"], elapsed_sec)

                else:  # READING_MODE_DELTA
                    delta_counts = raw_value
                    last_t = self._last_packet_time[motor_id]
                    elapsed_sec = (latest_ts - last_t
                                   if last_t is not None and latest_ts > last_t
                                   else POLL_INTERVAL_SEC)
                    self._last_packet_time[motor_id] = latest_ts
                    cfg = self.motor_config.get(str(motor_id), default_motor_config()[str(motor_id)])
                    panel.update_encoder(delta_counts, cfg["ppr"], cfg["gear_ratio"], elapsed_sec)

        # Blank stale readings
        now = time.monotonic()
        for panel in self.motor_frames:
            last_t = self._last_packet_time[panel.motor_id]
            if last_t is not None and (now - last_t) > STALE_TIMEOUT_SEC:
                panel.clear_live_rpm()
                self._last_packet_time[panel.motor_id] = None
                self._last_raw_value[panel.motor_id]   = None

        self.root.after(POLL_INTERVAL_MS, self._poll_encoder_queue)

    # ------------------------------------------------------------------
    # Command sending
    # ------------------------------------------------------------------

    def send_command(self):
        # 11-byte command packet:
        # Byte 0:  0x55 header
        # Byte 1:  motor flags [bit0=M01_STBY]
        # Byte 2:  M1 direction [bit0=IN1, bit1=IN2]
        # Byte 3:  M1 PWM (manual mode)
        # Byte 4:  M2 direction
        # Byte 5:  M2 PWM (manual mode)
        # Byte 6:  control flags [bit0=M1_PID, bit1=M2_PID, bit2=SYNC]
        # Byte 7:  M1 setpoint high byte  } motor shaft RPM×10 as uint16
        # Byte 8:  M1 setpoint low byte   }
        # Byte 9:  M2 setpoint high byte
        # Byte 10: M2 setpoint low byte
        cdcdata = [0x55, 0x03] + [0] * 9  # 11 bytes

        # Direction and PWM bytes (unchanged positions)
        for panel in self.motor_frames:
            motor_id = panel.motor_id
            dir_byte = (panel.motor_in1 * 1) + (panel.motor_in2 * 2)
            cdcdata[motor_id * 2]       = dir_byte   # bytes 2, 4
            cdcdata[(motor_id * 2) + 1] = panel.motor_pwm  # bytes 3, 5

        # Control flags byte 6
        m1 = self.motor_frames[0]
        m2 = self.motor_frames[1]
        m1_pid = m1.output_pid_enabled or m1.velocity_pid_enabled
        # When sync active, Motor 2 PID mirrors Motor 1
        m2_pid = m1_pid if self._sync_enabled else (m2.output_pid_enabled or m2.velocity_pid_enabled)

        ctrl = 0
        if m1_pid:              ctrl |= (1 << 0)  # FLAG_M1_PID
        if m2_pid:              ctrl |= (1 << 1)  # FLAG_M2_PID
        if self._sync_enabled:  ctrl |= (1 << 2)  # FLAG_SYNC
        cdcdata[6] = ctrl

        # Setpoints — bytes 7-10
        for panel in self.motor_frames:
            motor_id = panel.motor_id
            if self._sync_enabled and motor_id == 2:
                # Sync active — Motor 2 mirrors Motor 1 setpoint
                raw_sp = m1.motor_shaft_setpoint() * 10
            else:
                raw_sp = panel.motor_shaft_setpoint() * 10
            setpoint_x10 = int(max(0.0, min(raw_sp, 65535.0)))
            base = 5 + (motor_id * 2)  # M1→7,8  M2→9,10
            cdcdata[base]     = (setpoint_x10 >> 8) & 0xFF
            cdcdata[base + 1] =  setpoint_x10       & 0xFF

        print(printHex(cdcdata))

        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(bytes(cdcdata))
                self._update_sync_button()
                for panel in self.motor_frames:
                    if panel.motor_in1 == 0 and panel.motor_in2 == 0:
                        self._last_packet_time[panel.motor_id] = None
                        self._last_raw_value[panel.motor_id]   = None
            except serial.SerialException as e:
                messagebox.showerror("Serial Error", f"Failed to send command:\n{e}")
        else:
            messagebox.showwarning("Not Connected", "Please connect to a USB CDC device first.")

    def send_motor_config(self, motor_id, debug_enabled=False):
        motor_key = str(motor_id)
        defaults  = default_motor_config()[motor_key]
        cfg       = self.motor_config.get(motor_key, defaults)

        packet = bytearray(22)
        packet[0] = 0xBB
        packet[1] = motor_id
        struct.pack_into('<H', packet, 2,  int(cfg.get('ppr',             defaults['ppr'])))
        struct.pack_into('<f', packet, 4,  float(cfg.get('kp',            defaults['kp'])))
        struct.pack_into('<f', packet, 8,  float(cfg.get('ki',            defaults['ki'])))
        struct.pack_into('<f', packet, 12, float(cfg.get('kd',            defaults['kd'])))
        struct.pack_into('<f', packet, 16, float(cfg.get('integral_limit',defaults['integral_limit'])))
        packet[20] = int(max(1, min(255, cfg.get('max_pwm_step', defaults['max_pwm_step']))))

        # Byte 21: flags byte
        # bit 0 = debug_enabled, bit 1 = encoder_inverted
        flags = 0
        if debug_enabled:                              flags |= (1 << 0)
        if cfg.get('encoder_inverted', False):         flags |= (1 << 1)
        packet[21] = flags

        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(bytes(packet))
                print(f"Config sent for motor {motor_id}: {printHex(packet)}")
            except serial.SerialException as e:
                messagebox.showerror("Serial Error", f"Failed to send config:\n{e}")

    def send_all_config(self):
        for motor_id in range(1, NUM_MOTORS + 1):
            self.send_motor_config(motor_id)
            time.sleep(0.02)

    def on_close(self):
        # Stop all motors before closing
        if self.serial_port and self.serial_port.is_open:
            try:
                # Send a stop command — all motors coast, PID disabled,
                # PWM 0, sync off. Must be 11 bytes to match CMD_PACKET_SIZE.
                stop_packet = bytes([0x55, 0x03,
                                     0x00, 0x00,  # M1 coast, PWM 0
                                     0x00, 0x00,  # M2 coast, PWM 0
                                     0x00,        # ctrl flags: all off
                                     0x00, 0x00,  # M1 setpoint 0
                                     0x00, 0x00]) # M2 setpoint 0
                self.serial_port.write(stop_packet)
                time.sleep(0.1)  # give firmware time to process
            except serial.SerialException:
                pass
        self._stop_reader()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.root.destroy()


# ----------------------------------------------------------------------
# Entry point
# ----------------------------------------------------------------------

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use("clam")

    # Sync button — bold, centred
    style.configure("Sync.TButton",
                    font=("TkDefaultFont", 10, "bold"), anchor="center")
    style.configure("ActiveSync.TButton",
                    font=("TkDefaultFont", 10, "bold"), anchor="center",
                    background="green", foreground="white")
    style.map("ActiveSync.TButton",
              background=[("!disabled", "green")],
              foreground=[("!disabled", "white")])

    style.configure("ActiveDir.TButton",   background="green",  foreground="white")
    style.configure("ActiveStop.TButton",  background="red",    foreground="white")
    style.configure("ActiveBrake.TButton", background="orange", foreground="black")

    style.map("ActiveDir.TButton",   background=[("!disabled", "green")],  foreground=[("!disabled", "white")])
    style.map("ActiveStop.TButton",  background=[("!disabled", "red")],    foreground=[("!disabled", "white")])
    style.map("ActiveBrake.TButton", background=[("!disabled", "orange")], foreground=[("!disabled", "black")])

    app = MotorControlGUI(root)
    root._app = app  # allows PIDTuningWindow to find the app via widget tree
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()