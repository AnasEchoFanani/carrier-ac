from __future__ import annotations

from copy import deepcopy

from .models import ControlRequest, DeviceState, SavedDevice

DEMO_ID = "demo-living-room"
ROOM_TEMPERATURE = 27.4
OUTDOOR_TEMPERATURE = 32.1


def demo_saved() -> SavedDevice:
    return SavedDevice(
        id=DEMO_ID,
        name="Living room Carrier",
        kind="demo",
        ip="192.168.1.42",
        port=6444,
        sn="CARRIER-DEMO-42QHG",
        device_id=42,
    )


class DemoAirConditioner:
    """In-memory Carrier split that behaves like a local Midea LAN unit."""

    def __init__(self, saved: SavedDevice | None = None) -> None:
        saved = saved or demo_saved()
        self.saved = saved
        self.state = DeviceState(
            id=saved.id,
            name=saved.name,
            kind="demo",
            ip=saved.ip,
            port=saved.port,
            online=True,
            supported=True,
            power=True,
            mode="cool",
            fan_speed="auto",
            swing_mode="vertical",
            target_temperature=24.0,
            indoor_temperature=26.8,
            outdoor_temperature=OUTDOOR_TEMPERATURE,
            eco=False,
            turbo=False,
            sleep=False,
            display_on=True,
            demo=True,
        )

    async def refresh(self) -> DeviceState:
        indoor = self.state.indoor_temperature or ROOM_TEMPERATURE
        if self.state.power:
            target = self.state.target_temperature
            if self.state.mode == "fan_only":
                target = indoor
            elif self.state.mode == "dry":
                target = min(target, indoor)
            indoor += (target - indoor) * 0.18
        else:
            indoor += (ROOM_TEMPERATURE - indoor) * 0.08
        self.state.indoor_temperature = round(indoor, 1)
        self.state.outdoor_temperature = OUTDOOR_TEMPERATURE
        self.state.online = True
        self.state.last_error = None
        return deepcopy(self.state)

    async def apply(self, request: ControlRequest) -> DeviceState:
        if request.name:
            self.state.name = request.name
            self.saved.name = request.name
        if request.power is not None:
            self.state.power = request.power
        if request.mode is not None:
            if request.mode not in self.state.supported_modes:
                raise ValueError(f"Unsupported mode: {request.mode}")
            self.state.mode = request.mode
        if request.fan_speed is not None:
            if request.fan_speed not in self.state.supported_fan_speeds:
                raise ValueError(f"Unsupported fan speed: {request.fan_speed}")
            self.state.fan_speed = request.fan_speed
        if request.swing_mode is not None:
            if request.swing_mode not in self.state.supported_swing_modes:
                raise ValueError(f"Unsupported swing mode: {request.swing_mode}")
            self.state.swing_mode = request.swing_mode
        if request.target_temperature is not None:
            low = self.state.min_target_temperature
            high = self.state.max_target_temperature
            if not low <= request.target_temperature <= high:
                raise ValueError(f"Temperature must be between {low} and {high}")
            self.state.target_temperature = round(request.target_temperature, 1)
        if request.eco is not None:
            self.state.eco = request.eco
            if request.eco:
                self.state.turbo = False
        if request.turbo is not None:
            self.state.turbo = request.turbo
            if request.turbo:
                self.state.eco = False
        if request.sleep is not None:
            self.state.sleep = request.sleep
        if request.display_on is not None:
            self.state.display_on = request.display_on
        return await self.refresh()
