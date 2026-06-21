import serial
import struct

SYNC = 0xAA

def read_packet(ser):
    # find sync byte
    while True:
        b = ser.read(1)
        if b and b[0] == SYNC:
            break

    # collect exactly 8 bytes, however many read() calls it takes
    data = b''
    while len(data) < 8:
        data += ser.read(8 - len(data))

    enc1, enc2 = struct.unpack('<ii', data)
    return enc1, enc2

ser = serial.Serial('COM4', 115200, timeout=1)
while True:
    enc1, enc2 = read_packet(ser)
    print(enc1, enc2)