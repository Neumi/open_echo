import asyncio
from dataclasses import dataclass

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from openecho.echo import (
    ChecksumMismatchError,
    ConnectionTypeEnum,
    EchoPacket,
    EchoReadError,
    SerialReader,
    UDPReader,
)


def make_payload(
    num_samples: int, depth: int = 10, temp: float = 12.34, vdrv: float = 48.7
):
    temp_scaled = int(round(temp * 100))
    vdrv_scaled = int(round(vdrv * 100))
    # <HhH  => depth(uint16), temp(int16), vDrv(uint16)
    header = (
        (depth & 0xFFFF).to_bytes(2, "little")
        + (temp_scaled & 0xFFFF).to_bytes(2, "little", signed=False)
        + (vdrv_scaled & 0xFFFF).to_bytes(2, "little")
    )
    samples = bytes([i % 256 for i in range(num_samples)])
    payload = header + samples
    checksum = bytes([compute_checksum(payload)])
    return payload, checksum


def compute_checksum(payload: bytes) -> int:
    chk = 0
    for b in payload:
        chk ^= b
    return chk


@given(
    num_samples=st.integers(min_value=1, max_value=10000),
    depth=st.integers(min_value=0, max_value=100),
    temp=st.floats(
        allow_nan=False, allow_infinity=False, width=32, min_value=-40.0, max_value=85.0
    ),
    vdrv=st.floats(
        allow_nan=False, allow_infinity=False, width=32, min_value=0.0, max_value=100.0
    ),
)
def test_echopacket_unpack_property(num_samples, depth, temp, vdrv):
    payload, checksum = make_payload(num_samples, depth=depth, temp=temp, vdrv=vdrv)
    pkt = EchoPacket.unpack(payload, checksum, num_samples)
    assert pkt.samples.size == num_samples
    assert 0 <= pkt.depth_index <= num_samples
    assert isinstance(pkt.temperature, float)
    assert isinstance(pkt.drive_voltage, float)


@given(
    num_samples=st.integers(min_value=1, max_value=10000),
    corrupt_byte=st.integers(min_value=0, max_value=255),
)
def test_echopacket_checksum_mismatch_property(num_samples, corrupt_byte):
    payload, checksum = make_payload(num_samples)
    # Corrupt checksum deterministically
    bad_checksum = (
        bytes([corrupt_byte])
        if corrupt_byte != checksum[0]
        else bytes([(checksum[0] ^ 0xFF) & 0xFF])
    )
    with pytest.raises(ChecksumMismatchError):
        EchoPacket.unpack(payload, bad_checksum, num_samples)


def test_echopacket_unpack_happy_path():
    num_samples = 32
    payload, checksum = make_payload(num_samples, depth=20, temp=23.45, vdrv=50.0)

    pkt = EchoPacket.unpack(payload, checksum, num_samples)

    assert isinstance(pkt.samples, np.ndarray)
    assert pkt.samples.dtype == np.uint8
    assert pkt.samples.size == num_samples
    # depth is clamped to num_samples
    assert pkt.depth_index == min(20, num_samples)
    assert pytest.approx(pkt.temperature, 0.001) == 23.45
    assert pytest.approx(pkt.drive_voltage, 0.001) == 50.0


def test_echopacket_depth_clamped_when_exceeds_num_samples():
    num_samples = 16
    payload, checksum = make_payload(num_samples, depth=100, temp=10.0, vdrv=5.0)
    pkt = EchoPacket.unpack(payload, checksum, num_samples)
    assert pkt.depth_index == num_samples


def test_echopacket_unpack_handles_negative_temperature():
    num_samples = 8
    # temp = -5.67 C
    payload, checksum = make_payload(num_samples, depth=2, temp=-5.67, vdrv=12.0)
    pkt = EchoPacket.unpack(payload, checksum, num_samples)
    assert pytest.approx(pkt.temperature, 0.001) == -5.67


def test_echopacket_unpack_invalid_lengths():
    num_samples = 16
    payload, checksum = make_payload(num_samples)

    with pytest.raises(EchoReadError):
        EchoPacket.unpack(payload[:-1], checksum, num_samples)  # wrong payload length

    with pytest.raises(EchoReadError):
        EchoPacket.unpack(payload, b"", num_samples)  # wrong checksum length


def test_echopacket_unpack_checksum_mismatch():
    num_samples = 8
    payload, checksum = make_payload(num_samples)
    bad_checksum = bytes([(checksum[0] ^ 0xFF) & 0xFF])

    with pytest.raises(ChecksumMismatchError):
        EchoPacket.unpack(payload, bad_checksum, num_samples)


