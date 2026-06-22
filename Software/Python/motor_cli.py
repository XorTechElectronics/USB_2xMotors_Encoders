#!/usr/bin/env python3
"""
motor_cli.py

Command-line test tool for the 4-motor USB CDC controller, built on top
of MotorDriver. Works on Windows and Linux/Raspberry Pi.

Examples:
    # List available serial ports (and their VID/PID) to help identify
    # your board
    python3 motor_cli.py list-ports

    # Auto-detect and connect, then run an interactive test menu
    python3 motor_cli.py interactive

    # Auto-detect and connect, then run a scripted self-test sequence
    python3 motor_cli.py selftest

    # Spin motor 2 clockwise at 60% for 3 seconds, then stop
    python3 motor_cli.py run --motor 2 --direction cw --speed 60 --duration 3

    # Specify the port explicitly instead of auto-detecting
    python3 motor_cli.py --port /dev/ttyACM0 run --motor 1 --direction ccw --speed 40 --duration 2
    python3 motor_cli.py --port COM5 selftest

    # Emergency stop everything
    python3 motor_cli.py stop
"""

import argparse
import sys
import time

from motor_driver import MotorDriver, MotorDriverError, NUM_MOTORS, MIN_PWM, MAX_PWM


def cmd_list_ports(args):
    ports = MotorDriver.list_ports()
    if not ports:
        print("No serial ports found.")
        return

    print(f"{'DEVICE':<18}{'VID':<8}{'PID':<8}DESCRIPTION")
    for device, vid, pid, desc in ports:
        vid_s = f"{vid:04X}" if vid is not None else "----"
        pid_s = f"{pid:04X}" if pid is not None else "----"
        print(f"{device:<18}{vid_s:<8}{pid_s:<8}{desc}")


def _connect(args):
    driver = MotorDriver(port=args.port)
    try:
        port = driver.connect()
        print(f"Connected on {port}")
    except MotorDriverError as e:
        print(f"Error: {e}")
        sys.exit(1)
    return driver


def cmd_run(args):
    driver = _connect(args)
    try:
        print(f"Motor {args.motor}: {args.direction.upper()} @ {args.speed}% "
              f"for {args.duration:.1f}s")
        driver.set_motor(args.motor, args.direction, args.speed)
        time.sleep(args.duration)
    except MotorDriverError as e:
        print(f"Error: {e}")
    finally:
        print("Stopping.")
        driver.close()


def cmd_stop(args):
    driver = _connect(args)
    driver.stop_all()
    print("All motors stopped.")
    driver.close()


def cmd_selftest(args):
    """Exercise every motor briefly in both directions, one at a time.
    A good smoke test after wiring up a new board."""
    driver = _connect(args)
    try:
        for motor_id in range(1, NUM_MOTORS + 1):
            for direction, label in ((MotorDriver.CW, "CW"), (MotorDriver.CCW, "CCW")):
                print(f"Motor {motor_id}: {label} @ 50% for 1s")
                driver.set_motor(motor_id, direction, 50)
                time.sleep(1)
                driver.stop_motor(motor_id)
                time.sleep(0.3)
        print("Self-test complete.")
    except MotorDriverError as e:
        print(f"Error: {e}")
    finally:
        driver.stop_all()
        driver.close()


def cmd_interactive(args):
    """Simple REPL for manual testing without re-running the script for
    every command."""
    driver = _connect(args)

    help_text = """
Commands:
  set <motor 1-4> <cw|ccw|stop|brake> [speed 0-255]
  speed <motor 1-4> <0-255>
  stopall
  brakeall
  state <motor 1-4>
  help
  quit
"""
    print(help_text)

    try:
        while True:
            try:
                line = input("motor> ").strip()
            except EOFError:
                break
            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()

            try:
                if cmd in ("quit", "exit"):
                    break

                elif cmd == "help":
                    print(help_text)

                elif cmd == "set":
                    motor_id = int(parts[1])
                    direction = parts[2].lower()
                    speed = int(parts[3]) if len(parts) > 3 else None
                    driver.set_motor(motor_id, direction, speed)
                    print(f"Motor {motor_id} -> {direction}"
                          + (f" @ {speed}%" if speed is not None else ""))

                elif cmd == "speed":
                    motor_id = int(parts[1])
                    speed = int(parts[2])
                    driver.set_speed(motor_id, speed)
                    print(f"Motor {motor_id} speed -> {speed}%")

                elif cmd == "stopall":
                    driver.stop_all()
                    print("All motors stopped.")

                elif cmd == "brakeall":
                    driver.brake_all()
                    print("All motors braked.")

                elif cmd == "state":
                    motor_id = int(parts[1])
                    print(driver.get_state(motor_id))

                else:
                    print(f"Unknown command: {cmd}. Type 'help' for options.")

            except (IndexError, ValueError):
                print("Invalid arguments. Type 'help' for usage.")
            except MotorDriverError as e:
                print(f"Error: {e}")

    finally:
        print("Stopping all motors and closing connection.")
        driver.stop_all()
        driver.close()


def build_parser():
    parser = argparse.ArgumentParser(
        description="CLI test tool for the 4-motor USB CDC controller."
    )
    parser.add_argument(
        "--port", default=None,
        help="Serial port (e.g. COM5 or /dev/ttyACM0). "
             "If omitted, auto-detects via VID/PID or description match."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list-ports", help="List available serial ports.")

    p_run = subparsers.add_parser("run", help="Run a single motor for a fixed duration.")
    p_run.add_argument("--motor", type=int, required=True, choices=range(1, NUM_MOTORS + 1))
    p_run.add_argument("--direction", required=True, choices=["cw", "ccw", "stop", "brake"])
    p_run.add_argument("--speed", type=int, default=50,
                        help=f"PWM percent ({MIN_PWM}-{MAX_PWM}), default 128")
    p_run.add_argument("--duration", type=float, default=2.0,
                        help="Seconds to run before stopping, default 2.0")

    subparsers.add_parser("stop", help="Stop all motors immediately.")
    subparsers.add_parser("selftest", help="Briefly exercise every motor in both directions.")
    subparsers.add_parser("interactive", help="Interactive REPL for manual testing.")

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    dispatch = {
        "list-ports": cmd_list_ports,
        "run": cmd_run,
        "stop": cmd_stop,
        "selftest": cmd_selftest,
        "interactive": cmd_interactive,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()