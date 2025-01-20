import serial
import struct


class KoggerSBP:
    def __init__(self, port='/dev/tty.usbmodem208436614E521', baudrate=115200, timeout=1):
        # Initialize the serial port connection
        self.ser = serial.Serial(port, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE,
                                 stopbits=serial.STOPBITS_ONE, timeout=timeout)

        self.sync1 = 0xBB  # SYNC1 byte
        self.sync2 = 0x55  # SYNC2 byte

    def _calculate_checksum(self, data):
        """Calculate the Fletcher-16 checksum."""
        check1 = 0
        check2 = 0
        for byte in data:
            check1 = (check1 + byte) % 255
            check2 = (check2 + check1) % 255
        return check1, check2

    def _create_frame(self, route, mode, command_id, payload):
        """Create the full frame with header, payload, and checksum."""
        length = len(payload)
        frame = [self.sync1, self.sync2, route, mode, command_id, length]
        frame.extend(payload)
        check1, check2 = self._calculate_checksum(frame[2:])  # Checksum starts after SYNC bytes
        frame.append(check1)
        frame.append(check2)
        return bytearray(frame)

    def _send_command(self, route, mode, command_id, payload=[]):
        """Send a command to the device and wait for the response."""
        frame = self._create_frame(route, mode, command_id, payload)
        self.ser.write(frame)
        return self._receive_response()

    def _receive_response(self):
        """Receive and validate the response from the device."""
        response = self.ser.read(1024)  # Adjust the buffer size if needed
        print(f"Raw response: {response.hex()}")  # Print the raw response in hex for debugging

        if len(response) < 8:  # Minimum valid frame size
            raise Exception("Invalid response received")

        # Parse the frame and check sync bytes
        if response[0] != self.sync1 or response[1] != self.sync2:
            raise Exception("Invalid sync bytes")

        # Extract length and payload
        length = response[5]
        payload = response[6:6 + length]
        check1 = response[-2]
        check2 = response[-1]

        # Validate checksum
        calc_check1, calc_check2 = self._calculate_checksum(response[2:-2])
        if calc_check1 != check1 or calc_check2 != check2:
            raise Exception("Checksum validation failed")

        return payload

    def test_echo(self):
        """Test sensor response using the ID_MARK (0x21) command."""
        route = 0x00  # Default route (broadcast)
        mode = 0x02  # SETTING command (HOST → DEVICE)
        command_id = 0x21  # ID_MARK command
        payload = [0xC9, 0x6B, 0x5D, 0x4A]  # Confirmation key from the protocol

        try:
            response = self._send_command(route, mode, command_id, payload)
            print(f"Echo test response: {response}")
            return True
        except Exception as e:
            print(f"Echo test failed: {e}")
            return False

    def close(self):
        """Close the serial port."""
        self.ser.close()


# --- Main Test Script ---
if __name__ == "__main__":
    # Update the port name according to your setup (e.g., '/dev/tty.usbserial-xxxx')
    sensor = KoggerSBP(port='/dev/tty.usbserial-A50285BI', baudrate=115200)

    # Run the echo test to check if the sensor responds
    if sensor.test_echo():
        print("Sensor is connected and responding.")
    else:
        print("Failed to connect to the sensor.")

    # Close the serial port
    sensor.close()
