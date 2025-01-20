import serial
import struct
import time

# Configuration parameters
SERIAL_PORT = '/dev/cu.usbserial-A50285BI'  # Replace with your actual serial port
#SERIAL_PORT = '/dev/cu.usbmodem208436614E521'  # Replace with your actual serial port
BAUD_RATE = 115200              # Default baud 115200
SYNC1 = 0xBB
SYNC2 = 0x55
CONFIRMATION_KEY = 0xC96B5D4A  # For commands that require confirmation

# Frame structure sizes
HEADER_SIZE = 6  # SYNC1, SYNC2, ROUTE, MODE, ID, LENGTH
CHECKSUM_SIZE = 2

def fletcher16(data):
    """Calculate Fletcher-16 checksum."""
    check1, check2 = 0, 0
    for byte in data:
        check1 = (check1 + byte) % 255
        check2 = (check2 + check1) % 255
    return check1, check2

def parse_route(byte):
    """Parse the ROUTE byte into DEV_ADDRESS and RESERVED fields."""
    dev_address = byte & 0x0F
    reserved = (byte >> 4) & 0x03
    return {'DEV_ADDRESS': dev_address, 'RESERVED': reserved}

def parse_mode(byte):
    """Parse the MODE byte into TYPE, VERSION, MARK, and RESPONSE fields."""
    mode_type = byte & 0x03
    version = (byte >> 3) & 0x07
    mark = (byte >> 6) & 0x01
    response = (byte >> 7) & 0x01
    return {
        'TYPE': mode_type,
        'VERSION': version,
        'MARK': mark,
        'RESPONSE': response
    }

def build_command_frame(route, mode, command_id, payload):
    """Builds a frame to send a command to the device."""
    length = len(payload)
    frame = [SYNC1, SYNC2, route, mode, command_id, length] + list(payload)
    check1, check2 = fletcher16(frame)
    check1 = 0x85
    check2 = 0x8D # is checksum actually used?!
    frame += [check1, check2]
    return bytearray(frame)

def read_frame(ser):
    """Read a full frame from the device without length or checksum validation."""
    # Look for the start of the frame
    print("Reading frame")
    while True:
        # Check for the SYNC bytes

        if ser.read(1) == bytes([SYNC1]) and ser.read(1) == bytes([SYNC2]):
            print("Found SYNC bytes")
            # Read ROUTE, MODE, ID, and LENGTH bytes
            header = ser.read(4)
            if len(header) < 4:
                print("Incomplete header")
                continue
            route, mode, msg_id, length = struct.unpack('BBBB', header)

            # Read PAYLOAD based on LENGTH
            payload = ser.read(length)
            if len(payload) < length:
                print("Incomplete payload")
                continue

            # Read CHECKSUM bytes without validating
            check1, check2 = struct.unpack('BB', ser.read(2))

            # Parse ROUTE and MODE fields
            route_info = parse_route(route)
            mode_info = parse_mode(mode)

            return {
                'ROUTE': route_info,
                'MODE': mode_info,
                'ID': msg_id,
                'LENGTH': length,
                'PAYLOAD': payload,
                'CHECKSUM': (check1, check2)
            }


def request_data(ser, command_id):
    """Sends a request to the device for a specific command ID and reads the response."""
    route = 0x00  # Default device address
    mode = 0x83  # Host → Device (GETTING)
    frame = build_command_frame(route, mode, command_id, [])
    print(f"Sent request: {frame}")
    ser.write(frame)
    time.sleep(0.5)
    print(f"Sent request for command ID {command_id:#04x}")
    response = read_frame(ser)
    print("Response:")
    print(response['payload'])

    if response and response['ID'] == command_id:
        print(f"Received response for command ID {command_id:#04x}:")
        parse_payload(response)
    else:
        print("No valid response received.")


def parse_payload(response):
    """Parse payload based on command ID and display the data."""
    if response['ID'] == 0x01:  # ID_TIMESTAMP
        timestamp, = struct.unpack('<I', response['PAYLOAD'])
        print(f"Timestamp: {timestamp} ms")
    elif response['ID'] == 0x02:  # ID_DISTANCE
        print(f"RAW DISTANCE: {response['PAYLOAD']}")
    elif response['ID'] == 0x04:  # ID_ATTITUDE
        print(f"RAW ATTITUDE: {response['PAYLOAD']}")
    elif response['ID'] == 0x05:  # ID_TEMP MIGHT NOT WORK
        if len(response['PAYLOAD']) != response['LENGTH']:
            raise ValueError("Payload Lentgh mismatch")

        payload_padded = response['PAYLOAD'] + b'\x00'
        # Unpack as a 4-byte float (Little Endian)
        temperature = struct.unpack('<f', payload_padded)[0]
        print(f"Temperature: {temperature * 0.01:.2f} °C")

    elif response['ID'] == 0x21:  # ID_MARK
        mark, = struct.unpack('<B', response['PAYLOAD'])
        print(f"Mark: {mark}")
    else:
        print(f"Unknown payload for command ID {response['ID']:#04x}: {response['PAYLOAD']}")


def send_stop_message(serial_port):
    """Send the specified message to switch off the sonar data stream."""
    # Byte sequence as hexadecimal
    message = bytes.fromhex("bb55008210090100000000000000009c2b")

    # Open the serial port
    try:
        with serial.Serial(serial_port, baudrate=115200, timeout=1) as ser:
            ser.write(message)
            print(f"Message sent: {message.hex()}")
    except serial.SerialException as e:
        print(f"Error communicating with the serial port: {e}")


def main():
    # Usage example within your serial communication loop
    with serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1) as ser:
        request_data(ser, 0x02)  # Request ID_TEMP

if __name__ == "__main__":
    main()