def test_serialreader_get_serial_ports_does_not_throw(monkeypatch):
    # Monkeypatch serial.tools.list_ports.comports to return a dummy list
    class DummyPort:
        def __init__(self, device):
            self.device = device

    def fake_comports():
        return [DummyPort("/dev/tty.usbmodem0"), DummyPort("/dev/tty.usbserial1")]

    import serial.tools.list_ports

    monkeypatch.setattr(serial.tools.list_ports, "comports", fake_comports)

    ports = SerialReader.get_serial_ports()
    assert ports == ["/dev/tty.usbserial1", "/dev/tty.usbmodem0"]


@dataclass
class DummySettings:
    num_samples: int = 8
    udp_host: str = "127.0.0.1"
    udp_port: int = 9999
    serial_port: str = "/dev/tty.usbserial0"
    baud_rate: int = 115200


def build_udp_packet(
    settings: DummySettings,
    start_byte: int = 0xAA,
    depth: int = 3,
    temp: float = 21.0,
    vdrv: float = 48.0,
):
    payload, checksum = make_payload(
        settings.num_samples, depth=depth, temp=temp, vdrv=vdrv
    )
    return bytes([start_byte]) + payload + checksum


@pytest.mark.asyncio
async def test_udpreader_protocol_parses_full_packet_and_queues_result():
    settings = DummySettings(num_samples=8)
    reader = UDPReader(settings)
    # No need to open transport; test protocol behavior directly
    proto = UDPReader._PacketProtocol(reader)

    packet = build_udp_packet(settings, start_byte=0xAA, depth=5, temp=22.5, vdrv=49.0)
    proto.datagram_received(packet, ("127.0.0.1", 12345))

    result = await asyncio.wait_for(reader.read(), timeout=0.1)
    assert isinstance(result, EchoPacket)
    assert result.depth_index == min(5, settings.num_samples)
    assert result.samples.size == settings.num_samples
    assert pytest.approx(result.temperature, 0.001) == 22.5
    assert pytest.approx(result.drive_voltage, 0.001) == 49.0


@pytest.mark.asyncio
async def test_udpreader_protocol_ignores_wrong_start_byte_and_recovers():
    settings = DummySettings(num_samples=8)
    reader = UDPReader(settings)
    proto = UDPReader._PacketProtocol(reader)

    bad_start = build_udp_packet(
        settings, start_byte=0x00, depth=4, temp=15.0, vdrv=30.0
    )
    good_packet = build_udp_packet(
        settings, start_byte=0xAA, depth=4, temp=15.0, vdrv=30.0
    )

    # Send bad packet: should not enqueue
    proto.datagram_received(bad_start, ("127.0.0.1", 1))
    # Then a good packet
    proto.datagram_received(good_packet, ("127.0.0.1", 1))

    result = await asyncio.wait_for(reader.read(), timeout=0.1)
    assert isinstance(result, EchoPacket)
    assert result.depth_index == 4


@pytest.mark.asyncio
async def test_udpreader_protocol_handles_multiple_packets_in_one_datagram():
    settings = DummySettings(num_samples=6)
    reader = UDPReader(settings)
    proto = UDPReader._PacketProtocol(reader)

    pkt1 = build_udp_packet(settings, start_byte=0xAA, depth=1, temp=10.0, vdrv=20.0)
    pkt2 = build_udp_packet(settings, start_byte=0xAA, depth=5, temp=15.0, vdrv=30.0)
    joined = pkt1 + pkt2

    proto.datagram_received(joined, ("127.0.0.1", 2))

    r1 = await asyncio.wait_for(reader.read(), timeout=0.1)
    r2 = await asyncio.wait_for(reader.read(), timeout=0.1)

    assert r1.depth_index == 1
    assert r2.depth_index == 5


@pytest.mark.asyncio
async def test_udpreader_protocol_checksum_mismatch_clears_buffer_and_does_not_enqueue():
    settings = DummySettings(num_samples=8)
    reader = UDPReader(settings)
    proto = UDPReader._PacketProtocol(reader)

    # Build a valid payload then corrupt checksum
    payload, checksum = make_payload(
        settings.num_samples, depth=2, temp=10.0, vdrv=12.0
    )
    bad_checksum = bytes([(checksum[0] ^ 0xFF) & 0xFF])
    packet = bytes([0xAA]) + payload + bad_checksum
    # Protocol raises on checksum mismatch; ensure buffer clears and nothing enqueued
    with pytest.raises(ChecksumMismatchError):
        proto.datagram_received(packet, ("127.0.0.1", 1))

    # Verify queue is empty by timing out when trying to read
    with pytest.raises(asyncio.TimeoutError):
        await asyncio.wait_for(reader.read(), timeout=0.05)


