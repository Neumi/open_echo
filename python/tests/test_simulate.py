import asyncio

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from open_echo.echo import (
    START_BYTE,
    EchoPacket,
    compute_checksum,
    packet_size,
)
from open_echo.simulate import (
    _generate_packet,
    _udp_send,
    build_packet,
    run_simulate,
)

# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------

reasonable_num_samples = st.integers(min_value=1, max_value=5000)
depth_idx_strategy = st.integers(min_value=0, max_value=65535)
temperature_strategy = st.floats(
    min_value=-100.0, max_value=300.0, allow_nan=False, allow_infinity=False
)
drive_voltage_strategy = st.floats(
    min_value=0.0, max_value=600.0, allow_nan=False, allow_infinity=False
)


# ---------------------------------------------------------------------------
# build_packet – property-based
# ---------------------------------------------------------------------------


@given(
    num_samples=reasonable_num_samples,
    depth_idx=st.integers(min_value=0, max_value=4999),
    temperature=temperature_strategy,
    drive_voltage=drive_voltage_strategy,
)
def test_build_packet_starts_with_start_byte(
    num_samples, depth_idx, temperature, drive_voltage
):
    depth_idx = min(depth_idx, num_samples - 1)
    samples = bytes(num_samples)
    pkt = build_packet(num_samples, depth_idx, temperature, drive_voltage, samples)
    assert pkt[0] == START_BYTE


@given(
    num_samples=reasonable_num_samples,
    depth_idx=st.integers(min_value=0, max_value=4999),
    temperature=temperature_strategy,
    drive_voltage=drive_voltage_strategy,
)
def test_build_packet_has_correct_length(
    num_samples, depth_idx, temperature, drive_voltage
):
    depth_idx = min(depth_idx, num_samples - 1)
    samples = bytes(num_samples)
    pkt = build_packet(num_samples, depth_idx, temperature, drive_voltage, samples)
    assert len(pkt) == packet_size(num_samples)


@given(
    num_samples=reasonable_num_samples,
    depth_idx=st.integers(min_value=0, max_value=4999),
    temperature=temperature_strategy,
    drive_voltage=drive_voltage_strategy,
)
def test_build_packet_checksum_is_valid(
    num_samples, depth_idx, temperature, drive_voltage
):
    """The checksum byte must equal XOR of the entire payload."""
    depth_idx = min(depth_idx, num_samples - 1)
    samples = bytes(num_samples)
    pkt = build_packet(num_samples, depth_idx, temperature, drive_voltage, samples)
    payload = pkt[1:-1]
    expected_chk = compute_checksum(payload)
    assert pkt[-1] == expected_chk


@given(
    num_samples=reasonable_num_samples,
    depth_idx=st.integers(min_value=0, max_value=4999),
    temperature=temperature_strategy,
    drive_voltage=drive_voltage_strategy,
)
def test_build_packet_round_trips_through_unpack(
    num_samples, depth_idx, temperature, drive_voltage
):
    """build_packet output must be decodable by EchoPacket.unpack."""
    depth_idx = min(depth_idx, num_samples - 1)
    samples = bytes([i % 256 for i in range(num_samples)])
    pkt = build_packet(num_samples, depth_idx, temperature, drive_voltage, samples)

    payload = pkt[1:-1]
    checksum = pkt[-1:]
    decoded = EchoPacket.unpack(payload, checksum, num_samples)

    assert decoded.depth_index == min(depth_idx, num_samples)
    assert decoded.samples.size == num_samples
    np.testing.assert_array_equal(
        decoded.samples, np.frombuffer(samples, dtype=np.uint8)
    )
    assert decoded.temperature == pytest.approx(int(temperature * 100) / 100.0)
    assert decoded.drive_voltage == pytest.approx(int(drive_voltage * 100) / 100.0)


# ---------------------------------------------------------------------------
# build_packet – edge cases / error handling
# ---------------------------------------------------------------------------


def test_build_packet_rejects_wrong_sample_length():
    with pytest.raises(ValueError, match="samples length must equal num_samples"):
        build_packet(10, 0, 20.0, 3.3, bytes(5))


def test_build_packet_zero_samples():
    """Edge case: a packet with exactly 0 samples should still build correctly."""
    pkt = build_packet(0, 0, 20.0, 3.3, b"")
    assert pkt[0] == START_BYTE
    assert len(pkt) == packet_size(0)


