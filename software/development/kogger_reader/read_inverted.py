import serial

# Set up the serial connection
ser = serial.Serial(
    port='/dev/tty.usbserial-A50285BI',  # Replace with your serial device
    baudrate=115200,  # Match this with your device's baud rate
    timeout=1  # Timeout in seconds
)


def invert_bits(byte):
    # Inverts the bits of the byte (flip HIGH and LOW)
    return ~byte & 0xFF  # Invert bits and mask to 8 bits


# Ensure the connection is open
if ser.is_open:
    print("Serial port is open, waiting for data...")

while True:
    # Read a byte from the serial port
    byte = ser.read(1)

    if byte:
        # Convert byte to an integer
        byte_value = ord(byte)

        # Invert the bits
        inverted_byte = invert_bits(byte_value)

        # Print the inverted byte in hexadecimal
        print(f"Original Data: {byte_value:02X}, Inverted Data: {inverted_byte:02X}")
