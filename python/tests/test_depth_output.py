import asyncio
import json
from unittest.mock import patch

import pytest
from openecho.depth_output import (
    NMEA0183Output,
    OutputManager,
    SignalKOutput,
    output_methods,
)
from openecho.settings import NMEAOffset, Settings


class DummyWS:
    def __init__(self):
        self.sent = []
        self.closed = False

    async def send(self, data: str):
        self.sent.append(json.loads(data))

    async def close(self):
        self.closed = True


class DummyWriter:
    def __init__(self):
        self.buffer = bytearray()
        self._closing = False

    def write(self, data: bytes):
        self.buffer.extend(data)

    async def drain(self):
        return None

    def is_closing(self):
        return self._closing

    def close(self):
        self._closing = True

    async def wait_closed(self):
        return None


class DummyReader:
    async def read(self, n: int):
        return b""


@pytest.mark.asyncio
@patch("websockets.connect")
@patch("asyncio.open_connection")
@patch("openecho.depth_output.AsyncClient")
async def test_output_manager_update_settings_starts_methods(MockAsyncClient, mock_open_connection, mock_ws_connect):
    # Monkeypatch websockets.connect
    dummy_ws = DummyWS()

    mock_open_connection.return_value = (DummyReader(), DummyWriter())

    async def mock_connect(uri):
        assert uri.startswith("ws://localhost:3000/signalk/v1/stream")
        return dummy_ws

    mock_ws_connect.side_effect = mock_connect

    # Monkeypatch httpx.AsyncClient.post/get for token flow
    class DummyResponse:
        def __init__(self, json_data):
            self._json = json_data

        def json(self):
            return self._json

        def raise_for_status(self):
            return None

    class DummyClient:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, json=None):
            assert url == "http://localhost:3000/signalk/v1/access/requests"
            return DummyResponse({"href": "/signalk/v1/access/requests/abc", "state": "PENDING"})

        async def get(self, url):
            # First poll returns PENDING then COMPLETED with APPROVED
            if not hasattr(self, "_polled"):
                self._polled = True
                return DummyResponse({"state": "PENDING"})
            return DummyResponse({
                "state": "COMPLETED",
                "accessRequest": {"permission": "APPROVED", "token": "tok123"}
            })

    # Patch the imported AsyncClient used inside module, not httpx.AsyncClient
    MockAsyncClient.return_value = DummyClient()

    # Prepare settings enabling both outputs
    s = Settings(
        signalk_enable=True,
        signalk_address="localhost:3000",
        nmea_enable=True,
        nmea_address="localhost:10110",
        transducer_depth=1.0,
        draft=0.5,
    )

    om = OutputManager()
    await om.update_settings(s)

    # Two outputs created
    assert len(om._output_classes) == 2
    assert any(isinstance(o, SignalKOutput) for o in om._output_classes)
    assert any(isinstance(o, NMEA0183Output) for o in om._output_classes)

    # SignalKOutput has token set and connected
    sk = [o for o in om._output_classes if isinstance(o, SignalKOutput)][0]
    assert s.signalk_token == "tok123"
    assert sk._ws is dummy_ws


@pytest.mark.asyncio
@patch("openecho.depth_output.AsyncClient")
@patch("websockets.connect")
async def test_signalk_get_token_waits_when_ongoing(mock_ws_connect, MockAsyncClient):
    # Ensure concurrent get_token calls wait for ongoing request
    class DummyClient:
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return None
        async def post(self, url, json=None):
            return type("R", (), {"json": lambda self: {"href": "/h", "state": "PENDING"}, "raise_for_status": lambda self: None})()
        async def get(self, url):
            return type("G", (), {"json": lambda self: {"state": "COMPLETED", "accessRequest": {"permission": "APPROVED", "token": "tokX"}}})()

    MockAsyncClient.return_value = DummyClient()
    # Stub websockets to avoid real connect
    async def mock_connect(uri):
        return DummyWS()
    mock_ws_connect.side_effect = mock_connect

    s = Settings(signalk_enable=True, signalk_address="localhost:3000")
    sk = SignalKOutput(s)
    # Set ongoing flag and call get_token twice concurrently
    sk._access_request_ongoing = True
    async def unset_ongoing():
        # simulate another task completing access request soon
        await asyncio.sleep(0.01)
        sk._access_request_ongoing = False
    t = asyncio.create_task(unset_ongoing())
    tok = await sk.get_token()
    await t
    assert tok == s.signalk_token


