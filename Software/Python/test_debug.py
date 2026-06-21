import serial
import struct

PORT = 'COM4'   # adjust to your port
BAUD = 115200

ENCODER_SYNC = 0xAA
DEBUG_SYNC   = 0xBB

def read_next_packet(ser):
    while True:
        b = ser.read(1)
        if not b:
            continue
        if b[0] == ENCODER_SYNC:
            data = b''
            while len(data) < 8:
                data += ser.read(8 - len(data))
            enc1, enc2 = struct.unpack('<ii', data)
            return ('encoder', enc1, enc2)
        elif b[0] == DEBUG_SYNC:
            data = b''
            while len(data) < 4:
                data += ser.read(4 - len(data))
            prev_state, new_state, index, delta = struct.unpack('<BBBb', data)
            return ('debug', prev_state, new_state, index, delta)
        # else: unrecognized byte, keep scanning

if __name__ == '__main__':
    ser = serial.Serial(PORT, BAUD, timeout=1)
    print("Listening... turn the motor shaft slowly by hand.")
    while True:
        packet = read_next_packet(ser)
        if packet[0] == 'debug':
            _, prev_state, new_state, index, delta = packet
            print(f"prev={prev_state}  new={new_state}  index={index:2d}  delta={delta:+d}")