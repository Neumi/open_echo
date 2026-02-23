"""Tests for desktop.py helper functions and classes."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import MagicMock

import pytest
from open_echo.desktop import (
    WebServerManager,
    WebSocketClient,
    _fetch_serial_ports_sync,
    _fetch_settings_sync,
    _push_settings_sync,
)

# ---------------------------------------------------------------------------
# Tiny HTTP server used to test the sync HTTP helpers and WebServerManager
# ---------------------------------------------------------------------------


class _MockHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for testing sync helpers."""

    # Class-level response config — set before each test
    response_body: bytes = b"{}"
    response_code: int = 200

    def do_GET(self):
        self.send_response(self.response_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(self.response_body)

    def do_PUT(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        # Echo back the received JSON
        self.send_response(self.response_code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # suppress log spam


@pytest.fixture
def mock_server():
    """Start a local HTTP server on an ephemeral port for tests."""
    server = HTTPServer(("127.0.0.1", 0), _MockHandler)
    port = server.server_address[1]
    url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield url, server
    server.shutdown()


# ---------------------------------------------------------------------------
# Sync HTTP helpers
# ---------------------------------------------------------------------------


class TestFetchSettingsSync:
    def test_returns_dict_on_success(self, mock_server):
        url, server = mock_server
        _MockHandler.response_body = json.dumps(
            {"num_samples": 1800, "serial_port": "init"}
        ).encode()
        _MockHandler.response_code = 200

        result = _fetch_settings_sync(url)
        assert result is not None
        assert result["num_samples"] == 1800

    def test_returns_none_on_connection_error(self):
        result = _fetch_settings_sync("http://127.0.0.1:1")
        assert result is None


class TestPushSettingsSync:
    def test_returns_echoed_dict_on_success(self, mock_server):
        url, server = mock_server
        _MockHandler.response_code = 200

        payload = {"num_samples": 900, "serial_port": "/dev/tty0"}
        result = _push_settings_sync(url, payload)
        assert result is not None
        assert result["num_samples"] == 900

    def test_returns_none_on_connection_error(self):
        result = _push_settings_sync("http://127.0.0.1:1", {"a": 1})
        assert result is None


class TestFetchSerialPortsSync:
    def test_returns_list_on_success(self, mock_server):
        url, server = mock_server
        _MockHandler.response_body = json.dumps(
            ["/dev/ttyUSB0", "/dev/ttyACM0"]
        ).encode()
        _MockHandler.response_code = 200

        result = _fetch_serial_ports_sync(url)
        assert result == ["/dev/ttyUSB0", "/dev/ttyACM0"]

    def test_returns_empty_list_on_error(self):
        result = _fetch_serial_ports_sync("http://127.0.0.1:1")
        assert result == []


# ---------------------------------------------------------------------------
# WebServerManager
# ---------------------------------------------------------------------------


class TestWebServerManager:
    def test_is_reachable_returns_true_when_server_up(self, mock_server):
        url, server = mock_server
        _MockHandler.response_code = 200
        _MockHandler.response_body = b'{"serial_port":"init"}'

        mgr = WebServerManager(url)
        assert mgr._is_reachable() is True

    def test_is_reachable_returns_false_when_server_down(self):
        mgr = WebServerManager("http://127.0.0.1:1")
        assert mgr._is_reachable() is False

    def test_shutdown_noop_when_not_owned(self):
        mgr = WebServerManager()
        mgr._owned = False
        mgr._process = MagicMock()
        mgr.shutdown()
        mgr._process.terminate.assert_not_called()

    def test_shutdown_terminates_owned_process(self):
        mgr = WebServerManager()
        mgr._owned = True
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.wait.return_value = None
        mgr._process = mock_proc

        mgr.shutdown()

        mock_proc.terminate.assert_called_once()
        assert mgr._process is None

    @pytest.mark.asyncio
    async def test_ensure_running_returns_true_when_already_up(self, mock_server):
        url, server = mock_server
        _MockHandler.response_code = 200
        _MockHandler.response_body = b'{"serial_port":"init"}'

        mgr = WebServerManager(url)
        result = await mgr.ensure_running()
        assert result is True
        assert mgr._owned is False


# ---------------------------------------------------------------------------
# WebSocketClient
# ---------------------------------------------------------------------------


class TestWebSocketClient:
    def test_url_construction(self):
        ws = WebSocketClient("http://localhost:8000")
        assert ws._ws_url == "ws://localhost:8000/ws"

    def test_url_construction_https(self):
        ws = WebSocketClient("https://example.com:443")
        assert ws._ws_url == "wss://example.com:443/ws"

    def test_url_strips_trailing_slash(self):
        ws = WebSocketClient("http://localhost:8000/")
        assert ws._ws_url == "ws://localhost:8000/ws"

    def test_stop_sets_event_and_clears_thread(self):
        ws = WebSocketClient()
        ws._stop_event = threading.Event()
        mock_thread = MagicMock()
        mock_thread.join.return_value = None
        ws._thread = mock_thread

        ws.stop()

        assert ws._stop_event.is_set()
        mock_thread.join.assert_called_once()
        assert ws._thread is None
