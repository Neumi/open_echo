import asyncio
import struct
from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import numpy as np
import serial.tools.list_ports
import serial_asyncio_fast as aserial

if TYPE_CHECKING:
    from open_echo.settings import Settings


class EchoReadError(ValueError):
    pass


class ChecksumMismatchError(EchoReadError):
    pass


@dataclass
class EchoPacket:
    samples: np.ndarray
    depth_index: int
    temperature: float
    drive_voltage: float

    @classmethod
    def unpack(cls, payload: bytes, checksum: bytes, num_samples: int) -> "EchoPacket":
        if len(payload) != 6 + num_samples or len(checksum) != 1:
            raise EchoReadError("Invalid payload or checksum length")

        # Verify checksum
        calc_checksum = 0
        for byte in payload:
            calc_checksum ^= byte
        if calc_checksum != checksum[0]:
            print("⚠️ Checksum mismatch")
            raise ChecksumMismatchError("Checksum mismatch")

        # Unpack payload
        depth, temp_scaled, vDrv_scaled = struct.unpack("<HhH", payload[:6])
        depth = min(depth, num_samples)

        samples = np.frombuffer(payload[6:], dtype=np.uint8, count=num_samples)

        temperature = temp_scaled / 100.0
        drive_voltage = vDrv_scaled / 100.0
        values = np.array(samples)

        return cls(values, depth, temperature, drive_voltage)


class AsyncReader(ABC):
    def __init__(self, settings: "Settings"):
        print("AsyncReader initialized")
        self.settings = settings

    async def __aenter__(self) -> "AsyncReader":
        await self.open()
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    @abstractmethod
    async def open(self):
        pass

    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def read(self) -> EchoPacket:
        pass

    async def __aiter__(self) -> AsyncGenerator[EchoPacket, None]:
        try:
            while True:
                yield await self.read()
        except asyncio.CancelledError:
            return


class SerialReader(AsyncReader):
    def __init__(self, settings: "Settings"):
        print("SerialReader initialized")
        super().__init__(settings)
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    @staticmethod
    def get_serial_ports() -> list[str]:
        """Retrieve a list of available serial ports."""
        return [port.device for port in serial.tools.list_ports.comports()][::-1]

    async def open(self):
        self.reader, self.writer = await aserial.open_serial_connection(
            url=self.settings.serial_port,
            baudrate=self.settings.baud_rate,
            timeout=1,
        )

    async def close(self):
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def read(self) -> EchoPacket:
        if self.reader is None:
            raise RuntimeError("Serial port not opened")

        while True:
            header = await self.reader.readexactly(1)
            if header != b"\xaa":
                continue  # Wait for the start byte

            payload = await self.reader.readexactly(
                6 + self.settings.num_samples
            )  # Read payload
            checksum = await self.reader.readexactly(1)

            return EchoPacket.unpack(payload, checksum, self.settings.num_samples)


class UDPReader(AsyncReader):
    class _PacketProtocol(asyncio.DatagramProtocol):
        def __init__(self, outer):
            self.outer = outer

        def datagram_received(self, data: bytes, addr):
            for b in data:
                if not self.outer._buf:
                    if b == 0xAA:
                        self.outer._buf.append(b)
                    else:
                        continue
                else:
                    self.outer._buf.append(b)

                if len(self.outer._buf) >= self.outer.packet_size:
                    # Full packet
                    payload = self.outer._buf[
                        1 : 1 + 6 + self.outer.settings.num_samples
                    ]
                    checksum = self.outer._buf[-1:]
                    try:
                        result = EchoPacket.unpack(
                            payload, checksum, self.outer.settings.num_samples
                        )
                        self.outer._queue.put_nowait(result)
                    finally:
                        self.outer._buf.clear()

    def __init__(self, settings: "Settings"):
        super().__init__(settings)
        self._transport = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._buf = bytearray()
        self.packet_size = 1 + 6 + self.settings.num_samples + 1
        self.host = getattr(settings, "udp_host", "0.0.0.0")
        self.port = getattr(settings, "udp_port", 9999)

    async def open(self):
        print("Starting UDP listener...")
        loop = asyncio.get_running_loop()
        transport, protocol = await loop.create_datagram_endpoint(
            lambda: UDPReader._PacketProtocol(self),
            local_addr=(self.host, self.port),
        )
        self._transport = transport
        print(f"📡 UDP listener bound to {self.host}:{self.port}")

    async def close(self):
        if self._transport:
            self._transport.close()
            self._transport = None

    async def read(self) -> EchoPacket:
        # Wait for next valid parsed packet
        return await self._queue.get()


class ConnectionTypeEnum(Enum):
    SERIAL = SerialReader
    UDP = UDPReader
