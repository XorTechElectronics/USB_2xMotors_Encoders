"""
motor_driver.py

Reusable driver class for the 4-motor USB CDC controller.

Wraps the same packet format used by motor_control_gui.py:

    Byte 0 : enable flags (always 3 - both motor pairs enabled)
    Byte 1 : M0 direction bits  [bit0 = IN1, bit1 = IN2]
    Byte 2 : M0 PWM (0-255)
    Byte 3 : M1 direction bits
    Byte 4 : M1 PWM (0-255)
    Byte 5 : M2 direction bits
    Byte 6 : M2 PWM (0-255)
    Byte 7 : M3 direction bits
    Byte 8 : M3 PWM (0-255)

Direction bits per motor:
    IN1=0, IN2=0  -> coast / stop
    IN1=1, IN2=0  -> CW
    IN1=0, IN2=1  -> CCW
    IN1=1, IN2=1  -> brake

Cross-platform (Windows + Linux/Raspberry Pi) via pyserial.
Linux/Pi notes:
    - Install:  pip3 install pyserial
    - Add your user to the dialout group for serial port access:
          sudo usermod -aG dialout $USER   (then log out/in)
    - Devices typically show up as /dev/ttyACM0 or /dev/ttyUSB0
"""

import time
import serial
import serial.tools.list_ports

NUM_MOTORS = 4
MIN_PWM = 0
MAX_PWM = 255

# Direction constants
STOP  = "stop"
BRAKE = "brake"
CW    = "cw"
CCW   = "ccw"

# Known (VID, PID) pairs for the controller's USB CDC interface.
# Fill in with values found via MotorDriver.list_ports() for reliable
# auto-detection on both Windows and Linux/Pi.
KNOWN_VID_PID = [
    # (0x1234, 0x5678),
]


def _direction_bits(direction):
    """Translate a direction constant into (in1, in2) bits."""
    mapping = {
        STOP:  (0, 0),
        CW:    (1, 0),
        CCW:   (0, 1),
        BRAKE: (1, 1),
    }
    if direction not in mapping:
        raise ValueError(f"Unknown direction '{direction}'. "
                          f"Use one of: {', '.join(mapping)}")
    return mapping[direction]


class MotorDriverError(Exception):
    """Raised for driver-level errors (not connected, bad args, etc.)."""
    pass


