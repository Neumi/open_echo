import argparse
import asyncio
import random
import struct

from open_echo.echo import START_BYTE, compute_checksum


def build_packet(
    num_samples: int,
    depth_idx: int,
    temperature: float,
    drive_voltage: float,
    samples: bytes,
) -> bytes:
    """Build a valid echo packet from the given parameters."""
    temp_scaled = int(temperature * 100)
    vdrv_scaled = int(drive_voltage * 100)
    header = struct.pack("<HhH", int(depth_idx), temp_scaled, vdrv_scaled)
    if len(samples) != num_samples:
        raise ValueError("samples length must equal num_samples")
    payload = header + samples
    chk = compute_checksum(payload)
    return bytes([START_BYTE]) + payload + bytes([chk])


def _generate_packet(i: int, num_samples: int, randomize: bool) -> bytes:
    """Create a single simulated echo packet with background noise and a depth spike."""
    depth_idx = int(num_samples // 4 + (num_samples // 8) * (1 + (i % 5) / 5))
    if randomize:
        depth_idx = random.randint(0, num_samples - 1)

    # Light background noise to resemble a real echo waveform
    samples = bytearray(random.randint(0, 15) for _ in range(num_samples))
    samples[depth_idx] = random.randint(120, 255) if randomize else 220

    return build_packet(
        num_samples,
        depth_idx,
        temperature=20.0,
        drive_voltage=3.3,
        samples=bytes(samples),
    )


async def _udp_send(
    host: str, port: int, rate: float, num_samples: int, randomize: bool
):
    loop = asyncio.get_running_loop()
    transport, _ = await loop.create_datagram_endpoint(
        lambda: asyncio.DatagramProtocol(), remote_addr=(host, port)
    )

    try:
        i = 0
        while True:
            packet = _generate_packet(i, num_samples, randomize)
            transport.sendto(packet)
            await asyncio.sleep(1.0 / rate)
            i += 1
    finally:
        transport.close()


def run_simulate(args: argparse.Namespace | None = None):
    """Entry point for CLI. `args` should provide attributes: host, port, rate, num_samples, randomize"""
    host = getattr(args, "host", "127.0.0.1")
    port = int(getattr(args, "port", 9999))
    rate = float(getattr(args, "rate", 1.0))
    num_samples = int(getattr(args, "num_samples", 1800))
    randomize = bool(getattr(args, "randomize", False))

    try:
        print(
            f"Simulating UDP packets to {host}:{port} @ {rate} pkt/s (num_samples={num_samples})"
        )
        asyncio.run(_udp_send(host, port, rate, num_samples, randomize))
    except KeyboardInterrupt:
        print("Simulation stopped")
        return
