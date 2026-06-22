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

Encoder read protocol (ADJUST TO MATCH YOUR FIRMWARE):
    A background thread continuously reads from the serial port looking
    for 9-byte packets of the form:

        [0xAA, enc1_b0, enc1_b1, enc1_b2, enc1_b3, enc2_b0, enc2_b1, enc2_b2, enc2_b3]

    - Byte 0      : header / sync byte (0xAA)
    - Bytes 1-4   : Motor 1 encoder count, signed 32-bit, little-endian
    - Bytes 5-8   : Motor 2 encoder count, signed 32-bit, little-endian

    This is a placeholder default since the actual firmware framing
    wasn't specified. All parsing logic lives in
    SerialReader._try_parse_packet() - if your firmware sends a
    different format (e.g. ASCII lines like "E1:1234,E2:-56\\n", or a
    different packet size/header), that's the only method that needs
    to change.

    The GUI polls for new data every 50ms (~20Hz). Each received count
    is treated as "encoder counts since the last poll" (a delta, not an
    absolute position) for the purpose of RPM calculation.

RPM conversion:
    output_shaft_RPM = (delta_counts / (PPR * gear_ratio)) * (60 / elapsed_sec)

    Where elapsed_sec is the actual time between consecutive received
    packets, measured by timestamping each packet in the SerialReader
    thread at arrival. This makes RPM accurate regardless of how often
    the firmware sends encoder packets — no fixed send rate is assumed.
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

NUM_MOTORS = 2

# Settings file lives next to this script so it travels with it.
CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "motor_config.json")

# Sensible defaults until the user sets real values in the Settings window.
DEFAULT_PPR = 12          # pulses per revolution (encoder/motor shaft)
DEFAULT_GEAR_RATIO = 1.0  # motor shaft revs per output shaft rev (e.g. 100.0 for a 100:1 gearbox)

# Known (VID, PID) pairs for the motor controller's USB CDC interface.
# Add your board's IDs here for reliable auto-detection on both Windows
# and Linux/Pi. Click "Refresh Ports" to print the VID/PID of every
# connected serial device to the console, then add the matching pair, e.g.:
#     KNOWN_VID_PID = [(0x2E8A, 0x0005)]
KNOWN_VID_PID = [
    # (0x1234, 0x5678),
]

# --- Encoder packet format (placeholder - adjust to match firmware) ---
ENCODER_HEADER = 0xAA
ENCODER_PACKET_SIZE = 1 + (4 * NUM_MOTORS)  # header + 4 bytes per motor

# Values are unpacked as signed 32-bit ('l' in struct format), so the
# raw reading wraps at this range. Used to correct deltas computed
# across a wraparound (e.g. near the int32 boundary). If you change the
# struct format in SerialReader._try_parse_packets, update this to
# match (2**16 for 16-bit, 2**32 for 32-bit, etc).
RAW_VALUE_RANGE = 4294967296  # 2**32

# How often the GUI checks for newly-arrived encoder data.
POLL_INTERVAL_MS = 50  # ~20Hz
POLL_INTERVAL_SEC = POLL_INTERVAL_MS / 1000.0

# If no encoder packet arrives for this long, the live RPM and
# direction labels are blanked so stale values aren't mistaken for
# current readings. Stats (avg/min/max) are preserved.
STALE_TIMEOUT_SEC = 0.5

# Whether each value read off the wire is an ABSOLUTE encoder position
# (counts since power-on/reset - the common case, and counts UP/DOWN
# continuously even while sitting idle) or already a DELTA (counts since
# the previous poll). Get this wrong and RPM will be wildly inflated
# (absolute position misread as a delta) or always read ~0 (delta
# misread as absolute and re-diffed again).
READING_MODE_ABSOLUTE = "absolute"
READING_MODE_DELTA = "delta"
READING_MODE = READING_MODE_ABSOLUTE


def printHex(input):
    return ' '.join(f'{c:0>2X}' for c in input)


# ----------------------------------------------------------------------
# Per-motor configuration (PPR + gear ratio) with JSON persistence
# ----------------------------------------------------------------------

def default_motor_config():
    """Return a fresh config dict: {motor_id: {"ppr": .., "gear_ratio": ..}}"""
    return {
        str(m): {"ppr": DEFAULT_PPR, "gear_ratio": DEFAULT_GEAR_RATIO}
        for m in range(1, NUM_MOTORS + 1)
    }


