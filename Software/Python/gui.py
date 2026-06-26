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
ENCODER_PACKET_SIZE = 1 + (4 * NUM_MOTORS)  # header + 4 bytes per motor
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

class SerialReader(threading.Thread):
    def __init__(self, serial_port, data_queue):
        super().__init__(daemon=True)
        self.serial_port = serial_port
        self.data_queue = data_queue
        self._stop_event = threading.Event()
        self._buffer = bytearray()

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
            header_index = self._buffer.find(bytes([ENCODER_HEADER]))
            if header_index == -1:
                self._buffer.clear()
                return
            if header_index > 0:
                del self._buffer[:header_index]
            if len(self._buffer) < ENCODER_PACKET_SIZE:
                return
            packet = bytes(self._buffer[:ENCODER_PACKET_SIZE])
            del self._buffer[:ENCODER_PACKET_SIZE]
            try:
                values = struct.unpack(f'<{NUM_MOTORS}l', packet[1:])
            except struct.error:
                continue
            encoder_values = {m: values[m - 1] for m in range(1, NUM_MOTORS + 1)}
            self.data_queue.put((time.monotonic(), encoder_values))


# ----------------------------------------------------------------------
# Motor control panel
# ----------------------------------------------------------------------

class MotorControlPanel(ttk.LabelFrame):
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

    def __init__(self, parent, motor_id, send_command_cb):
        super().__init__(parent, text=f"Motor {motor_id}")
        self.motor_id     = motor_id
        self.send_command = send_command_cb

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
        self.send_command()

    def brake_motor(self):
        self.motor_in1 = 1; self.motor_in2 = 1
        self.reset_direction_styles()
        self.btn_brake.configure(style="ActiveBrake.TButton")
        self._update_pid_buttons()
        self.send_command()

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
        if not self.output_pid_enabled:
            self.output_pid_enabled   = True
            self.velocity_pid_enabled = False
        self._update_pid_buttons()
        self.send_command()

    def _on_output_sp_entry(self, event=None):
        try:
            v = float(self.output_sp_entry_var.get())
            v = max(0.0, min(v, self.output_sp_slider.cget("to")))
            self.output_sp_entry_var.set(f"{v:.1f}")
            self.output_sp_var.set(v)
            if not self.output_pid_enabled:
                self.output_pid_enabled   = True
                self.velocity_pid_enabled = False
            self._update_pid_buttons()
            self.send_command()
        except ValueError:
            pass

    def _on_vel_sp_slider(self, val):
        v = float(val)
        self.vel_sp_entry_var.set(f"{v:.3f}")
        if not self.velocity_pid_enabled:
            self.velocity_pid_enabled = True
            self.output_pid_enabled   = False
        self._update_pid_buttons()
        self.send_command()

    def _on_vel_sp_entry(self, event=None):
        try:
            v = float(self.vel_sp_entry_var.get())
            v = max(0.0, min(v, self.vel_sp_slider.cget("to")))
            self.vel_sp_entry_var.set(f"{v:.3f}")
            self.vel_sp_var.set(v)
            if not self.velocity_pid_enabled:
                self.velocity_pid_enabled = True
                self.output_pid_enabled   = False
            self._update_pid_buttons()
            self.send_command()
        except ValueError:
            pass

    def toggle_output_pid(self):
        self.output_pid_enabled = not self.output_pid_enabled
        if self.output_pid_enabled:
            self.velocity_pid_enabled = False
        else:
            # Restore manual control at a safe mid-range speed
            self.speed_var.set(128)
            self.motor_pwm = 128
        self._update_pid_buttons()
        self.send_command()

    def toggle_velocity_pid(self):
        self.velocity_pid_enabled = not self.velocity_pid_enabled
        if self.velocity_pid_enabled:
            self.output_pid_enabled = False
        else:
            # Restore manual control at a safe mid-range speed
            self.speed_var.set(128)
            self.motor_pwm = 128
        self._update_pid_buttons()
        self.send_command()

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

