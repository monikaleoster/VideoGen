from fastapi.testclient import TestClient

from videogen.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ws_echo() -> None:
    with client.websocket_connect("/ws/echo") as websocket:
        websocket.send_text("hello")
        assert websocket.receive_text() == "hello"

        websocket.send_text("world")
        assert websocket.receive_text() == "world"
