# Desktop client — connects to the web server's WebSocket for echo data.
# If no web server is running, spawns one as a subprocess.
import asyncio
import json
import logging
import subprocess
import sys
import threading

import numpy as np
import pyqtgraph as pg
import qdarktheme
from PyQt5.QtCore import QObject, Qt, pyqtSignal
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from qasync import QEventLoop

log = logging.getLogger(__name__)

MAX_ROWS = 300  # Number of time steps (Y-axis)
Y_LABEL_DISTANCE = 50  # distance between labels in cm
DEFAULT_LEVELS = (0, 256)

# Default server URL
DEFAULT_SERVER_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# WebSocket client — receives echo data from the web server
# ---------------------------------------------------------------------------


class WebSocketClient(QObject):
    """WebSocket client running in a background thread with its own event loop.

    qasync's event loop doesn't support TCP ``create_connection``, so we run
    the websockets client in a dedicated thread and bridge data back to Qt
    via pyqtSignal.
    """

    packet_received = pyqtSignal(dict)
    connection_changed = pyqtSignal(str)  # "connected", "reconnecting"

    def __init__(self, server_url: str = DEFAULT_SERVER_URL):
        super().__init__()
        self.server_url = server_url.rstrip("/")
        self._ws_url = (
            self.server_url.replace("http://", "ws://").replace("https://", "wss://")
            + "/ws"
        )
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self):
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._thread_main, daemon=True, name="ws-client"
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def _thread_main(self):
        """Entry point for the background thread — runs its own asyncio loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run())
        finally:
            loop.close()

    async def _run(self):
        import websockets

        retry_delay = 1.0
        while not self._stop_event.is_set():
            try:
                self.connection_changed.emit("reconnecting")
                async with websockets.connect(self._ws_url) as ws:
                    self.connection_changed.emit("connected")
                    retry_delay = 1.0
                    async for raw in ws:
                        if self._stop_event.is_set():
                            break
                        try:
                            data = json.loads(raw)
                            self.packet_received.emit(data)
                        except json.JSONDecodeError:
                            log.warning("Invalid JSON from WebSocket")
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.warning("WebSocket error: %s — retrying in %.0fs", e, retry_delay)
                self.connection_changed.emit("reconnecting")
                # Use stop_event.wait so we can exit promptly
                if self._stop_event.wait(timeout=retry_delay):
                    break
                retry_delay = min(retry_delay * 2, 30.0)


# ---------------------------------------------------------------------------
# Web server lifecycle — auto-detect or spawn
# ---------------------------------------------------------------------------


class WebServerManager:
    """Checks for an existing web server and spawns one if needed."""

    def __init__(self, server_url: str = DEFAULT_SERVER_URL):
        self.server_url = server_url.rstrip("/")
        self._process: subprocess.Popen | None = None
        self._owned = False  # True if we spawned the server

    async def ensure_running(self) -> bool:
        """Return True once the server is reachable. Spawns if needed."""
        if await asyncio.get_event_loop().run_in_executor(None, self._is_reachable):
            log.info("Web server already running at %s", self.server_url)
            return True

        log.info("No web server found — spawning one...")
        self._spawn()
        # Wait for it to become reachable
        for _ in range(60):  # up to ~30 s
            await asyncio.sleep(0.5)
            if await asyncio.get_event_loop().run_in_executor(None, self._is_reachable):
                log.info("Web server is now reachable")
                return True

        log.error("Web server failed to start within timeout")
        return False

    def _is_reachable(self) -> bool:
        import urllib.request

        try:
            resp = urllib.request.urlopen(f"{self.server_url}/api/settings", timeout=2)
            return resp.status == 200
        except Exception:
            return False

    def _spawn(self):
        self._process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "open_echo.web:app",
                "--host",
                "0.0.0.0",
                "--port",
                "8000",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._owned = True

    def shutdown(self):
        if self._owned and self._process:
            log.info("Shutting down spawned web server (pid %d)", self._process.pid)
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=2)
            self._process = None


# ---------------------------------------------------------------------------
# HTTP helpers — synchronous (run via executor from qasync loop)
# ---------------------------------------------------------------------------


def _fetch_settings_sync(server_url: str) -> dict | None:
    import json
    import urllib.request

    try:
        resp = urllib.request.urlopen(f"{server_url}/api/settings", timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        log.error("Failed to fetch settings: %s", e)
        return None


def _push_settings_sync(server_url: str, settings_dict: dict) -> dict | None:
    import json
    import urllib.request

    try:
        data = json.dumps(settings_dict).encode("utf-8")
        req = urllib.request.Request(
            f"{server_url}/api/settings",
            data=data,
            headers={"Content-Type": "application/json"},
            method="PUT",
        )
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        log.error("Failed to push settings: %s", e)
        return None


def _fetch_serial_ports_sync(server_url: str) -> list[str]:
    import json
    import urllib.request

    try:
        resp = urllib.request.urlopen(f"{server_url}/api/serial-ports", timeout=5)
        return json.loads(resp.read())
    except Exception as e:
        log.error("Failed to fetch serial ports: %s", e)
        return []


async def fetch_settings(server_url: str) -> dict | None:
    return await asyncio.get_event_loop().run_in_executor(
        None, _fetch_settings_sync, server_url
    )


async def push_settings(server_url: str, settings_dict: dict) -> dict | None:
    return await asyncio.get_event_loop().run_in_executor(
        None, _push_settings_sync, server_url, settings_dict
    )


async def fetch_serial_ports(server_url: str) -> list[str]:
    return await asyncio.get_event_loop().run_in_executor(
        None, _fetch_serial_ports_sync, server_url
    )


# ---------------------------------------------------------------------------
# Settings Dialog — local display + proxied echo settings
# ---------------------------------------------------------------------------


class SettingsDialog(QWidget):
    settings_applied = pyqtSignal()

    def __init__(
        self,
        parent=None,
        current_gradient="cyclic",
        server_url: str = DEFAULT_SERVER_URL,
    ):
        super().__init__(parent)
        self.main_app = parent
        self.server_url = server_url
        self.setWindowTitle("Settings")
        self.setFixedSize(380, 750)

        # Populated asynchronously after show()
        self._server_settings: dict = {}

        outer_layout = QVBoxLayout(self)
        outer_layout.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]

        card = QWidget()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(12)

        # === Display Settings (local) ===
        display_header = QLabel("Display")
        display_header.setStyleSheet("font-weight: bold; font-size: 15px;")
        card_layout.addWidget(display_header)

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

        self.large_depth_checkbox = QCheckBox("Show Depth Display")
        self.large_depth_checkbox.setChecked(
            getattr(parent, "large_depth_visible", True)
        )
        card_layout.addWidget(self.large_depth_checkbox)

        # === Echo Settings (proxied to web server) ===
        echo_header = QLabel("Echo Sounder")
        echo_header.setStyleSheet("font-weight: bold; font-size: 15px;")
        card_layout.addWidget(echo_header)

        # Connection type
        card_layout.addWidget(QLabel("Connection:"))
        self.connection_type_dropdown = QComboBox()
        self.connection_type_dropdown.addItems(["SERIAL", "UDP"])
        self.connection_type_dropdown.currentTextChanged.connect(
            self._on_connection_type_changed
        )
        card_layout.addWidget(self.connection_type_dropdown)

        # Serial port
        self.serial_port_label = QLabel("Serial Port:")
        card_layout.addWidget(self.serial_port_label)
        self.serial_port_dropdown = QComboBox()
        card_layout.addWidget(self.serial_port_dropdown)

        # UDP port
        self.udp_port_label = QLabel("UDP Port:")
        card_layout.addWidget(self.udp_port_label)
        self.udp_port_input = QLineEdit()
        self.udp_port_input.setText("9999")
        card_layout.addWidget(self.udp_port_input)

        # Medium
        card_layout.addWidget(QLabel("Medium:"))
        self.medium_dropdown = QComboBox()
        self.medium_dropdown.addItems(["water", "air"])
        card_layout.addWidget(self.medium_dropdown)

        # Num samples
        ns_row = QHBoxLayout()
        ns_row.addWidget(QLabel("Num Samples:"))
        self.num_samples_input = QLineEdit()
        self.num_samples_input.setText("1800")
        self.num_samples_input.setMaximumWidth(120)
        ns_row.addWidget(self.num_samples_input)
        ns_row.addStretch()
        card_layout.addLayout(ns_row)

        # === Depth Output ===
        depth_header = QLabel("Depth Output")
        depth_header.setStyleSheet("font-weight: bold; font-size: 15px;")
        card_layout.addWidget(depth_header)

        td_row = QHBoxLayout()
        td_row.addWidget(QLabel("Transducer depth (m):"))
        self.transducer_depth_input = QLineEdit("0.0")
        self.transducer_depth_input.setMaximumWidth(80)
        td_row.addWidget(self.transducer_depth_input)
        td_row.addStretch()
        card_layout.addLayout(td_row)

        draft_row = QHBoxLayout()
        draft_row.addWidget(QLabel("Draft (m):"))
        self.draft_input = QLineEdit("0.0")
        self.draft_input.setMaximumWidth(80)
        draft_row.addWidget(self.draft_input)
        draft_row.addStretch()
        card_layout.addLayout(draft_row)

        # SignalK
        self.signalk_enable = QCheckBox("SignalK output")
        card_layout.addWidget(self.signalk_enable)
        sk_row = QHBoxLayout()
        sk_row.addWidget(QLabel("SignalK address:"))
        self.signalk_address_input = QLineEdit("localhost:3000")
        sk_row.addWidget(self.signalk_address_input)
        card_layout.addLayout(sk_row)

        # NMEA
        self.nmea_enable = QCheckBox("NMEA0183 output")
        card_layout.addWidget(self.nmea_enable)
        nmea_row = QHBoxLayout()
        nmea_row.addWidget(QLabel("NMEA address:"))
        self.nmea_address_input = QLineEdit("localhost:10110")
        nmea_row.addWidget(self.nmea_address_input)
        card_layout.addLayout(nmea_row)

        # === Buttons ===
        button_layout = QHBoxLayout()
        apply_button = QPushButton("Apply")
        apply_button.clicked.connect(self._apply)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.close)  # type: ignore[arg-type]
        button_layout.addWidget(apply_button)
        button_layout.addWidget(cancel_button)
        card_layout.addLayout(button_layout)

        outer_layout.addWidget(card)

        self.setStyleSheet(
            """
            QWidget#Card {
                background-color: #2b2b2b;
                border-radius: 12px;
                padding: 15px;
            }
            QLabel { color: #ffffff; font-size: 14px; }
            QComboBox {
                background-color: #3c3c3c; color: white;
                padding: 4px; border-radius: 4px;
            }
            QLineEdit {
                background-color: #3c3c3c; color: white;
                padding: 4px; border-radius: 4px;
            }
            QPushButton {
                background-color: #444444; border: 1px solid #666;
                padding: 5px 10px; border-radius: 6px;
            }
            QPushButton:hover { background-color: #555; }
        """
        )

        self.setLayout(outer_layout)
        self._on_connection_type_changed(self.connection_type_dropdown.currentText())

    # --- async population ---

    def showEvent(self, event):
        super().showEvent(event)
        asyncio.ensure_future(self._load_from_server())

    async def _load_from_server(self):
        """Fetch current settings + serial ports from web server."""
        settings, ports = await asyncio.gather(
            fetch_settings(self.server_url),
            fetch_serial_ports(self.server_url),
        )

        if settings is None:
            QMessageBox.warning(self, "Error", "Could not reach web server")
            return

        self._server_settings = settings

        # Populate widgets from server state
        ct = settings.get("connection_type")
        if ct:
            idx = self.connection_type_dropdown.findText(ct.upper())
            if idx >= 0:
                self.connection_type_dropdown.setCurrentIndex(idx)

        self.serial_port_dropdown.clear()
        self.serial_port_dropdown.addItems(ports)
        sp = settings.get("serial_port", "")
        idx = self.serial_port_dropdown.findText(sp)
        if idx >= 0:
            self.serial_port_dropdown.setCurrentIndex(idx)

        self.udp_port_input.setText(str(settings.get("udp_port", 9999)))
        self.num_samples_input.setText(str(settings.get("num_samples", 1800)))

        medium = settings.get("medium", "water")
        idx = self.medium_dropdown.findText(medium)
        if idx >= 0:
            self.medium_dropdown.setCurrentIndex(idx)

        self.transducer_depth_input.setText(str(settings.get("transducer_depth", 0.0)))
        self.draft_input.setText(str(settings.get("draft", 0.0)))

        self.signalk_enable.setChecked(settings.get("signalk_enable", False))
        self.signalk_address_input.setText(
            settings.get("signalk_address", "localhost:3000")
        )

        self.nmea_enable.setChecked(settings.get("nmea_enable", False))
        self.nmea_address_input.setText(settings.get("nmea_address", "localhost:10110"))

    def _on_connection_type_changed(self, text):
        is_serial = text.upper() == "SERIAL"
        self.serial_port_label.setVisible(is_serial)
        self.serial_port_dropdown.setVisible(is_serial)
        self.udp_port_label.setVisible(not is_serial)
        self.udp_port_input.setVisible(not is_serial)

    # --- apply ---

    def _apply(self):
        # Local display settings — applied immediately
        if self.main_app:
            self.main_app.set_gradient(self.gradient_dropdown.currentText())
            self.main_app.set_large_depth_display(self.large_depth_checkbox.isChecked())

        # Echo settings → push to server
        echo_settings = dict(self._server_settings)
        echo_settings["connection_type"] = (
            self.connection_type_dropdown.currentText().upper()
        )
        echo_settings["serial_port"] = self.serial_port_dropdown.currentText()
        try:
            echo_settings["udp_port"] = int(self.udp_port_input.text())
        except ValueError:
            echo_settings["udp_port"] = 9999
        try:
            echo_settings["num_samples"] = int(self.num_samples_input.text())
        except ValueError:
            echo_settings["num_samples"] = 1800
        echo_settings["medium"] = self.medium_dropdown.currentText()
        try:
            echo_settings["transducer_depth"] = float(
                self.transducer_depth_input.text()
            )
        except ValueError:
            echo_settings["transducer_depth"] = 0.0
        try:
            echo_settings["draft"] = float(self.draft_input.text())
        except ValueError:
            echo_settings["draft"] = 0.0
        echo_settings["signalk_enable"] = self.signalk_enable.isChecked()
        echo_settings["signalk_address"] = self.signalk_address_input.text()
        echo_settings["nmea_enable"] = self.nmea_enable.isChecked()
        echo_settings["nmea_address"] = self.nmea_address_input.text()

        asyncio.ensure_future(self._push_and_close(echo_settings))

    async def _push_and_close(self, echo_settings: dict):
        result = await push_settings(self.server_url, echo_settings)
        if result is None:
            QMessageBox.warning(
                self,
                "Error",
                "Failed to update settings on web server",
            )
        else:
            self.settings_applied.emit()
            self.close()


# ---------------------------------------------------------------------------
# Main application window
# ---------------------------------------------------------------------------


class WaterfallApp(QMainWindow):
    def __init__(self, server_url: str = DEFAULT_SERVER_URL):
        super().__init__()
        self.server_url = server_url

        self.current_gradient = "cyclic"
        self.large_depth_visible = True

        # Sampling state — initialised from first WebSocket message
        self.num_samples = 1800
        self.resolution = 0.9768  # cm per row (water default)

        self.setWindowTitle("Open Echo Interface")
        self.setGeometry(0, 0, 480, 800)

        self._recompute_sampling_derived()
        self.data = np.zeros((MAX_ROWS, self.num_samples))

        # Solid background
        self.setAttribute(Qt.WA_TranslucentBackground, False)  # type: ignore[attr-defined]
        self.setWindowFlags(self.windowFlags() & ~Qt.FramelessWindowHint)  # type: ignore[attr-defined]
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
        self.waterfall.setMinimumHeight(400)
        self.waterfall.invertY(True)

        main_layout.addWidget(self.waterfall)

        inverted_depth_labels = list(self.depth_labels.items())[::-1]
        self.waterfall.getAxis("left").setTicks([inverted_depth_labels])
        self.depth_line = pg.InfiniteLine(angle=0, pen=pg.mkPen("r", width=2))
        self.waterfall.addItem(self.depth_line)

        right_axis = self.waterfall.getAxis("right")
        right_axis.setTicks([inverted_depth_labels])
        right_axis.setStyle(showValues=True)

        self._depth_lines: list[pg.InfiniteLine] = []
        self._add_grid_lines()

        # === Colorbar (hidden but still drives LUT) ===
        self.colorbar = pg.HistogramLUTWidget()
        self.colorbar.setImageItem(self.imageitem)
        self.colorbar.item.gradient.loadPreset("cyclic")
        self.imageitem.setLevels(DEFAULT_LEVELS)

        # === Controls ===
        controls_layout = QVBoxLayout()

        # Large Depth Display
        self.large_depth_label = QLabel("--- m")
        self.large_depth_label.setAlignment(Qt.AlignCenter)  # type: ignore[attr-defined]
        self.large_depth_label.setStyleSheet(
            """
            QLabel {
                color: #00ffcc;
                font-size: 64px;
                font-weight: bold;
            }
        """
        )
        self.large_depth_label.setVisible(True)
        controls_layout.addWidget(self.large_depth_label)

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
        controls_layout.addWidget(info_container)

        # Bottom row: status + buttons
        bottom_row = QHBoxLayout()

        self.status_label = QLabel("Starting...")
        self.status_label.setStyleSheet("color: #aaa; font-size: 12px;")
        bottom_row.addWidget(self.status_label)

        bottom_row.addStretch()

        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.open_settings)
        bottom_row.addWidget(self.settings_button)

        self.web_button = QPushButton("Open Web UI")
        self.web_button.clicked.connect(self._open_web_ui)
        bottom_row.addWidget(self.web_button)

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)  # type: ignore[arg-type]
        bottom_row.addWidget(self.quit_button)

        controls_layout.addLayout(bottom_row)

        controls_container = QWidget()
        controls_container.setLayout(controls_layout)
        main_layout.addWidget(controls_container)

        # === WebSocket client ===
        self._ws_client = WebSocketClient(server_url)
        self._ws_client.packet_received.connect(self._on_ws_packet)
        self._ws_client.connection_changed.connect(self._on_connection_changed)

        # === Web server manager ===
        self._server_manager = WebServerManager(server_url)

    # --- Lifecycle ---

    async def start_connection(self):
        """Ensure web server is running, then start WebSocket client."""
        self._update_status("Starting server...")
        ok = await self._server_manager.ensure_running()
        if not ok:
            self._update_status("Server failed to start")
            QMessageBox.critical(
                self,
                "Error",
                "Could not start or connect to the web server.\n"
                "Try running 'openecho web' manually.",
            )
            return

        # Check if this is the first run (no settings configured yet)
        settings = await fetch_settings(self.server_url)
        if settings and settings.get("serial_port") == "init":
            self._update_status("Waiting for configuration...")
            self.open_settings(on_first_run=True)
            return

        self._ws_client.start()

    def closeEvent(self, event):
        self._ws_client.stop()
        self._server_manager.shutdown()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == ord("Q"):
            self.close()
        else:
            super().keyPressEvent(event)

    # --- WebSocket data handling ---

    def _on_ws_packet(self, data: dict):
        spectrogram = data.get("spectrogram")
        if spectrogram is None:
            return

        spectrogram = np.array(spectrogram, dtype=np.uint8)

        # Dynamic num_samples handling
        if len(spectrogram) != self.num_samples:
            self.num_samples = len(spectrogram)
            self.data = np.zeros((MAX_ROWS, self.num_samples))
            self._recompute_sampling_derived()
            self._refresh_axes_and_grid()

        # Update resolution if it changed
        new_resolution = data.get("resolution", self.resolution)
        if abs(new_resolution - self.resolution) > 0.001:
            self.resolution = new_resolution
            self._recompute_sampling_derived()
            self._refresh_axes_and_grid()

        depth_m = data.get("measured_depth", 0.0)
        temperature = data.get("temperature", 0.0)
        drive_voltage = data.get("drive_voltage", 0.0)

        # Convert depth_m back to index for the depth line position
        depth_index = depth_m / (self.resolution / 100) if self.resolution > 0 else 0

        self._waterfall_plot_callback(
            spectrogram, depth_index, depth_m, temperature, drive_voltage
        )

    def _waterfall_plot_callback(
        self, spectrogram, depth_index, depth_m, temperature, drive_voltage
    ):
        self.data = np.roll(self.data, -1, axis=0)
        self.data[-1, :] = spectrogram
        self.imageitem.setImage(self.data.T, autoLevels=False)

        sigma = np.std(self.data)
        mean = np.mean(self.data)
        self.imageitem.setLevels((mean - 2 * sigma, mean + 2 * sigma))

        depth_cm = depth_m * 100
        self.depth_label.setText(f"Depth: {depth_cm:.1f} cm | Index: {depth_index:.0f}")
        self.temperature_label.setText(f"Temperature: {temperature:.1f} °C")
        self.drive_voltage_label.setText(f"vDRV: {drive_voltage:.1f} V")
        self.depth_line.setPos(depth_index)

        if self.large_depth_label.isVisible():
            self.large_depth_label.setText(f"{depth_m:.1f} m")

    # --- Connection status ---

    def _on_connection_changed(self, status: str):
        status_map = {
            "connected": "Server: connected",
            "reconnecting": "Server: reconnecting...",
            "starting": "Server: starting...",
        }
        self._update_status(status_map.get(status, status))

    def _update_status(self, text: str):
        self.status_label.setText(text)

    # --- Display settings ---

    def set_gradient(self, gradient_name):
        self.current_gradient = gradient_name
        self.colorbar.item.gradient.loadPreset(gradient_name)

    def set_large_depth_display(self, enabled: bool):
        self.large_depth_visible = enabled
        self.large_depth_label.setVisible(enabled)

    # --- Settings dialog ---

    def open_settings(self, on_first_run=False):
        self.settings_dialog = SettingsDialog(
            parent=self,
            current_gradient=self.current_gradient,
            server_url=self.server_url,
        )
        if on_first_run:
            # Start the WebSocket client once the user applies settings
            self.settings_dialog.settings_applied.connect(self._ws_client.start)
        self.settings_dialog.show()

    def _open_web_ui(self):
        from PyQt5.QtCore import QUrl
        from PyQt5.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl(self.server_url))

    # --- Sampling / axes ---

    def _recompute_sampling_derived(self):
        self.sample_resolution = self.resolution  # cm per row
        if self.sample_resolution <= 0:
            self.sample_resolution = 0.9768  # safe fallback
        self.max_depth = int(self.num_samples * self.sample_resolution)
        self.depth_labels = {
            int(i / self.sample_resolution): f"{i / 100}"
            for i in range(0, int(self.max_depth), Y_LABEL_DISTANCE)
        }

    def _refresh_axes_and_grid(self):
        inverted_depth_labels = list(self.depth_labels.items())[::-1]
        self.waterfall.getAxis("left").setTicks([inverted_depth_labels])
        self.waterfall.getAxis("right").setTicks([inverted_depth_labels])
        self._remove_grid_lines()
        self._add_grid_lines()

    def _add_grid_lines(self):
        for i in range(0, int(self.max_depth), Y_LABEL_DISTANCE):
            row_index = int(i / self.sample_resolution)
            hline = pg.InfiniteLine(
                pos=row_index,
                angle=0,
                pen=pg.mkPen(color="w", style=pg.QtCore.Qt.DotLine),
            )
            self.waterfall.addItem(hline)
            self._depth_lines.append(hline)

    def _remove_grid_lines(self):
        for ln in self._depth_lines:
            try:
                self.waterfall.removeItem(ln)
            except Exception:
                pass
        self._depth_lines.clear()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run_desktop(server_url: str = DEFAULT_SERVER_URL):
    app = QApplication(sys.argv)
    qdarktheme.setup_theme("dark")

    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = WaterfallApp(server_url=server_url)
    window.show()

    # Kick off the async server check + WebSocket connection
    asyncio.ensure_future(window.start_connection())

    with loop:
        loop.run_forever()


if __name__ == "__main__":
    run_desktop()