class SettingsWindow(tk.Toplevel):
    FIELDS = [
        ("ppr",              "PPR",             "Encoder lines/gaps per motor shaft revolution (datasheet value)", "positive"),
        ("gear_ratio",       "Gear Ratio",      "Motor shaft revs per output shaft rev (1.0 = no gearbox)",       "positive"),
        ("max_motor_rpm",    "Max Motor RPM",   "Sets setpoint slider range",                                      "positive"),
        ("wheel_diameter_mm","Wheel Dia (mm)",  "Output shaft wheel diameter. 0 = no wheel",                      "nonneg"),
        ("kp",               "Kp",              "PID proportional gain",                                           "nonneg"),
        ("ki",               "Ki",              "PID integral gain",                                               "nonneg"),
        ("kd",               "Kd",              "PID derivative gain",                                             "nonneg"),
        ("integral_limit",   "Integral Limit",  "Anti-windup clamp",                                               "positive"),
    ]

    def __init__(self, parent, current_config, on_save):
        super().__init__(parent)
        self.title("Motor Settings")
        self.resizable(False, False)
        self.on_save = on_save
        self.transient(parent)
        self.entries = {}

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
            cfg = {}
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

        # --- Connection controls ---
        detect_frame = ttk.Frame(root)
        detect_frame.pack(pady=5)
        ttk.Button(detect_frame, text="Auto-Detect",   command=self.detect_usb_device).pack(side="left", padx=5)
        self.port_var   = tk.StringVar()
        self.port_combo = ttk.Combobox(detect_frame, textvariable=self.port_var, width=22, state="readonly")
        self.port_combo.pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Refresh Ports", command=self.refresh_ports).pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Connect",       command=self.connect_selected_port).pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Settings...",   command=self.open_settings).pack(side="left", padx=5)

        self.status_label = ttk.Label(root, text="Status: Not connected")
        self.status_label.pack(pady=5)

        self.refresh_ports()

        # Motor panels — side by side
        self.motor_frames = []
        motors_frame = ttk.Frame(root)
        motors_frame.pack(padx=10, pady=10, fill="both", expand=True)
        for i in range(1, NUM_MOTORS + 1):
            panel = MotorControlPanel(motors_frame, i, self.send_command)
            panel.grid(row=0, column=i - 1, padx=10, pady=6, sticky="nsew")
            motors_frame.columnconfigure(i - 1, weight=1)
            cfg = self.motor_config.get(str(i), default_motor_config()[str(i)])
            panel.apply_config(cfg)
            self.motor_frames.append(panel)

        self.root.after(POLL_INTERVAL_MS, self._poll_encoder_queue)

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
            self.serial_reader = SerialReader(self.serial_port, self.encoder_queue)
            self.serial_reader.start()

            # Reset firmware to a known stopped state so it matches
            # the GUI's freshly initialised panel defaults.
            stop_packet = bytes([0x55, 0x03,
                                 0x00, 0x00,       # M1 coast, PWM 0
                                 0x00, 0x00,       # M2 coast, PWM 0
                                 0x00, 0x00, 0x00, # M1 PID off, setpoint 0
                                 0x00, 0x00, 0x00])# M2 PID off, setpoint 0
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

        for latest_ts, latest in packets:
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
        # 12-byte command packet:
        # [0x55, enable, M1_dir, M1_pwm, M2_dir, M2_pwm,
        #  M1_pid_en, M1_sp_hi, M1_sp_lo,
        #  M2_pid_en, M2_sp_hi, M2_sp_lo]
        cdcdata = [0x55, 0x03] + [0] * 10

        for panel in self.motor_frames:
            motor_id = panel.motor_id
            dir_byte = (panel.motor_in1 * 1) + (panel.motor_in2 * 2)
            cdcdata[motor_id * 2]       = dir_byte
            cdcdata[(motor_id * 2) + 1] = panel.motor_pwm

            pid_active = panel.output_pid_enabled or panel.velocity_pid_enabled
            raw_sp = panel.motor_shaft_setpoint() * 10
            setpoint_x10 = int(max(0.0, min(raw_sp, 65535.0)))
            sp_hi = (setpoint_x10 >> 8) & 0xFF
            sp_lo =  setpoint_x10       & 0xFF
            base = 6 + (motor_id - 1) * 3
            cdcdata[base]     = 1 if pid_active else 0
            cdcdata[base + 1] = sp_hi
            cdcdata[base + 2] = sp_lo

        print(printHex(cdcdata))

        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(bytes(cdcdata))
                for panel in self.motor_frames:
                    if panel.motor_in1 == 0 and panel.motor_in2 == 0:
                        self._last_packet_time[panel.motor_id] = None
                        self._last_raw_value[panel.motor_id]   = None
            except serial.SerialException as e:
                messagebox.showerror("Serial Error", f"Failed to send command:\n{e}")
        else:
            messagebox.showwarning("Not Connected", "Please connect to a USB CDC device first.")

    def send_motor_config(self, motor_id):
        motor_key = str(motor_id)
        defaults  = default_motor_config()[motor_key]
        cfg       = self.motor_config.get(motor_key, defaults)

        packet = bytearray(20)
        packet[0] = 0xBB
        packet[1] = motor_id
        struct.pack_into('<H', packet, 2,  int(cfg.get('ppr',             defaults['ppr'])))
        struct.pack_into('<f', packet, 4,  float(cfg.get('kp',            defaults['kp'])))
        struct.pack_into('<f', packet, 8,  float(cfg.get('ki',            defaults['ki'])))
        struct.pack_into('<f', packet, 12, float(cfg.get('kd',            defaults['kd'])))
        struct.pack_into('<f', packet, 16, float(cfg.get('integral_limit',defaults['integral_limit'])))

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
                # Send a stop command — all motors coast, PID disabled, PWM 0
                stop_packet = [0x55, 0x03,
                               0x00, 0x00,  # M1 coast, PWM 0
                               0x00, 0x00,  # M2 coast, PWM 0
                               0x00, 0x00, 0x00,  # M1 PID off, setpoint 0
                               0x00, 0x00, 0x00]  # M2 PID off, setpoint 0
                self.serial_port.write(bytes(stop_packet))
                time.sleep(0.05)  # give firmware time to process
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

    style.configure("ActiveDir.TButton",   background="green",  foreground="white")
    style.configure("ActiveStop.TButton",  background="red",    foreground="white")
    style.configure("ActiveBrake.TButton", background="orange", foreground="black")

    style.map("ActiveDir.TButton",   background=[("!disabled", "green")],  foreground=[("!disabled", "white")])
    style.map("ActiveStop.TButton",  background=[("!disabled", "red")],    foreground=[("!disabled", "white")])
    style.map("ActiveBrake.TButton", background=[("!disabled", "orange")], foreground=[("!disabled", "black")])

    app = MotorControlGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()