def load_motor_config():
    """Load motor config from CONFIG_PATH, falling back to defaults for
    any motor missing or malformed. Never raises - a bad/missing file
    just means defaults are used."""
    config = default_motor_config()

    if not os.path.exists(CONFIG_PATH):
        return config

    try:
        with open(CONFIG_PATH, "r") as f:
            loaded = json.load(f)
        for motor_key, defaults in config.items():
            entry = loaded.get(motor_key, {})
            ppr = entry.get("ppr", defaults["ppr"])
            gear_ratio = entry.get("gear_ratio", defaults["gear_ratio"])
            try:
                ppr = float(ppr)
                gear_ratio = float(gear_ratio)
                if ppr <= 0 or gear_ratio <= 0:
                    raise ValueError
                config[motor_key] = {"ppr": ppr, "gear_ratio": gear_ratio}
            except (TypeError, ValueError):
                pass  # keep the default for this motor
    except (json.JSONDecodeError, OSError):
        pass  # keep all defaults

    return config


def save_motor_config(config):
    """Write motor config to CONFIG_PATH. Returns True on success."""
    try:
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        return True
    except OSError:
        return False


class SerialReader(threading.Thread):
    """
    Background thread that continuously reads bytes from an open serial
    port, looks for encoder packets, and pushes decoded (motor_id ->
    count) dicts onto a thread-safe queue for the GUI thread to consume.

    Runs independently of the write side - the same serial_port object
    is shared, which is safe because pyserial read()/write() are
    typically safe to call from different threads on POSIX and Windows
    backends as long as each call only touches its own direction.
    """

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
                # Port likely closed/unplugged; stop quietly and let the
                # GUI's connection state handle user notification.
                break
            except Exception:
                # Never let a malformed/unexpected byte stream kill the
                # reader thread.
                self._buffer.clear()
                time.sleep(0.01)

    def _try_parse_packets(self):
        """Scan the buffer for complete encoder packets, decode each one
        found, and discard consumed/garbage bytes.

        ADJUST THIS METHOD if your firmware's read format differs from
        the [0xAA, enc1_b0..b3, enc2_b0..b3] placeholder.
        """
        while True:
            # Drop bytes until we find the header.
            header_index = self._buffer.find(bytes([ENCODER_HEADER]))
            if header_index == -1:
                self._buffer.clear()
                return
            if header_index > 0:
                del self._buffer[:header_index]

            if len(self._buffer) < ENCODER_PACKET_SIZE:
                return  # wait for more bytes

            packet = bytes(self._buffer[:ENCODER_PACKET_SIZE])
            del self._buffer[:ENCODER_PACKET_SIZE]

            try:
                # '<' little-endian, 'l' signed 32-bit, one per motor
                values = struct.unpack(f'<{NUM_MOTORS}l', packet[1:])
            except struct.error:
                continue  # malformed packet, keep scanning

            encoder_values = {m: values[m - 1] for m in range(1, NUM_MOTORS + 1)}
            # Capture wall-clock time at the moment this packet was
            # fully received. The GUI thread uses the elapsed time
            # between consecutive packets (per motor) as the actual
            # interval divisor for RPM, rather than assuming a fixed
            # POLL_INTERVAL_SEC that's only valid if firmware sends
            # at a perfectly regular rate.
            self.data_queue.put((time.monotonic(), encoder_values))


