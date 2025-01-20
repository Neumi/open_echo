import serial


def test_serial_communication(port, baudrate=1000000, timeout=1):
    try:
        # Open the serial port
        with serial.Serial(port, baudrate, timeout=timeout) as ser:
            print(f"Listening on {port} at {baudrate} baud...")

            while True:
                # Read data from the serial port
                data = ser.read(2)  # Read two bytes

                # Check if we received the starter bytes
                if len(data) == 2 and data[0] == 0xBB and data[1] == 0x55:
                    print("Received message with correct starter bytes: 0xBB 0x55")
                else:
                    print("No valid starter bytes received. Received:", data.hex())
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("\nStopped by user.")


if __name__ == "__main__":
    # Replace 'COM3' with your actual port (e.g., 'COM3', '/dev/ttyUSB0', etc.)
    test_serial_communication(port="/dev/tty.usbserial-A50285BI")
