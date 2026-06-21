"""
2-Motor USB CDC Control GUI with Encoder Readback

Cross-platform (Windows and Linux, including Raspberry Pi) Tkinter GUI
for controlling 2 motors and displaying live encoder counts read back
over the same USB CDC serial connection.

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
    for 5-byte packets of the form:

        [0xAA, enc1_lo, enc1_hi, enc2_lo, enc2_hi]

    - Byte 0      : header / sync byte (0xAA)
    - Bytes 1-2   : Motor 1 encoder count, signed 16-bit, little-endian
    - Bytes 3-4   : Motor 2 encoder count, signed 16-bit, little-endian

    This is a placeholder default since the actual firmware framing
    wasn't specified. All parsing logic lives in
    SerialReader._try_parse_packet() - if your firmware sends a
    different format (e.g. ASCII lines like "E1:1234,E2:-56\\n", or a
    different packet size/header), that's the only method that needs
    to change.

    The GUI polls for new data every 50ms (~20Hz).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import serial
import serial.tools.list_ports
import threading
import queue
import struct
import time

NUM_MOTORS = 2

# Known (VID, PID) pairs for the motor controller's USB CDC interface.
# Add your board's IDs here for reliable auto-detection on both Windows
# and Linux/Pi. Click "Refresh Ports" to print the VID/PID of every
# connected serial device to the console, then add the matching pair, e.g.:
#     KNOWN_VID_PID = [(0x2E8A, 0x0005)]
KNOWN_VID_PID = [
    # (0x1234, 0x5678),
]

# --- Encoder packet format (placeholder - adjust to match firmware) ---
ENCODER_HEADER      = 0xAA
ENCODER_PACKET_SIZE = 1 + (4 * NUM_MOTORS)  # header + 4 bytes per motor

# How often the GUI checks for newly-arrived encoder data.
POLL_INTERVAL_MS = 50  # ~20Hz


def printHex(input):
    return ' '.join(f'{c:0>2X}' for c in input)


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
        the [0xAA, enc1_lo, enc1_hi, enc2_lo, enc2_hi] placeholder.
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
                # '<' little-endian, 'h' signed 16-bit, one per motor
                #old values = struct.unpack(f'<{NUM_MOTORS}h', packet[1:])
                values = struct.unpack(f'<{NUM_MOTORS}i', packet[1:])
            except struct.error:
                continue  # malformed packet, keep scanning

            encoder_values = {m: values[m - 1] for m in range(1, NUM_MOTORS + 1)}
            self.data_queue.put(encoder_values)


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
        speed_slider = ttk.Scale(self, from_=0, to=100, orient="horizontal",
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
        ttk.Label(self, text="Encoder").grid(row=5, column=0, columnspan=2)
        self.encoder_value_var = tk.StringVar(value="--")
        self.encoder_label = ttk.Label(self, textvariable=self.encoder_value_var,
                                        font=("TkDefaultFont", 14, "bold"))
        self.encoder_label.grid(row=6, column=0, columnspan=2, pady=(0, 5))

    def update_encoder(self, value):
        self.encoder_value_var.set(str(value))

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


class MotorControlGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("2-Motor USB CDC Control")
        self.serial_port = None
        self.serial_reader = None
        self.encoder_queue = queue.Queue()

        # --- USB connection controls ---
        detect_frame = ttk.Frame(root)
        detect_frame.pack(pady=5)

        ttk.Button(detect_frame, text="Auto-Detect", command=self.detect_usb_device).pack(side="left", padx=5)

        self.port_var = tk.StringVar()
        self.port_combo = ttk.Combobox(detect_frame, textvariable=self.port_var, width=22, state="readonly")
        self.port_combo.pack(side="left", padx=5)

        ttk.Button(detect_frame, text="Refresh Ports", command=self.refresh_ports).pack(side="left", padx=5)
        ttk.Button(detect_frame, text="Connect", command=self.connect_selected_port).pack(side="left", padx=5)

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
        """Runs on the Tkinter main thread via root.after(). Drains any
        encoder readings the background SerialReader thread has queued
        and updates the corresponding panel labels. Never touches the
        serial port directly - only the queue - so it's safe to call
        from here."""
        try:
            latest = None
            while True:
                latest = self.encoder_queue.get_nowait()
        except queue.Empty:
            pass

        if latest:
            for panel in self.motor_frames:
                if panel.motor_id in latest:
                    panel.update_encoder(latest[panel.motor_id])

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