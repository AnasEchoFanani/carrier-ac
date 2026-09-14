from __future__ import annotations

import os
from typing import Any

from .demo import DEMO_ID, DemoAirConditioner, demo_saved
from .midea import MideaAirConditioner, discover_devices
from .models import (
    AppStatus,
    ControlRequest,
    DeviceState,
    DiscoverResult,
    SavedDevice,
)
from .store import load_saved_devices, save_devices


def demo_enabled() -> bool:
    value = os.environ.get("CARRIER_AC_DEMO", "").strip().lower()
    return value in {"1", "true", "yes", "on"}


class DeviceRegistry:
    def __init__(self) -> None:
        self._saved: dict[str, SavedDevice] = {}
        self._live: dict[str, Any] = {}

    async def startup(self) -> None:
        for saved in load_saved_devices():
            await self._attach(saved, persist=False)
        if demo_enabled() and DEMO_ID not in self._saved:
            await self.enable_demo()

    def persist(self) -> None:
        save_devices(list(self._saved.values()))

    def status(self) -> AppStatus:
        return AppStatus(
            demo=any(device.kind == "demo" for device in self._saved.values()),
            device_count=len(self._saved),
            hint=(
                "Demo living-room unit is loaded."
                if any(device.kind == "demo" for device in self._saved.values())
                else "Scan the LAN or add a unit by IP. Carrier splits speak Midea on TCP 6444."
            ),
        )

    def list_saved(self) -> list[SavedDevice]:
        return list(self._saved.values())

    async def enable_demo(self) -> DeviceState:
        saved = demo_saved()
        live = DemoAirConditioner(saved)
        self._saved[saved.id] = saved
        self._live[saved.id] = live
        self.persist()
        return await live.refresh()

    async def discover(self, host: str | None = None) -> list[DiscoverResult]:
        return await discover_devices(host)

    async def add_midea(self, saved: SavedDevice) -> DeviceState:
        live = await MideaAirConditioner.connect(saved)
        saved = live.saved
        saved.kind = "midea"
        if not saved.id:
            saved.id = str(saved.device_id or saved.ip)
        self._saved[saved.id] = saved
        self._live[saved.id] = live
        self.persist()
        return await live.refresh()

    async def add_from_discovery(self, found: DiscoverResult, name: str | None = None) -> DeviceState:
        device_id = int(found.id) if found.id and str(found.id).isdigit() else None
        saved = SavedDevice(
            id=found.id or found.ip,
            name=name or found.name or f"Carrier {found.ip}",
            kind="midea",
            ip=found.ip,
            port=found.port,
            token=found.token,
            key=found.key,
            device_id=device_id,
            sn=found.sn,
        )
        return await self.add_midea(saved)

    async def remove(self, device_id: str) -> None:
        self._saved.pop(device_id, None)
        self._live.pop(device_id, None)
        self.persist()

    async def refresh(self, device_id: str) -> DeviceState:
        live = await self._require(device_id)
        return await live.refresh()

    async def apply(self, device_id: str, request: ControlRequest) -> DeviceState:
        live = await self._require(device_id)
        state = await live.apply(request)
        if request.name:
            self._saved[device_id].name = request.name
            self.persist()
        return state

    async def refresh_all(self) -> list[DeviceState]:
        states: list[DeviceState] = []
        for device_id in list(self._saved):
            states.append(await self.refresh(device_id))
        return states

    async def _require(self, device_id: str) -> Any:
        live = self._live.get(device_id)
        if live is not None:
            return live
        saved = self._saved.get(device_id)
        if saved is None:
            raise KeyError(device_id)
        return await self._attach(saved, persist=False)

    async def _attach(self, saved: SavedDevice, persist: bool) -> Any:
        if saved.kind == "demo":
            live: Any = DemoAirConditioner(saved)
        else:
            live = await MideaAirConditioner.connect(saved)
            saved = live.saved
        self._saved[saved.id] = saved
        self._live[saved.id] = live
        if persist:
            self.persist()
        return live
