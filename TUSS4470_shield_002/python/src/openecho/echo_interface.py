import sys
import numpy as np
import serial
import serial.tools.list_ports
import struct
import time
import socket
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QComboBox,
    QPushButton,
    QLabel,
    QLineEdit,
)
from PyQt5.QtCore import pyqtSignal
import pyqtgraph as pg
import qdarktheme
from PyQt5.QtWidgets import (
    QHBoxLayout,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QCheckBox, QLineEdit
from PyQt5.QtWidgets import QApplication

# Async integration
import asyncio
from qasync import QEventLoop

# Use shared settings/readers
from openecho.settings import Settings
from openecho.echo import ConnectionTypeEnum

# Serial Configuration
BAUD_RATE = 250000
NUM_SAMPLES = 1800 # (X-axis)

MAX_ROWS = 300  # Number of time steps (Y-axis)
Y_LABEL_DISTANCE = 50  # distance between labels in cm

SPEED_OF_SOUND = 1440  # default sound speed meters/second in water
# SPEED_OF_SOUND = 343  # default sound speed meters/second in water

# SAMPLE_TIME = 52.226e-6  # 13.2 microseconds on Atmega328 max sample speed plus 50 microseconds delay in sampling loop
# SAMPLE_TIME = 47.0e-6
# SAMPLE_TIME = 41.666e-6 # 13.2 microseconds on Atmega328 max sample speed plus 40 microseconds delay in sampling loop
# SAMPLE_TIME = 22.22e-6  # 13.2 microseconds on Atmega328 max sample speed plus 20 microseconds delay in sampling loop
SAMPLE_TIME = 13.2e-6     # 13.2 microseconds on Atmega328 max sample speed without additional delay
# SAMPLE_TIME = 11.0e-6     # 13.2 microseconds on RP2040 max sample speed with 10 microseconds additional delay per sample
# SAMPLE_TIME = 7.682e-6  # 7.682 microseconds on STM32F103 max sample speed
# SAMPLE_TIME = 6.0e-6  # 6 microseconds on RP2040 max sample speed with 5 microseconds additional delay per sample
# SAMPLE_TIME = 1.290e-6     # 13.2 microseconds on RP2040 max sample speed without additional delay

DEFAULT_LEVELS = (0, 256)  # Expected data range

SAMPLE_RESOLUTION = (SPEED_OF_SOUND * SAMPLE_TIME * 100) / 2  # cm per row (0.99 cm per row)
PACKET_SIZE = 1 + 6 + NUM_SAMPLES + 1  # header + payload + checksum
MAX_DEPTH = NUM_SAMPLES * SAMPLE_RESOLUTION  # Total depth in cm
depth_labels = {int(i / SAMPLE_RESOLUTION): f"{i / 100}" for i in range(0, int(MAX_DEPTH), Y_LABEL_DISTANCE)}


def read_packet(ser):
    while True:
        header = ser.read(1)
        if header != b"\xaa":
            continue  # Wait for the start byte

        payload = ser.read(6 + NUM_SAMPLES)
        checksum = ser.read(1)

        if len(payload) != 6 + NUM_SAMPLES or len(checksum) != 1:
            continue  # Incomplete packet

        # Verify checksum
        calc_checksum = 0
        for byte in payload:
            calc_checksum ^= byte
        if calc_checksum != checksum[0]:
            print("⚠️ Checksum mismatch: {} != {}".format(calc_checksum, checksum[0]))
            continue

        # Unpack payload (firmware sends little-endian raw struct bytes)
        depth, temp_scaled, vDrv_scaled = struct.unpack("<HhH", payload[:6])
        depth = min(depth, NUM_SAMPLES)

        sample_bytes = payload[6:6+NUM_SAMPLES]
        values = np.frombuffer(sample_bytes, dtype=np.uint8, count=NUM_SAMPLES)

        temperature = temp_scaled / 100.0
        drive_voltage = vDrv_scaled / 100.0

        return values, depth, temperature, drive_voltage


def generate_dbt_sentence(depth_cm):
    depth_m = depth_cm / 100.0
    depth_ft = depth_m * 3.28084
    depth_fathoms = depth_m * 0.546807

    # Format the DBT sentence without checksum
    sentence_body = f"DBT,{depth_ft:.1f},f,{depth_m:.1f},M,{depth_fathoms:.1f},F"

    # Compute checksum
    checksum = 0
    for char in sentence_body:
        checksum ^= ord(char)

    nmea_sentence = f"${sentence_body}*{checksum:02X}"
    return nmea_sentence


def get_serial_ports():
    """Retrieve a list of available serial ports."""
    return [port.device for port in serial.tools.list_ports.comports()][::-1]


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class SettingsDialog(QWidget):
    def __init__(self, parent=None, current_gradient='cyclic', current_speed=343, nmea_enabled=False, nmea_port=10110,
                 nmea_address="127.0.0.1"):
        super().__init__(parent)
        self.setWindowTitle("Chart Settings")
        self.setFixedSize(320, 550)

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
        self.gradient_dropdown.addItems(
            [
                "viridis",
                "plasma",
                "inferno",
                "magma",
                "thermal",
                "flame",
                "yellowy",
                "bipolar",
                "spectrum",
                "cyclic",
                "greyclip",
                "grey",
            ]
        )
        self.gradient_dropdown.setCurrentText(current_gradient)
        card_layout.addWidget(self.gradient_dropdown)

        # --- Speed of Sound ---
        card_layout.addWidget(QLabel("Speed of Sound:"))
        self.speed_dropdown = QComboBox()
        self.speed_dropdown.addItems(["343m/s (Air)", "1440m/s (Water)"])
        self.speed_dropdown.setCurrentIndex(1 if current_speed == 1440 else 0)
        card_layout.addWidget(self.speed_dropdown)

        # --- NMEA Output Section ---
        nmea_section = QVBoxLayout()
        nmea_section.setSpacing(8)

        # Section title
        nmea_label = QLabel("NMEA TCP Output:")
        nmea_label.setStyleSheet("font-weight: bold;")
        nmea_section.addWidget(nmea_label)

        # Enable checkbox
        self.nmea_enable_checkbox = QCheckBox("Enable NMEA Output")
        self.nmea_enable_checkbox.setStyleSheet(
            "QCheckBox:hover { text-decoration: none; }"
        )
        nmea_section.addWidget(self.nmea_enable_checkbox)

        # Address display row
        addr_row = QHBoxLayout()
        addr_label = QLabel("Address:")
        addr_label.setMinimumWidth(60)

        self.addr_display = QLabel(nmea_address)
        self.addr_display.setStyleSheet("color: #cccccc; padding: 2px;")
        self.addr_display.setTextInteractionFlags(
            Qt.TextSelectableByMouse
        )  # Allow text copy

        copy_button = QPushButton("Copy")
        copy_button.setFixedHeight(22)
        copy_button.setStyleSheet("font-size: 11px; padding: 2px 6px;")
        copy_button.clicked.connect(
            lambda: QApplication.clipboard().setText(nmea_address)
        )

        addr_row.addWidget(addr_label)
        addr_row.addWidget(self.addr_display)
        addr_row.addWidget(copy_button)
        addr_row.addStretch()
        nmea_section.addLayout(addr_row)

        # Port input with label to the left
        port_row = QHBoxLayout()

        # --- Large Depth Display Option ---
        self.large_depth_checkbox = QCheckBox("Show Depth Display")
        self.large_depth_checkbox.setChecked(
            getattr(parent, "large_depth_visible", True)
        )
        card_layout.addWidget(self.large_depth_checkbox)

        port_label = QLabel("Port:")
        port_label.setMinimumWidth(40)

        self.port_input = QLineEdit()
        self.port_input.setPlaceholderText("TCP Port (default: 10110)")
        self.port_input.setText(str(nmea_port))
        self.port_input.setMaximumWidth(200)

        port_row.addWidget(port_label)
        port_row.addWidget(self.port_input)
        port_row.addStretch()
        nmea_section.addLayout(port_row)

        # ✅ Connect AFTER both widgets are created
        self.nmea_enable_checkbox.toggled.connect(self.port_input.setEnabled)

        # ✅ Apply initial state (pass nmea_enabled into the constructor!)
        self.nmea_enable_checkbox.setChecked(nmea_enabled)
        self.port_input.setEnabled(nmea_enabled)

        # ✅ Add to card layout
        card_layout.addLayout(nmea_section)

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
        selected_speed = 343 if self.speed_dropdown.currentIndex() == 0 else 1440
        nmea_enabled = self.nmea_enable_checkbox.isChecked()
        nmea_port = (
            int(self.port_input.text()) if self.port_input.text().isdigit() else 10110
        )

        if self.main_app:
            self.main_app.set_gradient(selected_gradient)
            self.main_app.set_sound_speed(selected_speed)
            self.main_app.configure_nmea_output(enabled=nmea_enabled, port=nmea_port)
            self.main_app.set_large_depth_display(self.large_depth_checkbox.isChecked())

        self.close()


class WaterfallApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.serial_thread = None  # kept for backward-compat, no longer used

        # Single async reader task (generic AsyncReader)
        self._reader_task = None

        self.nmea_enabled = False
        self.nmea_port = 10110
        self.nmea_socket = None
        self.nmea_output_enabled = False

        self.current_gradient = 'cyclic'  # default color scheme
        self.current_speed = SPEED_OF_SOUND  # default sound speed (343)

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
        self.imageitem = pg.ImageItem(axisOrder="row-major")
        self.waterfall.addItem(self.imageitem)
        self.waterfall.setMouseEnabled(x=False, y=False)
        self.waterfall.setMinimumHeight(400)  # Slightly more vertical space
        self.waterfall.invertY(True)

        main_layout.addWidget(self.waterfall)

        inverted_depth_labels = list(depth_labels.items())[::-1]
        self.waterfall.getAxis("left").setTicks([inverted_depth_labels])
        self.depth_line = pg.InfiniteLine(angle=0, pen=pg.mkPen("r", width=2))
        self.waterfall.addItem(self.depth_line)

        # Mirror Y-axis ticks to the right side
        right_axis = self.waterfall.getAxis("right")
        right_axis.setTicks([inverted_depth_labels])
        right_axis.setStyle(showValues=True)

        # dd horizontal lines
        for i in range(0, int(MAX_DEPTH), Y_LABEL_DISTANCE):
            row_index = int(i / SAMPLE_RESOLUTION)
            hline = pg.InfiniteLine(
                pos=row_index,
                angle=0,
                pen=pg.mkPen(color="w", style=pg.QtCore.Qt.DotLine),
            )
            self.waterfall.addItem(hline)

        # === Colorbar BELOW the plot to save width ===
        self.colorbar = pg.HistogramLUTWidget()
        self.colorbar.setImageItem(self.imageitem)
        self.colorbar.item.gradient.loadPreset("cyclic")
        # self.colorbar.setMaximumHeight(80)
        self.imageitem.setLevels(DEFAULT_LEVELS)

        # main_layout.addWidget(self.colorbar)

        # === Controls (Vertical) ===
        controls_layout = QVBoxLayout()

        # Serial row
        serial_row = QHBoxLayout()

        # === UDP Connection Row ===
        udp_row = QHBoxLayout()

        udp_row.addWidget(QLabel("UDP Port:"))
        self.udp_port_input = QLineEdit()
        self.udp_port_input.setText("5005")
        self.udp_port_input.setMaximumWidth(100)
        udp_row.addWidget(self.udp_port_input)

        self.udp_connect_button = QPushButton("Connect UDP")
        self.udp_connect_button.clicked.connect(self.toggle_udp_connection)
        udp_row.addWidget(self.udp_connect_button)

        controls_layout.addLayout(udp_row)

        # === Large Depth Display ===
        self.large_depth_label = QLabel("--- m")
        self.large_depth_label.setAlignment(Qt.AlignCenter)
        self.large_depth_label.setStyleSheet("""
            QLabel {
                color: #00ffcc;
                font-size: 64px;
                font-weight: bold;
            }
        """)
        self.large_depth_label.setVisible(True)  # hidden by default
        serial_row.addWidget(self.large_depth_label)

        serial_row.addWidget(QLabel("Port:"))
        self.serial_dropdown = QComboBox()
        ports = get_serial_ports()
        self.serial_dropdown.addItems(ports)
        self.serial_dropdown.setMinimumWidth(150)
        serial_row.addWidget(self.serial_dropdown)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(
            self.toggle_serial_connection
        )  # Connects to toggle handler
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

        # Adapter to safely update UI from async packets
        from PyQt5.QtCore import QObject

        class EchoAdapter(QObject):
            packet_signal = pyqtSignal(object)

            def __init__(self, app_ref):
                super().__init__()
                self._app = app_ref
                self.packet_signal.connect(self._on_packet)

            def _on_packet(self, pkt):
                try:
                    # EchoPacket fields: spectrogram, depth_index, temperature, drive_voltage
                    spectrogram = np.array(pkt.spectrogram, dtype=np.uint8)
                    self._app.waterfall_plot_callback(
                        spectrogram,
                        pkt.depth_index,
                        pkt.temperature,
                        pkt.drive_voltage,
                    )
                except Exception as e:
                    print(f"❌ UI packet handling error: {e}")

            async def emit(self, pkt):
                self.packet_signal.emit(pkt)

        self._adapter = EchoAdapter(self)

    def connect_udp(self):
        try:
            udp_port = int(self.udp_port_input.text())
            settings = Settings(connection_type=ConnectionTypeEnum.UDP, udp_port=udp_port)
            self._start_reader(settings)
            print(f"✅ UDP listener started on port {udp_port}")
        except Exception as e:
            print(f"❌ Failed to start UDP listener: {e}")

    def disconnect_udp(self):
        self._stop_reader()
        print("🔌 UDP listener stopped")

    def toggle_udp_connection(self):
        if hasattr(self, 'udp_thread') and self.udp_thread and self.udp_thread.isRunning():
            self.disconnect_udp()
            self.udp_connect_button.setText("Connect UDP")
        else:
            self.connect_udp()
            if hasattr(self, 'udp_thread') and self.udp_thread.isRunning():
                self.udp_connect_button.setText("Disconnect UDP")

    def set_large_depth_display(self, enabled: bool):
        self.large_depth_visible = enabled
        self.large_depth_label.setVisible(enabled)

    def configure_nmea_output(self, enabled: bool, port: int):
        self.nmea_output_enabled = enabled
        self.nmea_port = port

        # Close previous connections if needed
        if hasattr(self, "nmea_client_socket") and self.nmea_client_socket:
            try:
                self.nmea_client_socket.close()
            except Exception:
                pass
            self.nmea_client_socket = None

        if hasattr(self, "nmea_server_socket") and self.nmea_server_socket:
            try:
                self.nmea_server_socket.close()
            except Exception:
                pass
            self.nmea_server_socket = None

        if enabled:
            try:
                import socket

                self.nmea_server_socket = socket.socket(
                    socket.AF_INET, socket.SOCK_STREAM
                )
                self.nmea_server_socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
                )
                self.nmea_server_socket.bind(("0.0.0.0", port))
                self.nmea_server_socket.listen(1)
                print(f"📡 Waiting for TCP NMEA connection on port {port}...")
                self.nmea_client_socket, _ = self.nmea_server_socket.accept()
                print(f"✅ NMEA client connected on port {port}")
            except Exception as e:
                print(f"❌ Failed to set up NMEA output: {e}")
                self.nmea_output_enabled = False

    def generate_dbt_sentence(self, depth_cm):
        depth_m = depth_cm / 100.0
        depth_ft = depth_m * 3.28084
        depth_fathoms = depth_m * 0.546807

        sentence_body = f"DBT,{depth_ft:.1f},f,{depth_m:.1f},M,{depth_fathoms:.1f},F"
        checksum = 0
        for char in sentence_body:
            checksum ^= ord(char)

        return f"${sentence_body}*{checksum:02X}\r\n"

    def set_gradient(self, gradient_name):
        self.current_gradient = gradient_name
        self.colorbar.item.gradient.loadPreset(gradient_name)

    def set_sound_speed(self, speed):
        global SPEED_OF_SOUND, SAMPLE_RESOLUTION, MAX_DEPTH, depth_labels

        SPEED_OF_SOUND = speed
        self.current_speed = speed
        SAMPLE_RESOLUTION = (SPEED_OF_SOUND * SAMPLE_TIME * 100) / 2
        print(SAMPLE_RESOLUTION)
        MAX_DEPTH = NUM_SAMPLES * SAMPLE_RESOLUTION
        depth_labels = {
            int(i / SAMPLE_RESOLUTION): f"{i / 100}"
            for i in range(0, int(MAX_DEPTH), Y_LABEL_DISTANCE)
        }

        # Re-apply Y-axis ticks
        inverted_depth_labels = list(depth_labels.items())[::-1]
        self.waterfall.getAxis("left").setTicks([inverted_depth_labels])
        self.waterfall.getAxis("right").setTicks([inverted_depth_labels])

    def keyPressEvent(self, event):
        print("key pressed")
        if event.key() == ord("Q"):
            print("🛑 Quit triggered from keyboard.")
            self.close()
        elif event.key() == ord("C"):
            print("🔌 Connect triggered from keyboard.")
            self.connect_button.click()
        else:
            super().keyPressEvent(event)

    def connect_serial(self):
        selected_port = self.serial_dropdown.currentText()
        try:
            settings = Settings(connection_type=ConnectionTypeEnum.SERIAL, serial_port=selected_port)
            self._start_reader(settings)
            print(f"✅ Connected to {selected_port}")
        except Exception as e:
            print(f"❌ Connection failed: {e}")

    def toggle_serial_connection(self):
        if self.serial_thread and self.serial_thread.isRunning():
            self.disconnect_serial()
            self.connect_button.setText("Connect")
        else:
            self.connect_serial()
            if self.serial_thread and self.serial_thread.isRunning():
                self.connect_button.setText("Disconnect")

    def disconnect_serial(self):
        if self._reader_task:
            self._stop_reader()
            print("🔌 Disconnected from serial device")
        else:
            print("⚠️ No active serial connection to disconnect")

    def waterfall_plot_callback(
        self, spectrogram, depth_index, temperature, drive_voltage
    ):
        self.data = np.roll(self.data, -1, axis=0)
        self.data[-1, :] = spectrogram
        self.imageitem.setImage(self.data.T, autoLevels=False)

        sigma = np.std(self.data)
        mean = np.mean(self.data)
        self.imageitem.setLevels((mean - 2 * sigma, mean + 2 * sigma))

        depth_cm = depth_index * SAMPLE_RESOLUTION
        self.depth_label.setText(f"Depth: {depth_cm:.1f} cm | Index: {depth_index:.0f}")
        self.temperature_label.setText(f"Temperature: {temperature:.1f} °C")
        self.drive_voltage_label.setText(f"vDRV: {drive_voltage:.1f} V")
        self.depth_line.setPos(depth_index)

        # Update big depth label (in meters, 1 decimal)
        if self.large_depth_label.isVisible():
            self.large_depth_label.setText(f"{depth_cm / 100:.1f} m")

        if hasattr(self, 'nmea_output_enabled') and self.nmea_output_enabled:
            now = time.time()

            # Check if it's time to send again
            if (
                not hasattr(self, "_last_nmea_sent")
                or (now - self._last_nmea_sent) >= 1.0
            ):
                print("Sending NMEA data")
                try:
                    depth_cm = depth_index * SAMPLE_RESOLUTION
                    depth_m = depth_cm / 100
                    depth_ft = depth_m * 3.28084
                    depth_fathoms = depth_m * 0.546807

                    def calculate_checksum(sentence):
                        checksum = 0
                        for char in sentence:
                            checksum ^= ord(char)
                        return f"*{checksum:02X}"

                    nmea_sentence = (
                        f"DBT,{depth_ft:.1f},f,{depth_m:.1f},M,{depth_fathoms:.1f},F"
                    )
                    full_sentence = (
                        f"${nmea_sentence}{calculate_checksum(nmea_sentence)}\r\n"
                    )

                    self.nmea_client_socket.sendall(full_sentence.encode("ascii"))

                    # Update timestamp
                    self._last_nmea_sent = now

                except Exception as e:
                    print(f"⚠️ NMEA send failed: {e}")

    def send_hex_value(self):
        hex_value = self.hex_input.text().strip()
        print(hex_value)

        if hex_value.startswith("0x") and len(hex_value) > 2:
            try:
                if self.serial_thread and self.serial_thread.isRunning():
                    with serial.Serial(
                        self.serial_dropdown.currentText(), BAUD_RATE
                    ) as ser:
                        ser.write(hex_value.encode())
                        print(f"Sent: {hex_value}")
            except ValueError:
                print("❌ Invalid hex format.")
        else:
            print("❌ Invalid hex value. Please enter a valid hex string (e.g., 0x1F)")

    def closeEvent(self, event):
        # Cancel async reader task
        if self._reader_task:
            try:
                self._reader_task.cancel()
            except Exception:
                pass
            self._reader_task = None
        event.accept()

    def _start_reader(self, settings: Settings):
        print("Starting reader...")
        # Generic starter for any AsyncReader subclass
        if self._reader_task:
            self._stop_reader()

        async def _run():
            reader_cls = settings.connection_type.value
            reader = reader_cls(settings)
            try:
                async with reader:
                    async for pkt in reader:
                        print("Reader started")
                        await self._adapter.emit(pkt)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"❌ Reader error: {e}")

        self._reader_task = asyncio.create_task(_run())

    def _stop_reader(self):
        if self._reader_task:
            try:
                self._reader_task.cancel()
            except Exception:
                pass
            self._reader_task = None

    def open_settings(self):
        device_ip = get_local_ip()

        self.settings_dialog = SettingsDialog(
            parent=self,
            current_gradient=self.current_gradient,
            current_speed=self.current_speed,
            nmea_enabled=self.nmea_output_enabled,
            nmea_port=self.nmea_port,
            nmea_address=device_ip,
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
        return "cyclic"  # Fallback


if __name__ == "__main__":
    app = QApplication(sys.argv)
    qdarktheme.setup_theme("dark")

    # Run Qt and asyncio together
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = WaterfallApp()
    window.show()

    with loop:
        loop.run_forever()
