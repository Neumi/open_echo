import asyncio
from typing import Callable, Coroutine
import numpy as np
import serial.tools.list_ports
import struct
import logging
import serial_asyncio_fast as aserial

from settings import Settings

log = logging.getLogger("uvicorn")


class EchoReader:
    def __init__(
        self,
        data_callback: Callable[[dict], Coroutine],
        depth_callback: Callable[[dict], Coroutine],
        settings: Settings | None = None,
    ):
        self.settings = settings
        self._restart_event = asyncio.Event()
        self.data_callback = data_callback
        self.depth_callback = depth_callback
        self._task: asyncio.Task | None = None
        self.last_depth_index = 0

    def update_settings(self, new_settings: Settings):
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

    async def read_packet(self, reader: asyncio.StreamReader):
        while True:
            header = await reader.readexactly(1)
            if header != b"\xaa":
                continue  # Wait for the start byte

            payload = await reader.readexactly(
                6 + 2 * self.settings.num_samples
            )  # Read payload
            checksum = await reader.readexactly(1)

            if len(payload) != 6 + 2 * self.settings.num_samples or len(checksum) != 1:
                continue  # Incomplete packet

            # Verify checksum
            calc_checksum = 0
            for byte in payload:
                calc_checksum ^= byte
            if calc_checksum != checksum[0]:
                log.warning("⚠️ Checksum mismatch")
                continue

            # Unpack payload
            depth, temp_scaled, vDrv_scaled = struct.unpack(">HhH", payload[:6])
            depth = min(depth, self.settings.num_samples)

            samples = struct.unpack(f">{self.settings.num_samples}H", payload[6:])

            temperature = temp_scaled / 100.0
            drive_voltage = vDrv_scaled / 100.0
            values = np.array(samples)

            return values, depth, temperature, drive_voltage

    @staticmethod
    def get_serial_ports():
        """Retrieve a list of available serial ports."""
        return [port.device for port in serial.tools.list_ports.comports()][::-1]

    async def aread_echo(self, reader: asyncio.StreamReader):
        result = await self.read_packet(reader)
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
                reader, writer = await aserial.open_serial_connection(
                    url=self.settings.serial_port,
                    baudrate=self.settings.baud_rate,
                    timeout=1,
                )
                log.info("Connected to serial port: %s", str(self.settings.serial_port))
                while not self._restart_event.is_set():
                    await self.aread_echo(reader)

            except serial.SerialException as e:
                log.error(f"❌ Serial Error: {e}")

            finally:
                writer.close()
                await writer.wait_closed()

            await self._restart_event.wait()
