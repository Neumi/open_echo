import serial
import struct


class KoggerSBP:
    def __init__(self, port='/dev/cu.usbmodem208436614E521', baudrate=115200, timeout=1):
        self.ser = serial.Serial(port, baudrate, timeout=timeout)
        self.sync1 = 0xBB
        self.sync2 = 0x55

    def test_connection(self):
        """Test if the sensor is responding by requesting its version."""
        route = 0x00  # Default route (broadcast)
        mode = 0x03  # GETTING command (HOST → DEVICE)
        command_id = 0x20  # ID_VERSION
        try:
            response = self._send_command(route, mode, command_id)
            print(response)
            if len(response) >= 34:  # The expected length for version info is 34 bytes
                # Parse the version info (example: extract and print some of it)
                sw_boot_ver = struct.unpack('<I', response[0:4])[0]
                sw_fw_ver = struct.unpack('<I', response[4:8])[0]
                hw_ver = struct.unpack('<I', response[8:12])[0]
                print(f"Sensor Connected - SW Boot Ver: {sw_boot_ver}, SW FW Ver: {sw_fw_ver}, HW Ver: {hw_ver}")
                return True
            else:
                print(response)
                print("Invalid response length for version command.")
                # return False
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def _calculate_checksum(self, data):
        # Fletcher-16 checksum calculation
        check1 = 0
        check2 = 0
        for byte in data:
            check1 = (check1 + byte) % 255
            check2 = (check2 + check1) % 255
        return check1, check2

    def _create_frame(self, route, mode, command_id, payload):
        length = len(payload)
        frame = [self.sync1, self.sync2, route, mode, command_id, length]
        frame.extend(payload)
        check1, check2 = self._calculate_checksum(frame[2:])  # Checksum over route, mode, id, length, and payload
        frame.append(check1)
        frame.append(check2)
        return bytearray(frame)

    def _send_command(self, route, mode, command_id, payload=[]):
        frame = self._create_frame(route, mode, command_id, payload)
        self.ser.write(frame)
        return self._receive_response()

    def _receive_response(self):
        # Read the response frame
        response = self.ser.read(1024)  # You can set the appropriate buffer size
        print(response)
        if len(response) < 8:  # Minimum frame size is 8 bytes
            raise Exception("Invalid response received")

        # Parse the frame
        #if response[0] != self.sync1 or response[1] != self.sync2:
            # raise Exception("Invalid sync bytes")

        length = response[5]
        payload = response[6:6 + length]
        check1 = response[-2]
        check2 = response[-1]

        # Validate checksum
        calc_check1, calc_check2 = self._calculate_checksum(response[2:-2])
        #if calc_check1 != check1 or calc_check2 != check2:
            #raise Exception("Checksum validation failed")

        return payload

    # Example function to request distance
    def get_distance(self):
        route = 0x00  # Default route (broadcast)
        mode = 0x03  # GETTING command
        command_id = 0x02  # ID_DIST
        response = self._send_command(route, mode, command_id)
        if len(response) >= 4:
            # Response is a 4-byte distance (unsigned 32-bit int, little endian)
            distance = struct.unpack('<I', response)[0]
            return distance
        else:
            raise Exception("Invalid distance data")

    # Example function to request temperature
    def get_temperature(self):
        route = 0x00  # Default route (broadcast)
        mode = 0x03  # GETTING command
        command_id = 0x05  # ID_TEMP
        response = self._send_command(route, mode, command_id)
        if len(response) >= 2:
            # Response is a 2-byte temperature (signed 16-bit int, little endian)
            temp_raw = struct.unpack('<h', response)[0]
            return temp_raw / 100.0  # Temperature is in 0.01°C units
        else:
            raise Exception("Invalid temperature data")

    def close(self):
        self.ser.close()
