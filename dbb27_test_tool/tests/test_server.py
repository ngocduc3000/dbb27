from fastapi.testclient import TestClient

from backend.server import app

client = TestClient(app)


def test_scenarios_endpoint():
    r = client.get("/api/scenarios")
    assert r.status_code == 200
    assert "normal" in r.json()["scenarios"]


def test_ports_endpoint_returns_list():
    r = client.get("/api/ports")
    assert r.status_code == 200
    assert isinstance(r.json()["ports"], list)


def test_connect_mock_then_receive_ws_then_disconnect():
    with client.websocket_connect("/ws") as ws:
        r = client.post("/api/connect", json={"source": "mock", "scenario": "normal", "poll_ms": 10})
        assert r.status_code == 200
        msg = ws.receive_json()
        assert "decoded" in msg
        assert msg["source"] == "mock"
    client.post("/api/disconnect")
