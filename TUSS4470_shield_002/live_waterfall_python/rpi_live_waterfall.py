import sys
import numpy as np
import serial
import serial.tools.list_ports

from PyQt5.QtWidgets import QHBoxLayout, QGridLayout  # Add this to your imports
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton, QLabel, QLineEdit
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg

# works well with Arduino code: TUSS4470_shield.ino

# Serial Configuration
#BAUD_RATE = 921600
BAUD_RATE = 250000
NUM_SAMPLES = 2500  # Number of frequency/amplitude bins (X-axis)
#NUM_SAMPLES = 1800  # Number of frequency/amplitude bins (X-axis)
MAX_ROWS = 150  # Number of time steps (Y-axis)
DEFAULT_LEVELS = (0, 4095)  # Expected data range


# Distance Calculation
SPEED_OF_SOUND = 1500  # meters per second in water
#SPEED_OF_SOUND = 330  # meters per second in water
#SAMPLE_TIME = 13.2e-6  # 13.2 microseconds in seconds Atmega328 sample speed
SAMPLE_TIME = 7.682e-6  # 7.682 microseconds in seconds STM32 sample speed
SAMPLE_RESOLUTION = (SPEED_OF_SOUND * SAMPLE_TIME * 100) / 2  # cm per row (0.99 cm per row)

MAX_DEPTH = NUM_SAMPLES * SAMPLE_RESOLUTION  # Total depth in cm
depth_labels = {int(i / SAMPLE_RESOLUTION): f"{i / 100}" for i in range(0, int(MAX_DEPTH), 100)}

print(depth_labels)


def get_serial_ports():
    """Retrieve a list of available serial ports."""
    return [port.device for port in serial.tools.list_ports.comports()]


class SerialReader(QThread):
    """Thread for reading serial data asynchronously."""
    data_received = pyqtSignal(np.ndarray, float, float, float)  # Emit NumPy array and depth value

    def __init__(self, port, baud_rate):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.running = True

    def run(self):
        """Continuously read serial data and emit processed arrays."""
        try:
            with serial.Serial(self.port, self.baud_rate, timeout=1) as ser:
                print("connected")
                while self.running:
                    try:
                        line = ser.readline().decode("utf-8").strip()
                        if line.startswith("dds"):
                            depth_part, temperature_part, drive_voltage_part, sample_part = line.split(";")
                            depth_sample_number = float(depth_part[3:])
                            temperature = float(temperature_part[3:])
                            drive_voltage = int(drive_voltage_part[3:]) / 100

                            if sample_part.startswith("sp"):
                                values = np.array([int(x) for x in sample_part[2:].split(",")])
                                if values.shape[0] == NUM_SAMPLES:
                                    self.data_received.emit(values, depth_sample_number, temperature, drive_voltage)
                    except Exception as e:
                        print(f"⚠️ Serial read or parse error: {e}")
        except serial.SerialException as e:
            print(f"❌ Serial Error: {e}")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

class WaterfallApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread = None  # ✅ Define it early to avoid AttributeError

        self.setWindowTitle("Real-Time Waterfall Display")
        self.setGeometry(0, 0, 480, 800)  # Portrait mode for Raspberry Pi screen

        self.data = np.zeros((MAX_ROWS, NUM_SAMPLES))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        central_widget.setLayout(main_layout)

        # === Waterfall Plot ===
        self.waterfall = pg.PlotWidget()
        self.imageitem = pg.ImageItem(axisOrder='row-major')
        self.waterfall.addItem(self.imageitem)
        self.waterfall.setMouseEnabled(x=False, y=False)
        self.waterfall.setMinimumHeight(400)  # Slightly more vertical space
        main_layout.addWidget(self.waterfall)

        inverted_depth_labels = list(depth_labels.items())[::-1]
        self.waterfall.getAxis("left").setTicks([inverted_depth_labels])
        self.depth_line = pg.InfiniteLine(angle=0, pen=pg.mkPen('r', width=2))
        self.waterfall.addItem(self.depth_line)

        # === Colorbar BELOW the plot to save width ===
        self.colorbar = pg.HistogramLUTWidget()
        self.colorbar.setImageItem(self.imageitem)
        self.colorbar.item.gradient.loadPreset('viridis')
        self.colorbar.setMaximumHeight(80)
        self.imageitem.setLevels(DEFAULT_LEVELS)
        main_layout.addWidget(self.colorbar)

        # === Controls (Vertical) ===
        controls_layout = QVBoxLayout()

        # Serial row
        serial_row = QHBoxLayout()
        serial_row.addWidget(QLabel("Port:"))
        self.serial_dropdown = QComboBox()
        self.serial_dropdown.addItems(get_serial_ports())
        self.serial_dropdown.setMinimumWidth(150)
        serial_row.addWidget(self.serial_dropdown)
        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.connect_serial)
        serial_row.addWidget(self.connect_button)
        controls_layout.addLayout(serial_row)

        # Info labels
        info_layout = QHBoxLayout()
        self.depth_label = QLabel("Depth: --- cm")
        self.temperature_label = QLabel("Temperature: --- °C")
        self.drive_voltage_label = QLabel("vDRV: --- V")

        info_layout.addWidget(self.depth_label)
        info_layout.addWidget(self.temperature_label)
        info_layout.addWidget(self.drive_voltage_label)

        info_container = QWidget()
        info_container.setLayout(info_layout)
        controls_layout.addWidget(info_container)  # No grid args!



        # Hex input
        hex_row = QHBoxLayout()
        self.hex_input = QLineEdit()
        self.hex_input.setPlaceholderText("0x1F")
        hex_row.addWidget(self.hex_input)
        self.send_button = QPushButton("Send")
        self.send_button.clicked.connect(self.send_hex_value)
        hex_row.addWidget(self.send_button)
        controls_layout.addLayout(hex_row)

        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        main_layout.addWidget(controls_container)


    def connect_serial(self):
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

    def waterfall_plot_callback(self, spectrogram, depth_index, temperature, drive_voltage):
        self.data = np.roll(self.data, -1, axis=0)
        self.data[-1, :] = spectrogram
        self.imageitem.setImage(self.data.T, autoLevels=False)

        sigma = np.std(self.data)
        mean = np.mean(self.data)
        self.imageitem.setLevels((mean - 2 * sigma, mean + 2 * sigma))

        self.depth_label.setText(f"Depth: {depth_index * SAMPLE_RESOLUTION:.1f} cm | Index: {depth_index:.0f}")
        self.temperature_label.setText(f"Temperature: {temperature:.1f} °C")
        self.drive_voltage_label.setText(f"vDRV: {drive_voltage:.1f} V")
        self.depth_line.setPos(depth_index)

    def send_hex_value(self):
        hex_value = self.hex_input.text().strip()
        print(hex_value)

        if hex_value.startswith("0x") and len(hex_value) > 2:
            try:
                if self.serial_thread and self.serial_thread.isRunning():
                    with serial.Serial(self.serial_dropdown.currentText(), BAUD_RATE) as ser:
                        ser.write(hex_value.encode())
                        print(f"Sent: {hex_value}")
            except ValueError:
                print("❌ Invalid hex format.")
        else:
            print("❌ Invalid hex value. Please enter a valid hex string (e.g., 0x1F)")

    def closeEvent(self, event):
        if self.serial_thread:
            self.serial_thread.stop()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WaterfallApp()
    window.show()
    sys.exit(app.exec())
