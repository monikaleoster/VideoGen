from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()


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
