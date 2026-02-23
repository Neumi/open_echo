import asyncio
import logging
from collections.abc import Callable, Coroutine
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Form, Request, WebSocket
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from open_echo.depth_output import OutputManager
from open_echo.echo import EchoPacket, SerialReader
from open_echo.settings import Settings

log = logging.getLogger("uvicorn")


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket connected: {websocket.client}")

    async def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data) -> None:
        for connection in list(self.active_connections):
            try:
                await connection.send_json(data)
            except Exception as e:
                log.warning(f"WebSocket send failed, disconnecting client: {e}")
                await self.disconnect(connection)


class EchoReader:
    def __init__(
        self,
        data_callback: Callable[[dict], Coroutine[Any, Any, None]],
        depth_callback: Callable[[float], Coroutine[Any, Any, None]],
        settings=None,
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

    async def process_echo(self, echo: EchoPacket):
        resolution = self.settings.resolution
        depth = echo.depth_index * (resolution / 100)  # Convert to meters
        try:
            data = {
                "spectrogram": echo.samples.tolist(),
                "measured_depth": depth,
                "temperature": echo.temperature,
                "drive_voltage": echo.drive_voltage,
                "resolution": resolution,
            }
            await self.data_callback(data)
        except Exception as e:
            log.error(f"Error sending data: {e}", exc_info=e)

        try:
            await self.depth_callback(depth)
        except Exception as e:
            log.error(f"Error sending depth: {e}", exc_info=e)

    async def run_forever(self):
        """Continuously read serial data and emit processed arrays. Supports live settings update and restart."""
        retry_delay = 1  # seconds; doubles on each consecutive failure up to 30s max
        while True:
            if self.settings is None:
                log.warning("Settings not initialized, waiting...")
                await asyncio.sleep(1)
                continue

            log.info("EchoReader starting...")
            self._restart_event.clear()
            try:
                reader = self.settings.connection_type.value(self.settings)
                async with reader:
                    async for pkt in reader:
                        await self.process_echo(pkt)
                        if self._restart_event.is_set():
                            log.info("Restart event set, breaking loop")
                            break
                retry_delay = 1  # reset backoff on clean exit
                await self._restart_event.wait()
            except Exception as e:
                log.error(f"Error in EchoReader: {e}", exc_info=e)
                log.info(f"Retrying in {retry_delay}s...")
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)


connection_manager = ConnectionManager()
output_manager = OutputManager()
echo_reader = EchoReader(
    data_callback=connection_manager.broadcast_json,
    depth_callback=output_manager.update,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await update_settings(Settings.load())
    except Exception as e:
        log.error(f"Failed to load settings: {e}")

    with output_manager, echo_reader:
        yield


assets_dir = Path(__file__).parent.resolve() / "assets"

app = FastAPI(lifespan=lifespan)
app.state.settings = Settings()
templates = Jinja2Templates(directory=assets_dir / "templates")

app.mount("/static", StaticFiles(directory=assets_dir / "static"), name="static")


async def update_settings(new_settings: Settings):
    settings = Settings.model_validate(
        {
            **app.state.settings.model_dump(exclude_none=True, exclude_unset=True),
            **new_settings.model_dump(exclude_none=True, exclude_unset=True),
        }
    )

    echo_reader.update_settings(settings)
    await output_manager.update_settings(settings)
    app.state.settings = settings

    app.state.settings.save()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # Just here to keep the connection alive
    except Exception as e:
        log.error(f"WebSocket closed: {e}")
    finally:
        await connection_manager.disconnect(websocket)


@app.get("/")
async def home(request: Request):
    if app.state.settings.serial_port == "init":
        return RedirectResponse("/config", status_code=303)

    return templates.TemplateResponse(
        "frontend.html", {"request": request, "settings": app.state.settings}
    )


@app.get("/config")
async def config(request: Request):
    return templates.TemplateResponse(
        "config.html",
        {
            "request": request,
            "settings": app.state.settings,
            "ports": SerialReader.get_serial_ports(),
        },
    )


@app.post("/config")
async def config_post(request: Request, new_settings: Settings = Form(...)):  # noqa: B008
    await update_settings(new_settings)
    return RedirectResponse("/", status_code=303)


# --- JSON API for desktop client ---


@app.get("/api/settings")
async def api_get_settings():
    return app.state.settings.model_dump()


@app.put("/api/settings")
async def api_put_settings(new_settings: Settings):
    await update_settings(new_settings)
    return app.state.settings.model_dump()


@app.get("/api/serial-ports")
async def api_serial_ports():
    return SerialReader.get_serial_ports()


def run_web():
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    run_web()
