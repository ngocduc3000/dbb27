import asyncio
import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse
from serial.tools import list_ports

from backend import logger as logger_mod
from backend import mock, poller, transport

app = FastAPI(title="DBB-27 Serial Test Tool")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
INDEX_HTML = os.path.join(BASE_DIR, "frontend", "index.html")

# Each connected client gets its own queue; the poller pushes records into all
# queues (it runs in the same event loop, so put_nowait is safe), and each ws
# coroutine drains its queue and sends. This decouples producing from sending.
_clients: dict[WebSocket, "asyncio.Queue[dict]"] = {}
_poller: poller.Poller | None = None
_task: asyncio.Task | None = None


def _broadcast(record: dict) -> None:
    for q in list(_clients.values()):
        try:
            q.put_nowait(record)
        except Exception:
            pass


@app.get("/api/scenarios")
def scenarios():
    return {"scenarios": mock.SCENARIOS}


@app.get("/api/ports")
def ports():
    return {"ports": [p.device for p in list_ports.comports()]}


@app.post("/api/connect")
async def connect(cfg: dict):
    global _poller, _task
    await disconnect()
    source = cfg.get("source", "mock")
    if source == "serial":
        t = transport.SerialTransport(cfg["port"], int(cfg.get("baud", 9600)))
    else:
        t = transport.MockTransport(
            cfg.get("scenario", "normal"),
            float(cfg.get("fault_rate", 0.0)),
            alarms=cfg.get("alarms", []),
        )
    lg = logger_mod.FrameLogger(LOG_DIR)
    _poller = poller.Poller(
        t, lg, source=source, on_result=_broadcast,
        poll_ms=int(cfg.get("poll_ms", 1000)),
    )
    _task = asyncio.create_task(_poller.run())
    return {"status": "connected", "source": source}


@app.post("/api/disconnect")
async def disconnect():
    global _poller, _task
    if _poller is not None:
        _poller.stop()
    task, _poller, _task = _task, None, None
    if task is not None:
        try:
            await asyncio.wait_for(task, timeout=3.0)
        except BaseException:  # noqa: BLE001 - cleanup must not propagate (incl. CancelledError)
            pass
    return {"status": "disconnected"}


@app.get("/api/log/download")
def download_log():
    lg = logger_mod.FrameLogger(LOG_DIR)
    path = lg.current_path()
    if not os.path.exists(path):
        return HTMLResponse("No log yet", status_code=404)
    return FileResponse(path, filename=os.path.basename(path))


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await ws.accept()
    queue: asyncio.Queue[dict] = asyncio.Queue()
    _clients[ws] = queue

    async def sender():
        while True:
            record = await queue.get()
            await ws.send_json(record)

    send_task = asyncio.create_task(sender())
    try:
        # Read loop exists only to detect the client closing the connection.
        while True:
            await ws.receive_text()
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        send_task.cancel()
        _clients.pop(ws, None)


@app.get("/")
def index():
    if os.path.exists(INDEX_HTML):
        return FileResponse(INDEX_HTML)
    return HTMLResponse("<h1>frontend/index.html chưa tồn tại</h1>")
