from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import AddDeviceRequest, AppStatus, ControlRequest, DeviceState, DiscoverResult, SavedDevice
from .registry import DeviceRegistry

registry = DeviceRegistry()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await registry.startup()
    yield


app = FastAPI(
    title="Carrier AC",
    description="Local LAN control for Carrier air conditioners that speak the Midea protocol.",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/status")
async def status() -> AppStatus:
    return registry.status()


@app.get("/api/devices")
async def list_devices() -> list[DeviceState]:
    return await registry.refresh_all()


@app.post("/api/discover")
async def discover(payload: dict | None = None) -> list[DiscoverResult]:
    host = None
    if payload:
        host = payload.get("host") or payload.get("ip")
    try:
        return await registry.discover(host)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/devices")
async def add_device(request: AddDeviceRequest) -> DeviceState:
    saved = SavedDevice(
        id=str(request.device_id or request.ip),
        name=request.name or f"Carrier {request.ip}",
        kind="midea",
        ip=request.ip,
        port=request.port,
        token=request.token,
        key=request.key,
        device_id=request.device_id,
    )
    try:
        return await registry.add_midea(saved)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.post("/api/demo")
async def enable_demo() -> DeviceState:
    return await registry.enable_demo()


@app.get("/api/devices/{device_id}")
async def get_device(device_id: str) -> DeviceState:
    try:
        return await registry.refresh(device_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc


@app.patch("/api/devices/{device_id}")
async def control_device(device_id: str, request: ControlRequest) -> DeviceState:
    try:
        return await registry.apply(device_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Device not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.delete("/api/devices/{device_id}")
async def delete_device(device_id: str) -> dict[str, bool]:
    await registry.remove(device_id)
    return {"ok": True}