@pytest.mark.asyncio
@patch("websockets.connect")
async def test_signalk_output_sends_delta(mock_ws_connect):
    dummy_ws = DummyWS()

    async def mock_connect(uri):
        return dummy_ws

    mock_ws_connect.side_effect = mock_connect
    # Bypass token fetch
    s = Settings(signalk_enable=True, signalk_address="localhost:3000", transducer_depth=2.0, draft=0.5, signalk_token="tok")
    sk = SignalKOutput(s)
    await sk.start()

    sk.update(3.0)  # depth below transducer
    await sk.output()

    assert len(dummy_ws.sent) == 1
    values = dummy_ws.sent[0]["updates"][0]["values"]
    paths = {v["path"] for v in values}
    assert "environment.depth.belowTransducer" in paths
    assert "environment.depth.belowSurface" in paths
    assert "environment.depth.belowKeel" in paths


@pytest.mark.asyncio
@patch("websockets.connect")
async def test_signalk_output_reconnect_on_send_error(mock_ws_connect):
    # First connection returns ws that raises on send; second connection returns working ws
    class FailingWS(DummyWS):
        async def send(self, data: str):
            raise RuntimeError("send failure")

    failing_ws = FailingWS()
    working_ws = DummyWS()
    calls = []

    async def mock_connect(uri):
        calls.append(uri)
        # Return failing first, then working
        return failing_ws if len(calls) == 1 else working_ws

    mock_ws_connect.side_effect = mock_connect
    s = Settings(signalk_enable=True, signalk_address="localhost:3000", signalk_token="tok")
    sk = SignalKOutput(s)
    await sk.start()
    sk.update(1.0)
    # First output should log error and stop the failing ws
    await sk.output()
    assert failing_ws.closed is True
    # Second output should reconnect and send
    await sk.output()
    assert len(working_ws.sent) == 1


@pytest.mark.asyncio
@patch("asyncio.open_connection")
async def test_nmea0183_output_writes_sentences(mock_open_conn):
    dummy_writer = DummyWriter()
    dummy_reader = DummyReader()

    async def mock_open_connection(host, port):
        assert host == "localhost" and port == 10110
        return dummy_reader, dummy_writer

    mock_open_conn.side_effect = mock_open_connection
    s = Settings(nmea_enable=True, nmea_address="localhost:10110", nmea_offset=NMEAOffset.ToKeel, transducer_depth=1.0, draft=2.0)
    nmea = NMEA0183Output(s)
    await nmea.start()

    nmea.update(4.2)
    await nmea.output()

    # Expect DBT and DPT sentences written
    out = dummy_writer.buffer.decode("ascii")
    assert out.count("$SDDBT,") == 1
    assert out.count("$SDDPT,") == 1


@pytest.mark.asyncio
@patch("asyncio.open_connection")
async def test_nmea0183_output_reconnects_when_writer_closing(mock_open_conn):
    dummy_writer = DummyWriter()
    dummy_writer._closing = True
    dummy_reader = DummyReader()

    # Track reconnect calls
    reconnects = {"count": 0}

    async def mock_open_connection(host, port):
        reconnects["count"] += 1
        return dummy_reader, DummyWriter()  # new open writer

    mock_open_conn.side_effect = mock_open_connection
    s = Settings(nmea_enable=True, nmea_address="localhost:10110", nmea_offset=NMEAOffset.ToTransducer)
    nmea = NMEA0183Output(s)

    # Manually set closing writer
    nmea._writer = dummy_writer
    nmea.update(2.5)

    await nmea.output()
    assert reconnects["count"] >= 1


