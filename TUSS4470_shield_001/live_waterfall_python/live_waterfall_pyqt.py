import sys
import numpy as np
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton, QLabel
from PyQt6.QtCore import QThread, pyqtSignal
import pyqtgraph as pg

# Serial Configuration
BAUD_RATE = 2500000
NUM_SAMPLES = 500  # Number of frequency/amplitude bins (X-axis)
MAX_ROWS = 150  # Number of time steps (Y-axis)
DEFAULT_LEVELS = (0, 1024)  # Expected data range

# Distance Calculation
SPEED_OF_SOUND = 1500  # meters per second in water
SAMPLE_TIME = 13.2e-6  # 13.2 microseconds in seconds
SAMPLE_RESOLUTION = (SPEED_OF_SOUND * SAMPLE_TIME * 100) / 2  # cm per row (0.99 cm per row)

MAX_DEPTH = NUM_SAMPLES * SAMPLE_RESOLUTION  # Total depth in cm
depth_labels = {int(i / SAMPLE_RESOLUTION): f"{i/100} m" for i in range(0, int(MAX_DEPTH), 100)}

def get_serial_ports():
    """Retrieve a list of available serial ports."""
    return [port.device for port in serial.tools.list_ports.comports()]

class SerialReader(QThread):
    """Thread for reading serial data asynchronously."""
    data_received = pyqtSignal(np.ndarray, float)  # Emit NumPy array and depth value

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
                    if line.startswith("dbt"):
                        try:
                            depth_part, sample_part = line.split(";")
                            depth_value = float(depth_part[3:])  # Extract numeric depth value
                            if sample_part.startswith("sp"):
                                values = np.array([int(x) for x in sample_part[2:].split(",")])
                                if values.shape[0] == NUM_SAMPLES:
                                    self.data_received.emit(values, depth_value)  # Emit valid data
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

        self.waterfall.getAxis("left").setTicks([list(depth_labels.items())])
        self.waterfall.setLabel("left", "Depth (cm)")
        self.waterfall.setLabel("bottom", "Sample Content")

        # Colorbar for waterfall
        self.colorbar = pg.HistogramLUTWidget()
        self.colorbar.setImageItem(self.imageitem)
        self.colorbar.item.gradient.loadPreset('viridis')
        self.imageitem.setLevels(DEFAULT_LEVELS)
        layout.addWidget(self.colorbar)

        # Depth display label
        self.depth_label = QLabel("Depth: --- cm")
        layout.addWidget(self.depth_label)

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

    def waterfall_plot_callback(self, spectrogram, depth):
        """Update the waterfall chart and depth label."""
        self.data = np.roll(self.data, -1, axis=0)
        self.data[-1, :] = spectrogram
        self.imageitem.setImage(self.data.T, autoLevels=False)

        # Auto color scaling
        sigma = np.std(self.data)
        mean = np.mean(self.data)
        self.imageitem.setLevels((mean - 2 * sigma, mean + 2 * sigma))

        # Update depth label
        self.depth_label.setText(f"Depth: {depth:.1f} cm")

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
