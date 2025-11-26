from contextlib import asynccontextmanager
from depth_output import OutputManager
from settings import Settings
from echo import EchoReader, SerialReader
import logging
from fastapi import FastAPI, WebSocket, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

log = logging.getLogger("uvicorn")


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        log.info(f"WebSocket connected: {websocket.client}")

    async def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data):
        for connection in self.active_connections:
            await connection.send_json(data)


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


app = FastAPI(lifespan=lifespan)
app.state.settings = Settings()
templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

async def update_settings(new_settings: Settings):
    settings = Settings.model_validate(
        {
            **app.state.settings.model_dump(exclude_none=True, exclude_unset=True, exclude_defaults=True),
            **new_settings.model_dump(exclude_none=True, exclude_unset=True, exclude_defaults=True),
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
async def config_post(request: Request, new_settings: Settings = Form(...)):
    await update_settings(new_settings)
    return RedirectResponse("/", status_code=303)