@pytest.mark.asyncio
async def test_output_manager_context_lifecycle():
    # Avoid running an infinite loop: set settings to None so it sleeps; then exit quickly
    om = OutputManager(Settings())
    # Replace _run to a short coroutine
    async def short_run():
        await asyncio.sleep(0)

    om._run = short_run  # type: ignore[assignment]
    om.__enter__()
    assert om._task is not None
    om.__exit__(None, None, None)
    assert om._task is None


@pytest.mark.asyncio
async def test_signalk_start_missing_address_raises():
    s = Settings(signalk_enable=True, signalk_address="")
    sk = SignalKOutput(s)
    with pytest.raises(ValueError):
        await sk.start()


@pytest.mark.asyncio
async def test_nmea_start_missing_or_invalid_address_raises():
    s_missing = Settings(nmea_enable=True, nmea_address="")
    nmea_missing = NMEA0183Output(s_missing)
    with pytest.raises(ValueError):
        await nmea_missing.start()

    s_invalid = Settings(nmea_enable=True, nmea_address="localhost")
    nmea_invalid = NMEA0183Output(s_invalid)
    with pytest.raises(ValueError):
        await nmea_invalid.start()


@pytest.mark.asyncio
async def test_nmea_stop_handles_wait_closed_exception():
    class ErrWriter(DummyWriter):
        async def wait_closed(self):
            raise RuntimeError("boom")
    nmea = NMEA0183Output(Settings(nmea_enable=True, nmea_address="localhost:10110"))
    nmea._writer = ErrWriter()
    nmea._reader = DummyReader()
    # Should not raise
    await nmea.stop()


@pytest.mark.asyncio
@patch("asyncio.open_connection")
async def test_nmea_offset_to_surface_branch(mock_open_conn):
    dummy_writer = DummyWriter()
    dummy_reader = DummyReader()

    async def mock_open_connection(host, port):
        return dummy_reader, dummy_writer

    mock_open_conn.side_effect = mock_open_connection
    # ToSurface should use transducer_depth as positive offset
    s = Settings(
        nmea_enable=True,
        nmea_address="localhost:10110",
        nmea_offset=NMEAOffset.ToSurface,
        transducer_depth=1.5,
        draft=2.0,
    )
    nmea = NMEA0183Output(s)
    await nmea.start()
    nmea.update(2.0)
    await nmea.output()
    out = dummy_writer.buffer.decode("ascii")
    # DPT sentence contains depth plus offset and the offset itself
    assert "$SDDPT," in out


@pytest.mark.asyncio
async def test_output_manager_run_loop_behaviour():
    # Use a concrete OutputMethod that records outputs
    class Recorder(NMEA0183Output):
        async def start(self):
            self.started = True
        async def stop(self):
            self.stopped = True
        async def output(self):
            self.last_output = self._current_value

    s = Settings(nmea_enable=True, nmea_address="localhost:10110")
    om = OutputManager(s)

    # Inject recorder directly
    om._output_classes = [Recorder(s)]
    om.update(1.23)

    # Run a couple of iterations
    async def one_tick():
        await om.output()
    await one_tick()
    assert om._output_classes[0].last_output == 1.23


def test_output_methods_registry():
    assert output_methods["signalk"] is SignalKOutput
    assert output_methods["nmea0183"] is NMEA0183Output


@pytest.mark.asyncio
@patch("websockets.connect")
async def test_signalk_output_only_below_transducer_when_no_offsets(mock_ws_connect):
    dummy_ws = DummyWS()

    async def mock_connect(uri):
        return dummy_ws

    mock_ws_connect.side_effect = mock_connect
    s = Settings(signalk_enable=True, signalk_address="localhost:3000", signalk_token="tok")
    sk = SignalKOutput(s)
    await sk.start()
    sk.update(3.3)
    await sk.output()
    values = dummy_ws.sent[0]["updates"][0]["values"]
    paths = {v["path"] for v in values}
    assert paths == {"environment.depth.belowTransducer"}
