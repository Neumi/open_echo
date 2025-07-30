from abc import ABC, abstractmethod
import asyncio
import logging
import websockets
from typing import Any, Optional

from settings import NMEAOffset, Settings

log = logging.getLogger("uvicorn")


class OutputManager:
    def __init__(self, settings: Settings | None = None):
        self._task: asyncio.Task | None = None
        self.settings = settings

        self._output_classes: list[OutputMethod] = []

    def update(self, value: Any):
        """Update the current value."""
        for output_class in self._output_classes:
            output_class.update(value)

    async def update_settings(self, new_settings: Settings):
        self.settings = new_settings

        for output_class in self._output_classes:
            output_class.stop()

        new_output_classes = [
            output_methods[method]
            for method in new_settings.output_methods
            if method in output_methods
        ]
        self._output_classes = [cls(self.settings) for cls in new_output_classes]
        log.info(f"Output classes: {self._output_classes}")

        for output_class in self._output_classes:
            await output_class.start()

    async def output(self):
        """Override this in subclasses to define output behavior."""
        for output_class in self._output_classes:
            await output_class.output()

    async def _run(self):
        while True:
            if self.settings is None:
                await asyncio.sleep(1.0)
                continue

            await self.output()
            await asyncio.sleep(1.0)

    def __enter__(self):
        self._task = asyncio.create_task(self._run())

    def __exit__(self, exc_type, exc_value, traceback):
        if self._task:
            self._task.cancel()
            self._task = None


class OutputMethod(ABC):
    def __init__(self, settings: Settings):
        self.settings = settings
        self._current_value = None

    @abstractmethod
    def start(self):
        """Start the output method."""
        pass

    @abstractmethod
    def stop(self):
        """Stop the output method."""
        pass

    def update(self, value: Any):
        """Update the current value."""
        self._current_value = value

    @abstractmethod
    async def output(self):
        """Override this in subclasses to define output behavior."""
        pass


class SignalKOutput(OutputMethod):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self._ws = None
        self._ws_task: Optional[asyncio.Task] = None

        self.settings = settings

    async def start(self):
        # Use signalk_address from settings, which should be a full ws://host:port URI
        uri = getattr(self.settings, "signalk_address", None)
        if not uri:
            raise ValueError("SignalK websocket address not set in settings")
        self._ws = await websockets.connect(uri)

    async def stop(self):
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def output(self):
        if self._ws is None or self._ws.closed:
            try:
                await self.start()
            except Exception as e:
                print(f"SignalK connection error: {e}")
                return
        try:
            # Format as SignalK delta message for depth
            depth_m = self._current_value
            values = [{"path": "environment.depth.belowTransducer", "value": depth_m}]

            # Add water depth and depth below keel if settings are present
            transducer_depth = getattr(self.settings, "transducer_depth", None)
            draft = getattr(self.settings, "draft", None)
            try:
                transducer_depth = float(transducer_depth)
            except (TypeError, ValueError):
                transducer_depth = None
            try:
                draft = float(draft)
            except (TypeError, ValueError):
                draft = None

            # SignalK paths:
            # - environment.depth.belowTransducer
            # - environment.depth.belowSurface (actual water depth)
            # - environment.depth.belowKeel (depth under keel)
            if transducer_depth > 0.0:
                values.append(
                    {
                        "path": "environment.depth.belowSurface",
                        "value": depth_m + transducer_depth,
                    }
                )
                if draft > 0.0:
                    values.append(
                        {
                            "path": "environment.depth.belowKeel",
                            "value": depth_m + transducer_depth - draft,
                        }
                    )

            delta = {"updates": [{"values": values}]}
            import json

            await self._ws.send(json.dumps(delta))
        except Exception as e:
            print(f"SignalK send error: {e}")
            # Attempt reconnect next time
            if self._ws:
                await self.stop()


class NMEA0183Output(OutputMethod):
    def __init__(self, settings: Settings):
        super().__init__(settings)
        self._writer = None
        self._reader = None
        self.settings = settings

    async def start(self):
        address = getattr(self.settings, "nmea0183_address", None)
        if not address:
            raise ValueError("NMEA0183 TCP address not set in settings")
        # address should be in the form 'host:port'
        if ":" not in address:
            raise ValueError("NMEA0183 address must be in 'host:port' format")
        host, port = address.split(":", 1)
        self._reader, self._writer = await asyncio.open_connection(host, int(port))

    async def stop(self):
        if self._writer:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
            self._reader = None

    async def output(self):
        if self._writer is None or self._writer.is_closing():
            try:
                await self.start()
            except Exception as e:
                print(f"NMEA0183 TCP connection error: {e}")
                return
        try:
            # Send DBT and DPT sentences, ending with CRLF (NMEA standard)
            depth_m = self._current_value
            depth_ft = depth_m * 3.28084
            depth_fathoms = depth_m * 0.546807

            def calculate_checksum(sentence):
                checksum = 0
                for char in sentence:
                    checksum ^= ord(char)
                return f"*{checksum:02X}"

            # DBT: Depth Below Transducer
            dbt_sentence = f"DBT,{depth_ft:.1f},f,{depth_m:.1f},M,{depth_fathoms:.1f},F"
            dbt_full = f"${dbt_sentence}{calculate_checksum(dbt_sentence)}\r\n"

            self._writer.write(dbt_full.encode())

            nmea_offset = 0.0
            if self.settings.nmea_offset is not NMEAOffset.ToTransducer:
                to_keel = self.settings.draft - self.settings.transducer_depth
                to_surface = self.settings.transducer_depth

                nmea_offset = (
                    -to_keel
                    if self.settings.nmea_offset is NMEAOffset.ToKeel
                    else to_surface
                )

            # DPT: Depth + offset (below surface)
            dpt_depth = depth_m + nmea_offset
            dpt_sentence = f"DPT,{dpt_depth:.1f},{nmea_offset:.1f}"
            dpt_full = f"${dpt_sentence}{calculate_checksum(dpt_sentence)}\r\n"

            self._writer.write(dpt_full.encode())

            await self._writer.drain()
        except Exception as e:
            print(f"NMEA0183 TCP send error: {e}")
            # Attempt reconnect next time
            await self.stop()


output_methods = {
    "signalk": SignalKOutput,
    "nmea0183": NMEA0183Output,
}
