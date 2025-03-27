import sys
import numpy as np
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton, QLineEdit, QLabel
from PyQt6.QtCore import QThread, pyqtSignal
import pyqtgraph as pg

# Serial Configuration
BAUD_RATE = 1000000
NUM_SAMPLES = 250  # Number of frequency/amplitude bins (X-axis)
MAX_ROWS = 150  # Number of time steps (Y-axis)
DEFAULT_LEVELS = (0, 1024)  # Expected data range


def get_serial_ports():
    """Retrieve a list of available serial ports."""
    return [port.device for port in serial.tools.list_ports.comports()]


class SerialReader(QThread):
    """Thread for reading serial data asynchronously."""
    data_received = pyqtSignal(np.ndarray)  # Emit NumPy array

    def __init__(self, port, baud_rate):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.running = True

    def run(self):
        """Continuously read serial data and emit processed arrays."""
        try:
            with serial.Serial(self.port, self.baud_rate, timeout=1) as ser:
                while self.running:
                    line = ser.readline().decode("utf-8").strip()
                    if line.startswith("sp"):
                        try:
                            values = np.array([int(x) for x in line[2:].split(",")])
                            if values.shape[0] == NUM_SAMPLES:
                                self.data_received.emit(values)  # Emit valid data
                        except ValueError as e:
                            print(f"⚠️ Data parse error: {line} - {e}")
        except serial.SerialException as e:
            print(f"❌ Serial Error: {e}")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class WaterfallApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Real-Time Waterfall Display")
        self.setGeometry(100, 100, 800, 600)

        # Initialize data matrix (black screen initially)
        self.data = np.zeros((MAX_ROWS, NUM_SAMPLES))  # **Rows = Time, Columns = Sample Content**

        # Create central widget & layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout()
        central_widget.setLayout(layout)

        # Dropdown menu for serial port selection
        self.serial_dropdown = QComboBox()
        self.serial_dropdown.addItems(get_serial_ports())
        layout.addWidget(self.serial_dropdown)

        # Connect button
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_serial)
        layout.addWidget(self.connect_button)

        # Command input field (for entering settings)
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("Enter command in format CMD:VALUE")
        layout.addWidget(self.command_input)

        # Send button to send the command to the Arduino
        self.send_button = QPushButton("Send Command")
        self.send_button.clicked.connect(self.send_command)
        layout.addWidget(self.send_button)

        # Waterfall plot
        self.waterfall = pg.PlotWidget(labels={'left': 'Time (Newest at Bottom)', 'bottom': 'Sample Content'})
        self.imageitem = pg.ImageItem(axisOrder='row-major')  # Optimized for performance
        self.waterfall.addItem(self.imageitem)
        self.waterfall.setMouseEnabled(x=False, y=False)
        layout.addWidget(self.waterfall)

        # Colorbar for waterfall
        self.colorbar = pg.HistogramLUTWidget()
        self.colorbar.setImageItem(self.imageitem)  # Connects the colorbar
        self.colorbar.item.gradient.loadPreset('viridis')  # Set colormap
        self.imageitem.setLevels(DEFAULT_LEVELS)  # Set default levels
        layout.addWidget(self.colorbar)

        self.serial_thread = None  # Initially no thread

    def connect_serial(self):
        """Connect to the selected serial port and start the thread."""
        if self.serial_thread:
            self.serial_thread.stop()
            self.serial_thread = None

        selected_port = self.serial_dropdown.currentText()
        try:
            self.serial_thread = SerialReader(selected_port, BAUD_RATE)
            self.serial_thread.data_received.connect(self.waterfall_plot_callback)
            self.serial_thread.start()
            print(f"✅ Connected to {selected_port}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

    def send_command(self):
        """Send the command entered in the input field to the Arduino."""
        command = self.command_input.text().strip()
        if command:
            # Check if the command format is valid (CMD:VALUE)
            if ':' in command:
                cmd, value_str = command.split(':')
                try:
                    value = int(value_str, 16)  # Convert to integer
                    if 0 <= value <= 0xFF:  # Validate value range (0x00 to 0xFF)
                        self.send_to_arduino(cmd, value)
                    else:
                        print("❌ Invalid value range (must be 00-FF)")
                except ValueError:
                    print("❌ Invalid value format. Must be hexadecimal (e.g., 0xFF)")
            else:
                print("❌ Invalid command format. Use CMD:VALUE (e.g., BPF:11)")

    def send_to_arduino(self, cmd, value):
        """Send the formatted command to the Arduino."""
        command_str = f"{cmd.upper()}:{value:02X}\n"  # Format as CMD:VALUE (e.g., BPF:11)
        try:
            with serial.Serial(self.serial_dropdown.currentText(), BAUD_RATE, timeout=1) as ser:
                ser.write(command_str.encode())  # Send command to Arduino
                print(f"✅ Sent: {command_str.strip()}")
        except serial.SerialException as e:
            print(f"❌ Failed to send command: {e}")

    def waterfall_plot_callback(self, spectrogram):
        """Update the waterfall chart with new sensor data."""
        self.data = np.roll(self.data, -1, axis=0)  # Shift **up** (newest data at bottom)
        self.data[-1, :] = spectrogram  # Insert new row at the bottom
        self.imageitem.setImage(self.data.T, autoLevels=False)  # **Transpose to swap X/Y axes**

        # Auto color scaling
        sigma = np.std(self.data)
        mean = np.mean(self.data)
        self.imageitem.setLevels((mean - 2 * sigma, mean + 2 * sigma))

    def closeEvent(self, event):
        """Handle closing event properly."""
        if self.serial_thread:
            self.serial_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WaterfallApp()
    window.show()
    sys.exit(app.exec())