class MotorControlPanel(ttk.LabelFrame):
    def __init__(self, parent, motor_id, send_command):
        super().__init__(parent, text=f"Motor {motor_id}")
        self.motor_id = motor_id
        self.send_command = send_command
        self.speed_var = tk.IntVar()

        self.motor_in1 = 0
        self.motor_in2 = 0
        self.motor_pwm = 0

        # Speed Slider
        ttk.Label(self, text="Speed").grid(row=0, column=0, columnspan=2, pady=5)
        speed_slider = ttk.Scale(self, from_=0, to=255, orient="horizontal",
                                 variable=self.speed_var, command=self.on_speed_change)
        speed_slider.grid(row=1, column=0, columnspan=2, padx=10, sticky="ew")

        # Direction Buttons
        self.btn_ccw = ttk.Button(self, text="CCW", style="Dir.TButton", command=self.set_CCW)
        self.btn_ccw.grid(row=2, column=0, pady=5, sticky="ew")

        self.btn_cw  = ttk.Button(self, text="CW",  style="Dir.TButton", command=self.set_CW)
        self.btn_cw.grid(row=2, column=1, pady=5, sticky="ew")

        # Stop and Brake Buttons
        self.btn_stop = ttk.Button(self, text="Stop",  style="Stop.TButton", command=self.stop_motor)
        self.btn_stop.grid(row=3, column=0, pady=5)

        self.btn_brake = ttk.Button(self, text="Brake", style="Brake.TButton", command=self.brake_motor)
        self.btn_brake.grid(row=3, column=1, pady=5)

        # Encoder readout
        ttk.Separator(self, orient="horizontal").grid(row=4, column=0, columnspan=2, sticky="ew", pady=(10, 5))
        ttk.Label(self, text="Output Shaft RPM").grid(row=5, column=0, columnspan=2)
        self.rpm_value_var = tk.StringVar(value="--")
        self.rpm_label = ttk.Label(self, textvariable=self.rpm_value_var,
                                    font=("TkDefaultFont", 16, "bold"))
        self.rpm_label.grid(row=6, column=0, columnspan=2)

        self.direction_var = tk.StringVar(value="")
        self.direction_label = ttk.Label(self, textvariable=self.direction_var)
        self.direction_label.grid(row=7, column=0, columnspan=2, pady=(0, 5))

        self.raw_count_var = tk.StringVar(value="raw: --")
        ttk.Label(self, textvariable=self.raw_count_var, foreground="gray").grid(
            row=8, column=0, columnspan=2, pady=(0, 2))

        # RPM stats: rolling average, min, max.
        # Rolling window of RPM_WINDOW_SIZE samples (~1 second at 20Hz).
        # Min/max accumulate across the run and reset with the button.
        # Only non-zero samples are included, so a stopped/idle motor
        # doesn't drag the average or min down between runs.
        ttk.Separator(self, orient="horizontal").grid(row=9, column=0, columnspan=2, sticky="ew", pady=(5, 5))

        stats_frame = ttk.Frame(self)
        stats_frame.grid(row=10, column=0, columnspan=2, sticky="ew", padx=4)
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
        stats_frame.columnconfigure(2, weight=1)

        ttk.Label(stats_frame, text="Avg",  anchor="center").grid(row=0, column=0, sticky="ew")
        ttk.Label(stats_frame, text="Min",  anchor="center").grid(row=0, column=1, sticky="ew")
        ttk.Label(stats_frame, text="Max",  anchor="center").grid(row=0, column=2, sticky="ew")

        self.avg_var = tk.StringVar(value="--")
        self.min_var = tk.StringVar(value="--")
        self.max_var = tk.StringVar(value="--")

        ttk.Label(stats_frame, textvariable=self.avg_var, anchor="center",
                  font=("TkDefaultFont", 10, "bold")).grid(row=1, column=0, sticky="ew")
        ttk.Label(stats_frame, textvariable=self.min_var, anchor="center",
                  font=("TkDefaultFont", 10, "bold"), foreground="steelblue").grid(row=1, column=1, sticky="ew")
        ttk.Label(stats_frame, textvariable=self.max_var, anchor="center",
                  font=("TkDefaultFont", 10, "bold"), foreground="firebrick").grid(row=1, column=2, sticky="ew")

        self._rpm_window = []       # rolling window for average
        self._rpm_min = None
        self._rpm_max = None

        # Cumulative total count — accumulates deltas from zero on
        # connect (or last reset), so it can be directly compared
        # against firmware's motor1_count printed over UART on stop.
        ttk.Separator(self, orient="horizontal").grid(row=11, column=0, columnspan=2, sticky="ew", pady=(5, 5))
        ttk.Label(self, text="Total Count").grid(row=12, column=0, columnspan=2)
        self._total_count = 0
        self.total_count_var = tk.StringVar(value="0")
        ttk.Label(self, textvariable=self.total_count_var,
                  font=("TkDefaultFont", 13, "bold")).grid(row=13, column=0, columnspan=2)

        ttk.Button(self, text="Reset Stats", command=self.reset_stats).grid(
            row=14, column=0, columnspan=2, pady=(4, 6))

    # Rolling window size: number of RPM samples to average over.
    # 20 samples at 20Hz = ~1 second of smoothing. Increase for
    # more smoothing, decrease for faster response.
    RPM_WINDOW_SIZE = 20

    def clear_live_rpm(self):
        """Called when no packet has arrived for STALE_TIMEOUT_SEC.
        Blanks the live RPM and direction so stale values aren't
        mistaken for current readings. Stats (avg/min/max) are
        preserved so the run history is still visible."""
        self.rpm_value_var.set("--")
        self.direction_var.set("")
        self.raw_count_var.set("raw: --")

    def reset_stats(self):
        self._total_count = 0
        self.total_count_var.set("0")
        self._rpm_window.clear()
        self._rpm_min = None
        self._rpm_max = None
        self.avg_var.set("--")
        self.min_var.set("--")
        self.max_var.set("--")

    def reset_total_count(self):
        """Called on reconnect — resets count only, preserving RPM
        stats so a reconnect mid-session doesn't wipe them."""
        self._total_count = 0
        self.total_count_var.set("0")

    def update_encoder(self, delta_counts, ppr, gear_ratio, elapsed_sec):
        """Convert a raw encoder delta and real elapsed time since the
        previous packet into output-shaft RPM. Using the actual
        inter-packet interval (rather than a fixed assumed poll rate)
        makes RPM accurate regardless of how often the firmware sends."""
        self.raw_count_var.set(
            f"raw: {delta_counts:+d} counts  {elapsed_sec*1000:.0f}ms")

        self._total_count += delta_counts
        self.total_count_var.set(str(self._total_count))

        counts_per_output_rev = ppr * gear_ratio
        if counts_per_output_rev <= 0:
            self.rpm_value_var.set("--")
            self.direction_var.set("(invalid config)")
            return

        revs = delta_counts / counts_per_output_rev
        rpm  = abs(revs) * (60.0 / elapsed_sec)

        self.rpm_value_var.set(f"{rpm:.1f}")

        if delta_counts > 0:
            self.direction_var.set("CW")
        elif delta_counts < 0:
            self.direction_var.set("CCW")
        else:
            self.direction_var.set("stopped")

        # Only include non-zero RPM in stats so idle polls between
        # runs don't drag down the average or set a spurious min of 0.
        if rpm > 0:
            self._rpm_window.append(rpm)
            if len(self._rpm_window) > self.RPM_WINDOW_SIZE:
                self._rpm_window.pop(0)

            if self._rpm_min is None or rpm < self._rpm_min:
                self._rpm_min = rpm
            if self._rpm_max is None or rpm > self._rpm_max:
                self._rpm_max = rpm

            avg = sum(self._rpm_window) / len(self._rpm_window)
            self.avg_var.set(f"{avg:.1f}")
            self.min_var.set(f"{self._rpm_min:.1f}")
            self.max_var.set(f"{self._rpm_max:.1f}")

    def on_speed_change(self, val):
        self.motor_pwm  = int(float(val))
        self.send_command()

    def reset_direction_styles(self):
        self.btn_cw.configure(style="Dir.TButton")
        self.btn_ccw.configure(style="Dir.TButton")
        self.btn_stop.configure(style="Stop.TButton")
        self.btn_brake.configure(style="Brake.TButton")

    def set_CCW(self):
        self.motor_in1 = 0
        self.motor_in2 = 1
        self.reset_direction_styles()
        self.btn_ccw.configure(style="ActiveDir.TButton")
        self.send_command()

    def set_CW(self):
        self.motor_in1 = 1
        self.motor_in2 = 0
        self.reset_direction_styles()
        self.btn_cw.configure(style="ActiveDir.TButton")
        self.send_command()

    def stop_motor(self):
        self.motor_in1 = 0
        self.motor_in2 = 0
        self.reset_direction_styles()
        self.btn_stop.configure(style="ActiveStop.TButton")
        self.send_command()

    def brake_motor(self):
        self.motor_in1 = 1
        self.motor_in2 = 1
        self.reset_direction_styles()
        self.btn_brake.configure(style="ActiveBrake.TButton")
        self.send_command()


