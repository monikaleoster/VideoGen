import logging
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from videogen.logging_config import configure_logging
from videogen.pipeline.routes import router as notes_extraction_router
from videogen.pipeline.ui import STEPS as pipeline_steps
from videogen.pipeline.ui import router as pipeline_ui_router

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI()
app.include_router(notes_extraction_router)
app.include_router(pipeline_ui_router)
logger.info("VideoGen app initialized")

_templates = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    steps = [{"name": step.name, "display_name": step.display_name} for step in pipeline_steps]
    return _templates.TemplateResponse(request, "index.html", {"steps": steps})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/echo")
async def ws_echo(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            text = await websocket.receive_text()
            await websocket.send_text(text)
    except WebSocketDisconnect:
        pass
