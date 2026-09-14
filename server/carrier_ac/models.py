from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

DeviceKind = Literal["midea", "demo"]
ModeName = Literal["auto", "cool", "dry", "heat", "fan_only", "smart_dry"]
FanName = Literal["auto", "max", "high", "medium", "low", "silent"]
SwingName = Literal["off", "vertical", "horizontal", "both"]


class SavedDevice(BaseModel):
    id: str
    name: str
    kind: DeviceKind = "midea"
    ip: str
    port: int = 6444
    token: str | None = None
    key: str | None = None
    device_id: int | None = None
    sn: str | None = None


class DeviceState(BaseModel):
    id: str
    name: str
    kind: DeviceKind
    ip: str
    port: int
    online: bool = True
    supported: bool = True
    power: bool = False
    mode: str = "cool"
    fan_speed: str = "auto"
    swing_mode: str = "off"
    target_temperature: float = 24.0
    indoor_temperature: float | None = None
    outdoor_temperature: float | None = None
    eco: bool = False
    turbo: bool = False
    sleep: bool = False
    display_on: bool = True
    min_target_temperature: float = 16.0
    max_target_temperature: float = 30.0
    supported_modes: list[str] = Field(
        default_factory=lambda: ["auto", "cool", "dry", "heat", "fan_only"]
    )
    supported_fan_speeds: list[str] = Field(
        default_factory=lambda: ["auto", "silent", "low", "medium", "high", "max"]
    )
    supported_swing_modes: list[str] = Field(
        default_factory=lambda: ["off", "vertical", "horizontal", "both"]
    )
    supports_eco: bool = True
    supports_turbo: bool = True
    supports_sleep: bool = True
    last_error: str | None = None
    demo: bool = False


class DiscoverResult(BaseModel):
    ip: str
    port: int = 6444
    id: str | None = None
    name: str | None = None
    sn: str | None = None
    device_type: str | None = None
    online: bool | None = None
    supported: bool | None = None
    token: str | None = None
    key: str | None = None
    protocol: str | None = None


class ControlRequest(BaseModel):
    power: bool | None = None
    mode: str | None = None
    fan_speed: str | None = None
    swing_mode: str | None = None
    target_temperature: float | None = None
    eco: bool | None = None
    turbo: bool | None = None
    sleep: bool | None = None
    display_on: bool | None = None
    name: str | None = None


class AddDeviceRequest(BaseModel):
    ip: str
    name: str | None = None
    port: int = 6444
    token: str | None = None
    key: str | None = None
    device_id: int | None = None
    auto: bool = True


class AppStatus(BaseModel):
    demo: bool
    device_count: int
    hint: str


def enum_name(value: Any, fallback: str = "unknown") -> str:
    if value is None:
        return fallback
    name = getattr(value, "name", None)
    if isinstance(name, str):
        return name.lower()
    return str(value).lower()


def enum_list(values: Any) -> list[str]:
    if not values:
        return []
    names = [enum_name(item) for item in values]
    return [name for name in names if name and name != "unknown"]
