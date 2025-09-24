from abc import ABC, abstractmethod
import asyncio
from enum import Enum
from typing import Callable, Coroutine
import numpy as np
import serial.tools.list_ports
import struct
import logging
import serial_asyncio_fast as aserial


log = logging.getLogger("uvicorn")


class Reader(ABC):
    def __init__(self, settings):
        self.settings = settings

    @abstractmethod
    async def open(self):
        pass
    
    @abstractmethod
    async def close(self):
        pass

    @abstractmethod
    async def read(self):
        pass

    def unpack(self, payload: bytes, checksum: bytes) -> tuple[np.ndarray, float, float, float]:
        if len(payload) != 6 + self.settings.num_samples or len(checksum) != 1:
            raise ValueError("Invalid payload or checksum length")

        # Verify checksum
        calc_checksum = 0
        for byte in payload:
            calc_checksum ^= byte
        if calc_checksum != checksum[0]:
            log.warning("⚠️ Checksum mismatch")
            raise ValueError("Checksum mismatch")

        # Unpack payload
        depth, temp_scaled, vDrv_scaled = struct.unpack(">HhH", payload[:6])
        depth = min(depth, self.settings.num_samples)

        samples = np.frombuffer(payload[6:], dtype=np.uint8, count=self.settings.num_samples)

        temperature = temp_scaled / 100.0
        drive_voltage = vDrv_scaled / 100.0
        values = np.array(samples)

        return values, depth, temperature, drive_voltage


class SerialReader(Reader):
    def __init__(self, settings):
        super().__init__(settings)

    @staticmethod
    def get_serial_ports():
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

    async def read(self):
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

            try:
                return self.unpack(payload, checksum)
            except ValueError:
                continue  # Invalid packet, try again


class UDPReader(Reader):
    class _PacketProtocol(asyncio.DatagramProtocol):
        def __init__(self, outer):
            self.outer = outer

        def datagram_received(self, data: bytes, addr):
            for b in data:
                buf = self.outer._buf
                if not buf:
                    if b == 0xAA:
                        buf.append(b)
                    else:
                        continue
                else:
                    buf.append(b)

                if len(buf) == self.outer.packet_size:
                    # Full packet
                    payload = buf[1:1 + 6 + 2 * self.outer.settings.num_samples]
                    checksum = buf[-1:]
                    try:
                        result = self.outer.unpack(payload, checksum)
                        self.outer._queue.put_nowait(result)
                    except ValueError:
                        pass
                    finally:
                        buf.clear()

    def __init__(self, settings):
        super().__init__(settings)
        self._transport = None
        self._queue: asyncio.Queue = asyncio.Queue()
        self._buf = bytearray()
        self.packet_size = 1 + 6 + self.settings.num_samples + 1
        self.host = getattr(settings, "udp_host", "0.0.0.0")
        self.port = getattr(settings, "udp_port", 9999)

    async def open(self):
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

    async def read(self):
        # Wait for next valid parsed packet
        return await self._queue.get()


class EchoReader:
    def __init__(
        self,
        data_callback: Callable[[dict], Coroutine],
        depth_callback: Callable[[dict], Coroutine],
        settings = None,
    ):
        self.settings = settings
        self._restart_event = asyncio.Event()
        self.data_callback = data_callback
        self.depth_callback = depth_callback
        self._task: asyncio.Task | None = None

    def update_settings(self, new_settings):
        log.info("EchoReader updating settings...")
        self.settings = new_settings
        self._restart_event.set()  # Signal restart

    def __enter__(self):
        self._task = asyncio.create_task(self.run_forever())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        if self._task:
            self._task.cancel()
            self._task = None

        if exc_type is not None:
            log.error(f"Error in EchoReader: {exc_value}")

    async def aread_echo(self, reader: Reader):
        result = await reader.read()
        if result:
            values, depth_index, temperature, drive_voltage = result

            resolution = self.settings.resolution
            depth = depth_index * (resolution / 100)  # Convert to meters
            try:
                data = {
                    "spectrogram": values.tolist(),
                    "measured_depth": depth,
                    "temperature": temperature,
                    "drive_voltage": drive_voltage,
                    "resolution": resolution,
                }
                await self.data_callback(data)
            except Exception as e:
                log.error(f"❌ Error sending data: {e}", exc_info=e)

            try:
                self.depth_callback(depth)
            except Exception as e:
                log.error(f"❌ Error sending depth: {e}", exc_info=e)

        await asyncio.sleep(0.1)  # Allow time for other tasks

    async def run_forever(self):
        """Continuously read serial data and emit processed arrays. Supports live settings update and restart."""
        while True:
            if self.settings is None:
                log.warning("Settings not initialized, waiting...")
                await asyncio.sleep(1)
                continue

            self._restart_event.clear()
            try:
                reader = self.settings.connection_type.value(self.settings)
                while not self._restart_event.is_set():
                    await self.aread_echo(reader)
            except Exception as e:
                log.error(f"❌ Error in EchoReader: {e}", exc_info=e)
            finally:
                reader.close()

            await self._restart_event.wait()


class ConnectionTypeEnum(Enum):
    SERIAL = SerialReader
    UDP = UDPReader