class MotorDriver:
    """
    Controls a 4-motor USB CDC controller board.

    Typical usage:
        driver = MotorDriver()
        driver.connect()                  # auto-detect a port
        driver.set_motor(1, MotorDriver.CW, 50)
        driver.stop_all()
        driver.close()

    Or as a context manager:
        with MotorDriver(port="/dev/ttyACM0") as driver:
            driver.set_motor(1, MotorDriver.CW, 50)
    """

    # Re-exposed here so callers can do MotorDriver.CW etc. without a
    # separate import.
    STOP  = STOP
    BRAKE = BRAKE
    CW    = CW
    CCW   = CCW

    def __init__(self, port=None, baudrate=115200, timeout=1):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.serial_port = None

        # Track current state per motor (1-indexed, like the GUI) so we
        # can resend the full packet when only one motor changes.
        self._state = {
            m: {"in1": 0, "in2": 0, "pwm": 0} for m in range(1, NUM_MOTORS + 1)
        }

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    @staticmethod
    def list_ports():
        """Return a list of (device, vid, pid, description) for every
        detected serial port. Useful for finding VID/PID to add to
        KNOWN_VID_PID."""
        results = []
        for p in serial.tools.list_ports.comports():
            results.append((p.device, p.vid, p.pid, p.description or ""))
        return results

    @staticmethod
    def find_device(keyword="USB Serial"):
        """Search connected serial ports for a likely USB CDC motor
        controller. Tries VID/PID first (works identically on Windows
        and Linux/Pi), then falls back to description substring
        matching."""
        ports = serial.tools.list_ports.comports()

        for p in ports:
            if (p.vid, p.pid) in KNOWN_VID_PID:
                return p.device

        cdc_keywords = (keyword.lower(), "cdc", "acm")
        for p in ports:
            description = (p.description or "").lower()
            if any(k in description for k in cdc_keywords):
                return p.device

        return None

    def connect(self, port=None):
        """Open the serial connection. If no port is given (here or in
        the constructor), attempts auto-detection."""
        target = port or self.port or self.find_device()
        if not target:
            raise MotorDriverError(
                "No port specified and no USB CDC device could be "
                "auto-detected. Use MotorDriver.list_ports() to see "
                "available ports."
            )
        try:
            self.serial_port = serial.Serial(target, baudrate=self.baudrate,
                                              timeout=self.timeout)
        except serial.SerialException as e:
            raise MotorDriverError(f"Failed to open {target}: {e}") from e

        self.port = target
        return self.port

    @property
    def is_connected(self):
        return self.serial_port is not None and self.serial_port.is_open

    def close(self):
        """Stop all motors and close the serial port."""
        if self.is_connected:
            try:
                self.stop_all()
            except MotorDriverError:
                pass
            self.serial_port.close()
        self.serial_port = None

    def __enter__(self):
        if not self.is_connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    # ------------------------------------------------------------------
    # Motor control
    # ------------------------------------------------------------------

    def set_motor(self, motor_id, direction, speed=None):
        """
        Set a single motor's direction and (optionally) speed, then send
        the full 4-motor packet.

        motor_id  : 1-4
        direction : MotorDriver.CW, .CCW, .STOP, or .BRAKE
        speed     : 0-255 (PWM percent). If omitted, keeps the motor's
                    current speed.
        """
        self._validate_motor_id(motor_id)
        in1, in2 = _direction_bits(direction)

        if speed is None:
            speed = self._state[motor_id]["pwm"]
        speed = self._validate_speed(speed)

        self._state[motor_id]["in1"] = in1
        self._state[motor_id]["in2"] = in2
        self._state[motor_id]["pwm"] = speed

        self._send_packet()

    def set_speed(self, motor_id, speed):
        """Change only the speed of a motor, keeping its current
        direction."""
        self._validate_motor_id(motor_id)
        speed = self._validate_speed(speed)
        self._state[motor_id]["pwm"] = speed
        self._send_packet()

    def stop_motor(self, motor_id):
        """Coast-stop a single motor (PWM held at its current value is
        irrelevant once IN1/IN2 are both 0, but we zero it for
        clarity)."""
        self._validate_motor_id(motor_id)
        self._state[motor_id]["in1"] = 0
        self._state[motor_id]["in2"] = 0
        self._state[motor_id]["pwm"] = 0
        self._send_packet()

    def brake_motor(self, motor_id):
        """Actively brake a single motor (IN1=IN2=1)."""
        self._validate_motor_id(motor_id)
        self._state[motor_id]["in1"] = 1
        self._state[motor_id]["in2"] = 1
        self._send_packet()

    def stop_all(self):
        """Coast-stop all 4 motors."""
        for m in range(1, NUM_MOTORS + 1):
            self._state[m] = {"in1": 0, "in2": 0, "pwm": 0}
        self._send_packet()

    def brake_all(self):
        """Actively brake all 4 motors."""
        for m in range(1, NUM_MOTORS + 1):
            self._state[m]["in1"] = 1
            self._state[m]["in2"] = 1
        self._send_packet()

    def get_state(self, motor_id):
        """Return a copy of the current (in1, in2, pwm) state for a
        motor."""
        self._validate_motor_id(motor_id)
        return dict(self._state[motor_id])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _validate_motor_id(self, motor_id):
        if motor_id not in range(1, NUM_MOTORS + 1):
            raise MotorDriverError(
                f"motor_id must be 1-{NUM_MOTORS}, got {motor_id}"
            )

    def _validate_speed(self, speed):
        speed = int(speed)
        if not (MIN_PWM <= speed <= MAX_PWM):
            raise MotorDriverError(
                f"speed must be {MIN_PWM}-{MAX_PWM}, got {speed}"
            )
        return speed

    def _build_packet(self):
        """Build the 9-byte command packet from current state, matching
        the GUI's send_command() format exactly."""
        packet = [3, 0, 0, 0, 0, 0, 0, 0, 0]
        for motor_id in range(1, NUM_MOTORS + 1):
            s = self._state[motor_id]
            dir_byte = s["in1"] * 1 + s["in2"] * 2
            packet[(motor_id * 2) - 1] = dir_byte
            packet[motor_id * 2] = s["pwm"]
        return packet

    def _send_packet(self):
        if not self.is_connected:
            raise MotorDriverError("Not connected. Call connect() first.")
        packet = self._build_packet()
        try:
            self.serial_port.write(bytes(packet))
        except serial.SerialException as e:
            raise MotorDriverError(f"Failed to send command: {e}") from e
        return packet