class SettingsWindow(tk.Toplevel):
    """
    Modal-ish settings window for editing per-motor PPR (pulses per
    revolution) and gear ratio, used to convert raw encoder counts into
    output-shaft RPM. Changes are written to motor_config.json and take
    effect immediately (no restart needed) via the on_save callback.
    """

    def __init__(self, parent, current_config, on_save):
        super().__init__(parent)
        self.title("Motor Settings")
        self.resizable(False, False)
        self.on_save = on_save
        self.transient(parent)

        self.entries = {}  # motor_id -> {"ppr": StringVar, "gear_ratio": StringVar}

        container = ttk.Frame(self, padding=10)
        container.pack(fill="both", expand=True)

        ttk.Label(container, text="Encoder & Gearbox Configuration",
                  font=("TkDefaultFont", 11, "bold")).grid(
            row=0, column=0, columnspan=3, pady=(0, 10))

        ttk.Label(container, text="Motor").grid(row=1, column=0, padx=5, pady=2)
        ttk.Label(container, text="PPR (pulses/rev)").grid(row=1, column=1, padx=5, pady=2)
        ttk.Label(container, text="Gear Ratio").grid(row=1, column=2, padx=5, pady=2)

        for row_offset, motor_id in enumerate(range(1, NUM_MOTORS + 1)):
            r = row_offset + 2
            motor_key = str(motor_id)
            motor_cfg = current_config.get(motor_key, {"ppr": DEFAULT_PPR, "gear_ratio": DEFAULT_GEAR_RATIO})

            ttk.Label(container, text=f"Motor {motor_id}").grid(row=r, column=0, padx=5, pady=4)

            ppr_var = tk.StringVar(value=str(motor_cfg["ppr"]))
            ppr_entry = ttk.Entry(container, textvariable=ppr_var, width=10, justify="center")
            ppr_entry.grid(row=r, column=1, padx=5, pady=4)

            gear_var = tk.StringVar(value=str(motor_cfg["gear_ratio"]))
            gear_entry = ttk.Entry(container, textvariable=gear_var, width=10, justify="center")
            gear_entry.grid(row=r, column=2, padx=5, pady=4)

            self.entries[motor_key] = {"ppr": ppr_var, "gear_ratio": gear_var}

        hint = ("Gear ratio = motor shaft revolutions per output shaft revolution.\n"
                "Use 1.0 if there is no gearbox.")
        ttk.Label(container, text=hint, foreground="gray", justify="left").grid(
            row=NUM_MOTORS + 2, column=0, columnspan=3, pady=(8, 8), sticky="w")

        self.error_var = tk.StringVar(value="")
        ttk.Label(container, textvariable=self.error_var, foreground="red").grid(
            row=NUM_MOTORS + 3, column=0, columnspan=3)

        button_frame = ttk.Frame(container)
        button_frame.grid(row=NUM_MOTORS + 4, column=0, columnspan=3, pady=(8, 0))
        ttk.Button(button_frame, text="Save", command=self._save).pack(side="left", padx=5)
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side="left", padx=5)

        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _save(self):
        new_config = {}
        for motor_key, vars in self.entries.items():
            try:
                ppr = float(vars["ppr"].get())
                gear_ratio = float(vars["gear_ratio"].get())
                if ppr <= 0 or gear_ratio <= 0:
                    raise ValueError
            except ValueError:
                self.error_var.set(f"Motor {motor_key}: PPR and gear ratio must be positive numbers.")
                return
            new_config[motor_key] = {"ppr": ppr, "gear_ratio": gear_ratio}

        if save_motor_config(new_config):
            self.on_save(new_config)
            self.destroy()
        else:
            self.error_var.set(f"Failed to write {CONFIG_PATH}. Check file permissions.")


