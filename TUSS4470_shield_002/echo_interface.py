import sys
import numpy as np
import serial
import serial.tools.list_ports
import struct

from PyQt5.QtWidgets import QHBoxLayout, QGridLayout
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QComboBox, QPushButton, QLabel, QLineEdit
from PyQt5.QtCore import QThread, pyqtSignal
import pyqtgraph as pg
import qdarktheme
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QPushButton, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor


# Serial Configuration
BAUD_RATE = 250000
NUM_SAMPLES = 1200  # Number of frequency/amplitude bins (X-axis)

MAX_ROWS = 300  # Number of time steps (Y-axis)
Y_LABEL_DISTANCE = 50  # distance between labels in cm

# SPEED_OF_SOUND = 1500  # meters per second in water
SPEED_OF_SOUND = 330  # meters per second in water
SAMPLE_TIME = 13.2e-6  # 13.2 microseconds in seconds Atmega328 sample speed
# SAMPLE_TIME = 7.682e-6  # 7.682 microseconds in seconds STM32 sample speed

DEFAULT_LEVELS = (0, 256)  # Expected data range

SAMPLE_RESOLUTION = (SPEED_OF_SOUND * SAMPLE_TIME * 100) / 2  # cm per row (0.99 cm per row)
PACKET_SIZE = 1 + 6 + 2 * NUM_SAMPLES + 1  # header + payload + checksum
MAX_DEPTH = NUM_SAMPLES * SAMPLE_RESOLUTION  # Total depth in cm
depth_labels = {int(i / SAMPLE_RESOLUTION): f"{i / 100}" for i in range(0, int(MAX_DEPTH), Y_LABEL_DISTANCE)}


def read_packet(ser):
    while True:
        header = ser.read(1)
        if header != b'\xAA':
            continue  # Wait for the start byte

        payload = ser.read(6 + 2 * NUM_SAMPLES)
        checksum = ser.read(1)

        if len(payload) != 6 + 2 * NUM_SAMPLES or len(checksum) != 1:
            continue  # Incomplete packet

        # Verify checksum
        calc_checksum = 0
        for byte in payload:
            calc_checksum ^= byte
        if calc_checksum != checksum[0]:
            print("⚠️ Checksum mismatch")
            continue

        # Unpack payload
        depth, temp_scaled, vDrv_scaled = struct.unpack(">HhH", payload[:6])
        depth = min(depth, NUM_SAMPLES)

        # print(depth)

        samples = struct.unpack(f">{NUM_SAMPLES}H", payload[6:])

        temperature = temp_scaled / 100.0
        drive_voltage = vDrv_scaled / 100.0
        values = np.array(samples)

        return values, depth, temperature, drive_voltage


def get_serial_ports():
    """Retrieve a list of available serial ports."""
    return [port.device for port in serial.tools.list_ports.comports()][::-1]


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
            with serial.Serial(self.port, BAUD_RATE, timeout=1) as ser:
                print("connected")
                while self.running:
                    result = read_packet(ser)
                    if result:
                        values, depth, temperature, drive_voltage = result
                        # print(f"Depth: {depth}, Temp: {temperature}°C, Vdrv: {drive_voltage}V")
                        # print(len(values))

                        self.data_received.emit(values, depth, temperature, drive_voltage)
        except serial.SerialException as e:
            print(f"❌ Serial Error: {e}")

    def stop(self):
        self.running = False
        self.quit()
        self.wait()


class SettingsDialog(QWidget):
    def __init__(self, parent=None, current_gradient='cyclic', current_speed=330):
        super().__init__(parent)
        self.setWindowTitle("Chart Settings")
        self.setFixedSize(320, 250)

        self.main_app = parent

        # Outer layout for centering
        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)

        # === Card container ===
        card = QWidget()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(15)

        # --- Color Map ---
        card_layout.addWidget(QLabel("Color Map:"))
        self.gradient_dropdown = QComboBox()
        self.gradient_dropdown.addItems([
            'viridis', 'plasma', 'inferno', 'magma',
            'thermal', 'flame', 'yellowy', 'bipolar',
            'spectrum', 'cyclic', 'greyclip', 'grey'
        ])
        self.gradient_dropdown.setCurrentText(current_gradient)
        card_layout.addWidget(self.gradient_dropdown)

        # --- Speed of Sound ---
        card_layout.addWidget(QLabel("Speed of Sound:"))
        self.speed_dropdown = QComboBox()
        self.speed_dropdown.addItems(["330 (Air)", "1500 (Water)"])
        self.speed_dropdown.setCurrentIndex(1 if current_speed == 1500 else 0)
        card_layout.addWidget(self.speed_dropdown)

        # --- Buttons ---
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self.apply_settings)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.close)
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        card_layout.addLayout(button_layout)

        # Add card to outer layout
        outer_layout.addWidget(card)

        # --- Styling ---
        self.setStyleSheet("""
                QDialog {
                    background-color: #1e1e1e;
                }
                QWidget#Card {
                    background-color: #2b2b2b;
                    border-radius: 12px;
                    padding: 15px;
                }
                QLabel {
                    color: #ffffff;
                    font-size: 14px;
                }
                QComboBox {
                    background-color: #3c3c3c;
                    color: white;
                    padding: 4px;
                    border-radius: 4px;
                }
                QPushButton {
                    background-color: #444444;
                    border: 1px solid #666;
                    padding: 5px 10px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
            """)

        # Set object name so stylesheet applies to card
        card.setObjectName("Card")

        self.setLayout(outer_layout)


    def apply_settings(self):
        selected_gradient = self.gradient_dropdown.currentText()
        selected_speed = 330 if self.speed_dropdown.currentIndex() == 0 else 1500
        if self.main_app:
            self.main_app.set_gradient(selected_gradient)
            self.main_app.set_sound_speed(selected_speed)
        self.close()


class WaterfallApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread = None  # ✅ Define it early to avoid AttributeError

        self.current_gradient = 'cyclic'  # default color scheme
        self.current_speed = SPEED_OF_SOUND  # default sound speed (330)

        self.setWindowTitle("Open Echo Interface")
        self.setGeometry(0, 0, 480, 800)  # Portrait mode for Raspberry Pi screen

        self.data = np.zeros((MAX_ROWS, NUM_SAMPLES))

        # Disable window translucency
        self.setAttribute(Qt.WA_TranslucentBackground, False)

        # Force opaque window flag
        self.setWindowFlags(self.windowFlags() & ~Qt.FramelessWindowHint)

        # Set solid background color explicitly via palette
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor("#2b2b2b"))
        self.setPalette(palette)
        self.setAutoFillBackground(True)


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

        # Mirror Y-axis ticks to the right side
        right_axis = self.waterfall.getAxis("right")
        right_axis.setTicks([inverted_depth_labels])
        right_axis.setStyle(showValues=True)

        # dd horizontal lines
        for i in range(0, int(MAX_DEPTH), Y_LABEL_DISTANCE):
            row_index = int(i / SAMPLE_RESOLUTION)
            hline = pg.InfiniteLine(pos=row_index, angle=0, pen=pg.mkPen(color='w', style=pg.QtCore.Qt.DotLine))
            self.waterfall.addItem(hline)

        # === Colorbar BELOW the plot to save width ===
        self.colorbar = pg.HistogramLUTWidget()
        self.colorbar.setImageItem(self.imageitem)
        self.colorbar.item.gradient.loadPreset('cyclic')
        # self.colorbar.setMaximumHeight(80)
        self.imageitem.setLevels(DEFAULT_LEVELS)
        # main_layout.addWidget(self.colorbar)

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

        # ➕ Settings button
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        hex_row.addWidget(self.settings_button)

        # ➕ Quit button
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        hex_row.addWidget(self.quit_button)

        controls_layout.addLayout(hex_row)

        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        main_layout.addWidget(controls_container)

    def set_gradient(self, gradient_name):
        self.current_gradient = gradient_name
        self.colorbar.item.gradient.loadPreset(gradient_name)

    def set_sound_speed(self, speed):
        global SPEED_OF_SOUND, SAMPLE_RESOLUTION, MAX_DEPTH, depth_labels

        SPEED_OF_SOUND = speed
        self.current_speed = speed
        SAMPLE_RESOLUTION = (SPEED_OF_SOUND * SAMPLE_TIME * 100) / 2
        MAX_DEPTH = NUM_SAMPLES * SAMPLE_RESOLUTION
        depth_labels = {int(i / SAMPLE_RESOLUTION): f"{i / 100}" for i in range(0, int(MAX_DEPTH), Y_LABEL_DISTANCE)}

        # Re-apply Y-axis ticks
        inverted_depth_labels = list(depth_labels.items())[::-1]
        self.waterfall.getAxis("left").setTicks([inverted_depth_labels])
        self.waterfall.getAxis("right").setTicks([inverted_depth_labels])

    def keyPressEvent(self, event):
        print("key pressed")
        if event.key() == ord('Q'):
            print("🛑 Quit triggered from keyboard.")
            self.close()
        elif event.key() == ord('C'):
            print("🔌 Connect triggered from keyboard.")
            self.connect_button.click()
        else:
            super().keyPressEvent(event)

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

    def open_settings(self):
        self.settings_dialog = SettingsDialog(
            self,
            current_gradient=self.current_gradient,
            current_speed=self.current_speed
        )
        self.settings_dialog.show()


def set_gradient(self, gradient_name):
    try:
        self.current_gradient = gradient_name
        self.colorbar.item.gradient.loadPreset(gradient_name)
        print(f"✅ Gradient changed to: {gradient_name}")
    except Exception as e:
        print(f"❌ Failed to apply gradient '{gradient_name}': {e}")


def get_current_gradient(self):
    try:
        return self.colorbar.item.gradient.currentPreset
    except Exception:
        return 'cyclic'  # Fallback


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Apply the dark theme
    qdarktheme.setup_theme("dark")
    window = WaterfallApp()

    # window.showFullScreen()
    window.show()

    sys.exit(app.exec())
