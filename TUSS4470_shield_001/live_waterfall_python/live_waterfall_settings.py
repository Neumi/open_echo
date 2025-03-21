import sys
import numpy as np
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton, QLabel, QLineEdit
from PyQt6.QtCore import QThread, pyqtSignal
import pyqtgraph as pg

# works well with Arduino code: TUSS4470_shield.ino

# Serial Configuration
BAUD_RATE = 921600
NUM_SAMPLES = 2500  # Number of frequency/amplitude bins (X-axis)
MAX_ROWS = 150  # Number of time steps (Y-axis)
DEFAULT_LEVELS = (0, 1024)  # Expected data range

# Distance Calculation
#SPEED_OF_SOUND = 1500  # meters per second in water
SPEED_OF_SOUND = 330  # meters per second in water
#SAMPLE_TIME = 13.2e-6  # 13.2 microseconds in seconds Atmega328 sample speed
SAMPLE_TIME = 7.682e-6  # 7.682 microseconds in seconds STM32 sample speed
SAMPLE_RESOLUTION = (SPEED_OF_SOUND * SAMPLE_TIME * 100) / 2  # cm per row (0.99 cm per row)

MAX_DEPTH = NUM_SAMPLES * SAMPLE_RESOLUTION  # Total depth in cm
depth_labels = {int(i / SAMPLE_RESOLUTION): f"{i / 100} m" for i in range(0, int(MAX_DEPTH), 100)}


def get_serial_ports():
    """Retrieve a list of available serial ports."""
    return [port.device for port in serial.tools.list_ports.comports()]


class SerialReader(QThread):
    """Thread for reading serial data asynchronously."""
    data_received = pyqtSignal(np.ndarray, float, float)  # Emit NumPy array and depth value

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
                    if line.startswith("dds"):
                        try:
                            depth_part, temperature_part, sample_part = line.split(";")
                            depth_sample_number = float(depth_part[3:])  # Extract numeric depth value
                            temperature = float(temperature_part[3:])  # Extract numeric depth value
                            if sample_part.startswith("sp"):
                                values = np.array([int(x) for x in sample_part[2:].split(",")])
                                if values.shape[0] == NUM_SAMPLES:
                                    self.data_received.emit(values, depth_sample_number, temperature)  # Emit valid data
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
        self.setGeometry(100, 100, 900, 600)

        # Initialize data matrix
        self.data = np.zeros((MAX_ROWS, NUM_SAMPLES))

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

        # Waterfall plot
        self.waterfall = pg.PlotWidget()
        self.imageitem = pg.ImageItem(axisOrder='row-major')
        self.waterfall.addItem(self.imageitem)
        self.waterfall.setMouseEnabled(x=False, y=False)
        layout.addWidget(self.waterfall)

        # Reverse the ticks and set range for inverted y-axis
        inverted_depth_labels = list(depth_labels.items())[::-1]  # Reverse depth labels
        self.waterfall.getAxis("left").setTicks([inverted_depth_labels])  # Set reversed depth labels
        self.waterfall.setLabel("left", "Depth (cm)")
        self.waterfall.setLabel("bottom", "Sample Content")

        # Set y-axis range to be reversed
        self.waterfall.getAxis("left").setRange(0, MAX_DEPTH)  # Reverse the axis range

        # Colorbar for waterfall
        self.colorbar = pg.HistogramLUTWidget()
        self.colorbar.setImageItem(self.imageitem)
        self.colorbar.item.gradient.loadPreset('viridis')
        self.imageitem.setLevels(DEFAULT_LEVELS)
        layout.addWidget(self.colorbar)

        # Depth display label
        self.depth_label = QLabel("Depth: --- cm")
        layout.addWidget(self.depth_label)

        self.temperature_label = QLabel("Temperature: --- °C")
        layout.addWidget(self.temperature_label)

        self.depth_line = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=3))
        self.waterfall.addItem(self.depth_line)

        # Input field for hex value
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("Enter hex value (e.g., 0x1F)")
        layout.addWidget(self.hex_input)

        # Send button for sending the hex value to Arduino
        self.send_button = QPushButton("Send Hex Value")
        self.send_button.clicked.connect(self.send_hex_value)
        layout.addWidget(self.send_button)

        self.serial_thread = None

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

    def waterfall_plot_callback(self, spectrogram, depth_index, temperature):
        """Update the waterfall chart and depth label."""
        self.data = np.roll(self.data, -1, axis=0)
        self.data[-1, :] = spectrogram
        self.imageitem.setImage(self.data.T, autoLevels=False)

        # Auto color scaling
        sigma = np.std(self.data)
        mean = np.mean(self.data)
        self.imageitem.setLevels((mean - 2 * sigma, mean + 2 * sigma))

        # Update depth label
        self.depth_label.setText(f"Depth: {depth_index * SAMPLE_RESOLUTION:.1f} cm")

        self.temperature_label.setText(f"Temperature: {temperature:.1f} °C")

        self.depth_line.setPos(depth_index)

    def send_hex_value(self):
        """Send the hex value entered in the input field to Arduino."""
        hex_value = self.hex_input.text().strip()
        print(hex_value)

        # Validate hex value format
        if hex_value.startswith("0x") and len(hex_value) > 2:
            try:
                if self.serial_thread and self.serial_thread.isRunning():
                    # Send the hex value to Arduino via serial
                    with serial.Serial(self.serial_dropdown.currentText(), BAUD_RATE) as ser:

                        ser.write(hex_value.encode())
                        print(f"Sent: {hex_value}")
            except ValueError:
                print("❌ Invalid hex format.")
        else:
            print("❌ Invalid hex value. Please enter a valid hex string (e.g., 0x1F)")

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
