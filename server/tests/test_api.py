from pathlib import Path

from fastapi.testclient import TestClient

from carrier_ac.app import app, registry


def test_health_and_demo_control(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("CARRIER_AC_HOME", str(tmp_path))
    monkeypatch.setenv("CARRIER_AC_DEMO", "1")
    registry._saved.clear()
    registry._live.clear()

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        devices = client.get("/api/devices")
        assert devices.status_code == 200
        payload = devices.json()
        assert len(payload) == 1
        device_id = payload[0]["id"]
        assert payload[0]["demo"] is True
        assert payload[0]["name"] == "Living room Carrier"

        changed = client.patch(
            f"/api/devices/{device_id}",
            json={"mode": "cool", "target_temperature": 22, "power": True},
        )
        assert changed.status_code == 200
        body = changed.json()
        assert body["mode"] == "cool"
        assert body["target_temperature"] == 22
        assert body["power"] is True

        missing = client.patch("/api/devices/nope", json={"power": False})
        assert missing.status_code == 404