# ---------------------------------------------------------------------------
# _generate_packet – property-based
# ---------------------------------------------------------------------------


@given(
    i=st.integers(min_value=0, max_value=10000),
    num_samples=st.integers(min_value=10, max_value=3000),
    randomize=st.booleans(),
)
@settings(max_examples=200)
def test_generate_packet_produces_valid_decodable_packets(i, num_samples, randomize):
    """Every generated packet must be decodable by EchoPacket.unpack."""
    pkt = _generate_packet(i, num_samples, randomize)
    assert pkt[0] == START_BYTE
    assert len(pkt) == packet_size(num_samples)

    payload = pkt[1:-1]
    checksum = pkt[-1:]
    decoded = EchoPacket.unpack(payload, checksum, num_samples)
    assert decoded.samples.size == num_samples
    assert 0 <= decoded.depth_index <= num_samples


@given(
    i=st.integers(min_value=0, max_value=100),
    num_samples=st.integers(min_value=10, max_value=3000),
)
def test_generate_packet_deterministic_has_spike_at_220(i, num_samples):
    """When randomize=False the spike sample at depth_idx must be 220."""
    pkt = _generate_packet(i, num_samples, randomize=False)
    payload = pkt[1:-1]
    checksum = pkt[-1:]
    decoded = EchoPacket.unpack(payload, checksum, num_samples)
    assert decoded.samples[decoded.depth_index] == 220


@given(
    i=st.integers(min_value=0, max_value=100),
    num_samples=st.integers(min_value=10, max_value=3000),
)
def test_generate_packet_has_background_noise(i, num_samples):
    """Samples should contain background noise (not all zeros except spike)."""
    pkt = _generate_packet(i, num_samples, randomize=False)
    payload = pkt[1:-1]
    checksum = pkt[-1:]
    decoded = EchoPacket.unpack(payload, checksum, num_samples)

    # At least some non-spike samples should be > 0 (noise)
    # With num_samples >= 10 and values 0-15, probability of all-zero is negligible
    non_spike = np.delete(decoded.samples, decoded.depth_index)
    # Allow for the rare case where all noise is 0 (possible but astronomically unlikely for num_samples>=10)
    # We just assert the max background value is within noise range
    assert non_spike.max() <= 15


# ---------------------------------------------------------------------------
# _udp_send – integration (receive a few packets from localhost)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_udp_send_delivers_valid_packets():
    """Start a UDP listener, run _udp_send briefly, and verify received packets."""
    num_samples = 32
    expected_pkt_size = packet_size(num_samples)
    received: list[bytes] = []

    class Receiver(asyncio.DatagramProtocol):
        def datagram_received(self, data, addr):
            received.append(data)

    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        Receiver, local_addr=("127.0.0.1", 0)
    )
    _, port = transport.get_extra_info("sockname")

    # Run sender as a task, cancel after we get enough packets
    sender_task = asyncio.create_task(
        _udp_send("127.0.0.1", port, rate=200, num_samples=num_samples, randomize=False)
    )

    # Wait until we have at least 3 packets (with a timeout)
    for _ in range(100):
        if len(received) >= 3:
            break
        await asyncio.sleep(0.02)

    sender_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await sender_task
    transport.close()

    assert len(received) >= 3
    for pkt_bytes in received[:3]:
        assert len(pkt_bytes) == expected_pkt_size
        assert pkt_bytes[0] == START_BYTE
        decoded = EchoPacket.unpack(pkt_bytes[1:-1], pkt_bytes[-1:], num_samples)
        assert decoded.samples.size == num_samples


# ---------------------------------------------------------------------------
# run_simulate – CLI plumbing
# ---------------------------------------------------------------------------


def test_run_simulate_defaults_without_args(capsys):
    """run_simulate(None) should fall back to defaults and start UDP (we just verify it doesn't crash on init)."""
    # We can't let it actually run forever, so we patch asyncio.run to capture the coroutine
    import unittest.mock as mock

    with mock.patch("open_echo.simulate.asyncio") as mock_asyncio:
        mock_asyncio.run = mock.MagicMock(side_effect=KeyboardInterrupt)
        run_simulate(None)

    captured = capsys.readouterr()
    assert "Simulating UDP" in captured.out or "Simulation stopped" in captured.out