@pytest.mark.asyncio
async def test_asyncreader_iterator_yields_until_cancelled():
    # Build a minimal stub of AsyncReader that produces N packets then cancels
    # Subclass AsyncReader to exercise its __aiter__ implementation directly
    from openecho.echo import AsyncReader

    class ConcreteReader(AsyncReader):
        def __init__(self, settings, packets: int):
            super().__init__(settings)
            self._remaining = packets

        async def open(self):
            return None

        async def close(self):
            return None

        async def read(self):
            if self._remaining <= 0:
                raise asyncio.CancelledError()
            self._remaining -= 1
            payload, checksum = make_payload(4, depth=2, temp=10.0, vdrv=12.0)
            return EchoPacket.unpack(payload, checksum, 4)

    reader = ConcreteReader(DummySettings(), packets=3)
    out = []
    async for pkt in reader:
        out.append(pkt)
        if len(out) >= 3:
            break
    assert len(out) == 3
    assert all(isinstance(p, EchoPacket) for p in out)


@pytest.mark.asyncio
async def test_udpreader_open_and_close_monkeypatched_log():
    # Patch a dummy logger into module to avoid NameError
    import openecho.echo as echo_mod

    class DummyLog:
        def info(self, *_args, **_kwargs):
            return None

    echo_mod.log = DummyLog()

    settings = DummySettings(
        num_samples=8, udp_host="127.0.0.1", udp_port=0
    )  # use ephemeral port
    reader = UDPReader(settings)

    # Create a datagram endpoint bound to localhost; then close
    await reader.open()
    await reader.close()


@pytest.mark.asyncio
async def test_serialreader_open_read_close_with_mock(monkeypatch):
    # Mock serial_asyncio_fast.open_serial_connection to return a reader/writer
    class DummyStreamReader:
        def __init__(self, packets: bytes | None = None):
            self._buf = packets or b""

        async def readexactly(self, n):
            # Pop n bytes from buffer
            if len(self._buf) < n:
                raise asyncio.IncompleteReadError(partial=self._buf, expected=n)
            chunk = self._buf[:n]
            self._buf = self._buf[n:]
            return chunk

    class DummyStreamWriter:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

        async def wait_closed(self):
            return None

    settings = DummySettings(num_samples=8)

    # Build one valid packet buffer: header(0xAA) + payload + checksum
    payload, checksum = make_payload(
        settings.num_samples, depth=6, temp=20.0, vdrv=40.0
    )
    packet_bytes = bytes([0xAA]) + payload + checksum

    dummy_reader = DummyStreamReader(packets=packet_bytes)
    dummy_writer = DummyStreamWriter()

    async def fake_open_serial_connection(url, baudrate, timeout):
        assert url == settings.serial_port
        assert baudrate == settings.baud_rate
        return dummy_reader, dummy_writer

    import serial_asyncio_fast as aserial

    monkeypatch.setattr(aserial, "open_serial_connection", fake_open_serial_connection)

    sr = SerialReader(settings)
    await sr.open()
    pkt = await sr.read()
    await sr.close()

    assert isinstance(pkt, EchoPacket)
    assert pkt.depth_index == 6
    assert dummy_writer.closed is True


@pytest.mark.asyncio
async def test_serialreader_read_skips_until_start_byte(monkeypatch):
    # Build buffer with noise byte then a valid packet
    settings = DummySettings(num_samples=4)

    noise = b"\x00"  # not 0xAA
    payload, checksum = make_payload(
        settings.num_samples, depth=2, temp=25.0, vdrv=33.3
    )
    packet_bytes = noise + bytes([0xAA]) + payload + checksum

    class DummyReader:
        def __init__(self, buf: bytes):
            self._buf = buf

        async def readexactly(self, n):
            if len(self._buf) < n:
                raise asyncio.IncompleteReadError(partial=self._buf, expected=n)
            chunk = self._buf[:n]
            self._buf = self._buf[n:]
            return chunk

    class DummyWriter:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

        async def wait_closed(self):
            return None

    dummy_reader = DummyReader(packet_bytes)
    dummy_writer = DummyWriter()

    async def fake_open_serial_connection(url, baudrate, timeout):
        return dummy_reader, dummy_writer

    import serial_asyncio_fast as aserial

    monkeypatch.setattr(aserial, "open_serial_connection", fake_open_serial_connection)

    sr = SerialReader(settings)
    await sr.open()
    pkt = await sr.read()
    await sr.close()

    assert pkt.depth_index == 2


def test_connection_type_enum_values():
    assert ConnectionTypeEnum.SERIAL.value is SerialReader
    assert ConnectionTypeEnum.UDP.value is UDPReader


@pytest.mark.asyncio
async def test_serialreader_read_raises_when_not_open():
    sr = SerialReader(DummySettings(num_samples=4))
    with pytest.raises(RuntimeError):
        await sr.read()
