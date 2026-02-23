"""Tests for the web server FastAPI endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from open_echo.settings import Settings
from open_echo.web import (
    ConnectionManager,
    EchoReader,
    app,
    echo_reader,
    output_manager,
)


@pytest.fixture
def client():
    """Provide a TestClient with lifespan mocked (no real background tasks)."""
    with (
        patch.object(echo_reader, "__enter__", return_value=echo_reader),
        patch.object(echo_reader, "__exit__", return_value=False),
        patch.object(output_manager, "__enter__", return_value=output_manager),
        patch.object(output_manager, "__exit__", return_value=False),
        patch.object(output_manager, "update_settings", new_callable=AsyncMock),
        patch.object(echo_reader, "update_settings"),
        patch("open_echo.web.Settings.load", return_value=Settings()),
        patch("open_echo.web.Settings.save"),
        TestClient(app, raise_server_exceptions=True) as c,
    ):
        yield c


@pytest.fixture(autouse=True)
def _reset_app_state():
    """Reset app.state.settings between tests."""
    app.state.settings = Settings()
    yield
    app.state.settings = Settings()


# ---------------------------------------------------------------------------
# JSON API: GET /api/settings
# ---------------------------------------------------------------------------


class TestApiGetSettings:
    def test_returns_200_with_default_settings(self, client):
        resp = client.get("/api/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert data["num_samples"] == 1800
        assert data["serial_port"] == "init"
        assert data["medium"] == "water"

    def test_reflects_updated_state(self, client):
        app.state.settings = Settings(num_samples=500, serial_port="/dev/ttyUSB0")
        resp = client.get("/api/settings")
        data = resp.json()
        assert data["num_samples"] == 500
        assert data["serial_port"] == "/dev/ttyUSB0"


# ---------------------------------------------------------------------------
# JSON API: PUT /api/settings
# ---------------------------------------------------------------------------


class TestApiPutSettings:
    def test_updates_settings_and_returns_new_state(self, client):
        resp = client.put(
            "/api/settings",
            json={
                "connection_type": "UDP",
                "udp_port": 7777,
                "num_samples": 900,
                "serial_port": "test",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["udp_port"] == 7777
        assert data["num_samples"] == 900
        assert data["connection_type"] == "UDP"

    def test_merges_with_existing_settings(self, client):
        # Set initial state
        app.state.settings = Settings(serial_port="/dev/ttyUSB0", num_samples=1000)
        # PUT only changes num_samples
        resp = client.put(
            "/api/settings",
            json={
                "connection_type": "SERIAL",
                "num_samples": 2000,
                "serial_port": "/dev/ttyUSB0",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["num_samples"] == 2000
        assert data["serial_port"] == "/dev/ttyUSB0"

    def test_rejects_invalid_connection_type(self, client):
        resp = client.put(
            "/api/settings",
            json={"connection_type": "BLUETOOTH"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# JSON API: GET /api/serial-ports
# ---------------------------------------------------------------------------


class TestApiSerialPorts:
    @patch("open_echo.web.SerialReader.get_serial_ports")
    def test_returns_list(self, mock_ports, client):
        mock_ports.return_value = ["/dev/ttyUSB0", "/dev/ttyACM0"]
        resp = client.get("/api/serial-ports")
        assert resp.status_code == 200
        assert resp.json() == ["/dev/ttyUSB0", "/dev/ttyACM0"]

    @patch("open_echo.web.SerialReader.get_serial_ports")
    def test_returns_empty_list_when_no_ports(self, mock_ports, client):
        mock_ports.return_value = []
        resp = client.get("/api/serial-ports")
        assert resp.status_code == 200
        assert resp.json() == []


# ---------------------------------------------------------------------------
# GET / — redirects to config when serial_port == "init"
# ---------------------------------------------------------------------------


class TestHomeRoute:
    def test_redirects_to_config_when_unconfigured(self, client):
        app.state.settings = Settings(serial_port="init")
        resp = client.get("/", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/config"


# ---------------------------------------------------------------------------
# ConnectionManager
# ---------------------------------------------------------------------------


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_and_disconnect(self):
        cm = ConnectionManager()
        ws = AsyncMock()
        await cm.connect(ws)
        assert ws in cm.active_connections
        await cm.disconnect(ws)
        assert ws not in cm.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_is_noop(self):
        cm = ConnectionManager()
        ws = AsyncMock()
        await cm.disconnect(ws)  # should not raise

    @pytest.mark.asyncio
    async def test_broadcast_json_sends_to_all(self):
        cm = ConnectionManager()
        ws1 = AsyncMock()
        ws2 = AsyncMock()
        await cm.connect(ws1)
        await cm.connect(ws2)

        data = {"depth": 1.5}
        await cm.broadcast_json(data)

        ws1.send_json.assert_awaited_once_with(data)
        ws2.send_json.assert_awaited_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast_json_removes_failed_client(self):
        cm = ConnectionManager()
        good_ws = AsyncMock()
        bad_ws = AsyncMock()
        bad_ws.send_json.side_effect = RuntimeError("broken pipe")

        await cm.connect(good_ws)
        await cm.connect(bad_ws)

        await cm.broadcast_json({"test": True})

        assert good_ws in cm.active_connections
        assert bad_ws not in cm.active_connections


# ---------------------------------------------------------------------------
# EchoReader
# ---------------------------------------------------------------------------


class TestEchoReader:
    def test_update_settings_sets_restart_event(self):
        data_cb = AsyncMock()
        depth_cb = AsyncMock()
        er = EchoReader(data_callback=data_cb, depth_callback=depth_cb)

        new_settings = Settings(num_samples=500, serial_port="test")
        er.update_settings(new_settings)

        assert er.settings == new_settings
        assert er._restart_event.is_set()

    @pytest.mark.asyncio
    async def test_process_echo_calls_callbacks(self):
        import numpy as np
        from open_echo.echo import EchoPacket

        data_cb = AsyncMock()
        depth_cb = AsyncMock()
        er = EchoReader(data_callback=data_cb, depth_callback=depth_cb)
        er.settings = Settings(medium="water")

        samples = np.array([100, 150, 200], dtype=np.uint8)
        pkt = EchoPacket(
            samples=samples, depth_index=5, temperature=22.5, drive_voltage=48.0
        )

        await er.process_echo(pkt)

        data_cb.assert_awaited_once()
        depth_cb.assert_awaited_once()

        call_data = data_cb.call_args[0][0]
        assert call_data["spectrogram"] == [100, 150, 200]
        assert call_data["temperature"] == 22.5
        assert call_data["drive_voltage"] == 48.0
        assert "measured_depth" in call_data
        assert "resolution" in call_data

    @pytest.mark.asyncio
    async def test_process_echo_handles_data_callback_error(self):
        data_cb = AsyncMock(side_effect=RuntimeError("boom"))
        depth_cb = AsyncMock()
        er = EchoReader(data_callback=data_cb, depth_callback=depth_cb)
        er.settings = Settings(medium="water")

        import numpy as np
        from open_echo.echo import EchoPacket

        pkt = EchoPacket(
            samples=np.zeros(3, dtype=np.uint8),
            depth_index=1,
            temperature=20.0,
            drive_voltage=5.0,
        )
        # Should not raise — errors are logged
        await er.process_echo(pkt)
        # depth callback should still be called
        depth_cb.assert_awaited_once()

    def test_context_manager_creates_and_cancels_task(self):
        """Test __enter__ creates task and __exit__ cancels it."""
        data_cb = AsyncMock()
        depth_cb = AsyncMock()
        er = EchoReader(data_callback=data_cb, depth_callback=depth_cb)

        mock_task = MagicMock()
        with patch("asyncio.create_task", return_value=mock_task):
            er.__enter__()
            assert er._task is mock_task

        er.__exit__(None, None, None)
        assert er._task is None
        mock_task.cancel.assert_called_once()