class MotorControlGUI:
    # Maximum encoder packets processed per 50ms GUI tick. Caps the
    # time spent in _poll_encoder_queue so Tkinter stays responsive
    # even if the firmware sends flat-out. Any excess packets remain
    # in the queue and are processed on the next tick. Raise this if
    # you need higher stat fidelity; lower it if the GUI still lags.
    MAX_PACKETS_PER_TICK = 20

    def __init__(self, root):
        self.root = root
        self.root.title("2-Motor USB CDC Control")
        self.serial_port = None
        self.serial_reader = None
        self.encoder_queue = queue.Queue()
        self.motor_config = load_motor_config()
        self.settings_window = None

        # Last raw value seen per motor, used to compute a delta when
        # READING_MODE is "absolute". Reset to None on each new
        # connection so a stale value from a previous session can't
        # produce a bogus first-sample delta.
        self._last_raw_value = {m: None for m in range(1, NUM_MOTORS + 1)}

        # Timestamp (time.monotonic()) of the last received packet per
        # motor. Used to compute the true inter-packet interval for RPM
        # instead of assuming a fixed POLL_INTERVAL_SEC.
        self._last_packet_time = {m: None for m in range(1, NUM_MOTORS + 1)}

        # --- USB connection controls ---
        detect_frame = ttk.Frame(root)
        detect_frame.pack(pady=5)

        ttk.Button(detect_frame, text="Auto-Detect", command=self.detect_usb_device).pack(side="left", padx=5)

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(detect_frame, textvariable=self.port_var, width=22, state="readonly")
        self.port_combo.pack(side="left", padx=5)

        ttk.Button(detect_frame, text="Refresh Ports", command=self.refresh_ports).pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Connect", command=self.connect_selected_port).pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Settings...", command=self.open_settings).pack(side="left", padx=5)

        self.status_label = ttk.Label(root, text="Status: Not connected")
        self.status_label.pack(pady=5)

        self.refresh_ports()

        # Motor Panels
        self.motor_frames = []
        motors_frame = ttk.Frame(root)
        motors_frame.pack(padx=10, pady=10)
        for i in range(1, NUM_MOTORS + 1):
            panel = MotorControlPanel(motors_frame, i, self.send_command)
            panel.grid(row=0, column=i - 1, padx=10, pady=10, sticky="nsew")
            self.motor_frames.append(panel)

        # Kick off the GUI-side polling loop (reads from encoder_queue,
        # which the background SerialReader thread fills).
        self.root.after(POLL_INTERVAL_MS, self._poll_encoder_queue)

    # ------------------------------------------------------------------
    # Settings
    # ------------------------------------------------------------------

    def open_settings(self):
        # Avoid opening multiple settings windows at once.
        if self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_set()
            return

        self.settings_window = SettingsWindow(self.root, self.motor_config, self._on_settings_saved)

    def _on_settings_saved(self, new_config):
        self.motor_config = new_config

    # ------------------------------------------------------------------
    # Port discovery / connection
    # ------------------------------------------------------------------

    def refresh_ports(self):
        """Repopulate the port dropdown and print details of each detected
        port to the console (handy for finding a device's VID/PID to add
        to KNOWN_VID_PID for reliable auto-detect)."""
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

        # 1) Prefer matching by VID/PID - consistent across Windows and Linux,
        #    unlike the description string below.
        for port in ports:
            if (port.vid, port.pid) in KNOWN_VID_PID:
                return port.device

        # 2) Fall back to matching common substrings in the description.
        #    Windows often reports "USB Serial Device", while Linux/Pi
        #    commonly reports "USB ACM Device", "CDC ACM", or sometimes
        #    nothing useful at all.
        cdc_keywords = (keyword.lower(), "cdc", "acm")
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
                "Select a port from the dropdown and click Connect."
            )

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

            # Discard any stale absolute readings from a previous
            # connection so the first delta computed isn't bogus.
            self._last_raw_value = {m: None for m in range(1, NUM_MOTORS + 1)}
            self._last_packet_time = {m: None for m in range(1, NUM_MOTORS + 1)}

            # Reset each panel's cumulative count so it starts from
            # zero on each new connection, matching firmware's
            # motor1_count which is typically zero at power-on.
            for panel in self.motor_frames:
                panel.reset_total_count()

            self.serial_reader = SerialReader(self.serial_port, self.encoder_queue)
            self.serial_reader.start()

        except serial.SerialException as e:
            messagebox.showerror("Connection Error", f"Failed to open {device}:\n{e}")
            self.status_label.config(text="Status: Not connected")

    def _stop_reader(self):
        if self.serial_reader and self.serial_reader.is_alive():
            self.serial_reader.stop()
            self.serial_reader.join(timeout=1)
        self.serial_reader = None

    # ------------------------------------------------------------------
    # Encoder polling (GUI-thread side)
    # ------------------------------------------------------------------

    def _poll_encoder_queue(self):
        """Runs on the Tkinter main thread via root.after(). Drains up
        to MAX_PACKETS_PER_TICK encoder packets per call, leaving any
        remainder for the next tick. This prevents the main thread from
        stalling on a large burst from the firmware, which would cause
        the GUI to freeze. Each packet is processed individually with
        its own arrival timestamp so RPM is accurate regardless of send
        rate. Never touches the serial port directly - only the queue."""
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

                if READING_MODE == READING_MODE_ABSOLUTE:
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
                else:
                    delta_counts = raw_value

                last_t = self._last_packet_time[motor_id]
                if last_t is not None and latest_ts > last_t:
                    elapsed_sec = latest_ts - last_t
                else:
                    elapsed_sec = POLL_INTERVAL_SEC
                self._last_packet_time[motor_id] = latest_ts

                motor_key = str(motor_id)
                cfg = self.motor_config.get(
                    motor_key, {"ppr": DEFAULT_PPR, "gear_ratio": DEFAULT_GEAR_RATIO})
                panel.update_encoder(delta_counts, cfg["ppr"], cfg["gear_ratio"],
                                     elapsed_sec)

        # Blank live RPM/direction for any motor that hasn't sent a
        # packet recently, so stale values aren't mistaken for current
        # readings when the motor is stopped or firmware goes quiet.
        now = time.monotonic()
        for panel in self.motor_frames:
            last_t = self._last_packet_time[panel.motor_id]
            if last_t is not None and (now - last_t) > STALE_TIMEOUT_SEC:
                panel.clear_live_rpm()
                # Reset to None so clear_live_rpm is only called once
                # per stale event, not every tick until a new packet arrives.
                self._last_packet_time[panel.motor_id] = None
                self._last_raw_value[panel.motor_id] = None

        self.root.after(POLL_INTERVAL_MS, self._poll_encoder_queue)

    # ------------------------------------------------------------------
    # Command sending
    # ------------------------------------------------------------------

    def send_command(self):

        cdcdata = [3] + [0] * (2 * NUM_MOTORS)
        #Byte 0 : [1]   enable motors 2 and 3
        #         [0]   enable motors 0 and 1

        #Byte 1 : [1]   M0 IN 2
        #         [0]   M0 IN 1

        #Byte 2 : [7:0] M0 PWM

        ##repeats

        for panel in self.motor_frames:
            motor_id  = panel.motor_id
            motor_in1 = panel.motor_in1
            motor_in2 = panel.motor_in2
            speed     = panel.motor_pwm

            if motor_in1 == 1:
                cdcdata[(motor_id*2)-1] = cdcdata[(motor_id*2)-1] + 1
            if motor_in2 == 1:
                cdcdata[(motor_id*2)-1] = cdcdata[(motor_id*2)-1] + 2

            cdcdata[motor_id*2] = speed

        print(printHex(cdcdata))

        if self.serial_port and self.serial_port.is_open:
            try:
                self.serial_port.write(bytes(cdcdata))
                # Reset timestamps only for motors that are coast-stopped
                # (in1=0 AND in2=0). A pwm=0 with direction set, a speed
                # change, or a brake all leave timing intact.
                for panel in self.motor_frames:
                    if panel.motor_in1 == 0 and panel.motor_in2 == 0:
                        self._last_packet_time[panel.motor_id] = None
                        self._last_raw_value[panel.motor_id]   = None
            except serial.SerialException as e:
                messagebox.showerror("Serial Error", f"Failed to send command:\n{e}")
        else:
            messagebox.showwarning("Not Connected", "Please connect to a USB CDC device first.")

    def on_close(self):
        self._stop_reader()
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use("clam")   # important: clam respects background/foreground

    # Active styles
    style.configure("ActiveDir.TButton",   background="green",  foreground="white")
    style.configure("ActiveStop.TButton",  background="red",    foreground="white")
    style.configure("ActiveBrake.TButton", background="orange", foreground="black")

    # Some platforms (esp. macOS) need map() to enforce colors
    style.map("ActiveDir.TButton",   background=[("!disabled", "green")],  foreground=[("!disabled", "white")])
    style.map("ActiveStop.TButton",  background=[("!disabled", "red")],    foreground=[("!disabled", "white")])
    style.map("ActiveBrake.TButton", background=[("!disabled", "orange")], foreground=[("!disabled", "black")])

    app = MotorControlGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()