import serial
import time
import struct
import serial.tools.list_ports

class KoggerSonar:
    # Protocol constants
    SYNC1 = 0xBB
    SYNC2 = 0x55
    
    # Command IDs
    ID_CHART = 0x03
    
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        """Initialize sonar connection"""
        self.serial = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        
    def read_frame(self):
        """Read and parse a complete frame"""
        print("Waiting for sync bytes...")
        # Wait for sync bytes
        while True:
            byte = self.serial.read(1)
            if not byte:  # Timeout occurred
                print("Timeout waiting for data")
                continue
            if byte[0] == self.SYNC1:
                byte2 = self.serial.read(1)
                if not byte2:
                    print("Timeout waiting for SYNC2")
                    continue
                if byte2[0] == self.SYNC2:
                    print("Found sync bytes!")
                    break
        
        print("Reading header...")
        # Read header
        route = self.serial.read(1)[0]
        mode = self.serial.read(1)[0]
        cmd_id = self.serial.read(1)[0]
        length = self.serial.read(1)[0]
        
        print(f"Header: route={route:02x}, mode={mode:02x}, cmd_id={cmd_id:02x}, length={length}")
        
        # Read payload and checksum
        payload = self.serial.read(length)
        checksum = self.serial.read(2)
        
        return cmd_id, payload

    def parse_chart_data(self, payload):
        """Parse chart data from payload"""
        if len(payload) < 6:
            return None
            
        # Parse header
        seq_offset, sample_resol, abs_offset = struct.unpack('<HHH', payload[:6])
        
        # Get chart data
        chart_data = list(payload[6:])
        
        return {
            'sequence_offset': seq_offset,
            'sample_resolution': sample_resol,
            'absolute_offset': abs_offset,
            'data': chart_data
        }

    def start_reading(self):
        """Start continuous reading of sonar data"""
        print("Starting to read echo data...")
        try:
            while True:
                cmd_id, payload = self.read_frame()
                
                if cmd_id == self.ID_CHART:
                    chart_data = self.parse_chart_data(payload)
                    # ... rest of the code ...
        except Exception as e:
            print(f"Error reading frame: {e}")
                    

# List available ports
print("Available ports:")
ports = serial.tools.list_ports.comports()
for port in ports:
    print(f"- {port.device}: {port.description}")

# Create sonar instance
port = input("\nEnter port name (e.g., COM3 or /dev/ttyUSB0): ").strip()
print(f"\nTrying to connect to {port}...")

try:
    sonar = KoggerSonar(port)
    if sonar.serial.is_open:
        print("Serial port opened successfully")
        print("\nStarting to read data...")
        print("Press Ctrl+C to stop")
        sonar.start_reading()
except KeyboardInterrupt:
    print("\nStopping sonar reading...")
except Exception as e:
    print(f"Error: {e}")
finally:
    if 'sonar' in locals():
        sonar.serial.close()
        print("Serial port closed")