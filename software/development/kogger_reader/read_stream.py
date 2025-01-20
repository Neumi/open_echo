import serial
from sbp.client.drivers.pyserial_driver import PySerialDriver
from sbp.client.handler import Handler

# Configuration
BAUD_RATE = 115200
SERIAL_PORT = '/dev/cu.usbmodem208436614E521'


def main():
    try:
        # Open the serial port
        with PySerialDriver(SERIAL_PORT, baud=BAUD_RATE) as driver:
            print(f"Listening on {SERIAL_PORT} at {BAUD_RATE} baud.")

            # Create an SBP handler
            with Handler(driver.read, driver.write) as handler:
                for msg, metadata in handler:
                    # Print the decoded SBP message
                    print(f"Message: {msg}, Metadata: {metadata}")

    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
    except KeyboardInterrupt:
        print("\nExiting program.")


if __name__ == "__main__":
    main()
