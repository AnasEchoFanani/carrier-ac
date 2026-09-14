from __future__ import annotations

import logging
from typing import Any

from .models import (
    ControlRequest,
    DeviceState,
    DiscoverResult,
    SavedDevice,
    enum_list,
    enum_name,
)

_LOGGER = logging.getLogger(__name__)


def _coerce_enum(enum_cls: Any, value: str) -> Any:
    key = value.upper()
    members = getattr(enum_cls, "__members__", {})
    if key in members:
        return members[key]
    getter = getattr(enum_cls, "get_from_name", None)
    if getter:
        return getter(key)
    raise ValueError(f"Unknown {getattr(enum_cls, '__name__', 'value')}: {value}")


def _attr(device: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if hasattr(device, name):
            value = getattr(device, name)
            if value is not None:
                return value
    return default


class MideaAirConditioner:
    def __init__(self, saved: SavedDevice, device: Any) -> None:
        self.saved = saved
        self.device = device

    @classmethod
    async def connect(cls, saved: SavedDevice) -> "MideaAirConditioner":
        from msmart.device import AirConditioner as AC
        from msmart.discover import Discover

        device = None
        have_secrets = bool(saved.token and saved.key and saved.device_id)
        if not have_secrets:
            try:
                device = await Discover.discover_single(saved.ip)
            except Exception as exc:  # noqa: BLE001
                _LOGGER.warning("Auto-discover of %s failed: %s", saved.ip, exc)

        if device is None:
            device_id = saved.device_id or 0
            device = AC(ip=saved.ip, port=saved.port, device_id=int(device_id))
            if saved.token and saved.key:
                await device.authenticate(saved.token, saved.key)

        if saved.token is None:
            saved.token = _attr(device, "token")
        if saved.key is None:
            saved.key = _attr(device, "key")
        if saved.device_id is None:
            saved.device_id = _attr(device, "id")
        if saved.sn is None:
            saved.sn = _attr(device, "sn")
        if not saved.name or saved.name == saved.ip:
            saved.name = _attr(device, "name", default=saved.name)

        try:
            await device.get_capabilities()
        except Exception as exc:  # noqa: BLE001
            _LOGGER.warning("Capability query failed for %s: %s", saved.ip, exc)

        wrapper = cls(saved, device)
        await wrapper.refresh()
        return wrapper

    async def refresh(self) -> DeviceState:
        try:
            await self.device.refresh()
            self.saved.token = _attr(self.device, "token", default=self.saved.token)
            self.saved.key = _attr(self.device, "key", default=self.saved.key)
            return self._to_state(last_error=None)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.exception("Refresh failed for %s", self.saved.id)
            state = self._to_state(last_error=str(exc))
            state.online = False
            return state

    async def apply(self, request: ControlRequest) -> DeviceState:
        from msmart.device import AirConditioner as AC

        if request.name:
            self.saved.name = request.name
        if request.power is not None:
            self.device.power_state = request.power
        if request.mode is not None:
            self.device.operational_mode = _coerce_enum(AC.OperationalMode, request.mode)
        if request.fan_speed is not None:
            self.device.fan_speed = _coerce_enum(AC.FanSpeed, request.fan_speed)
        if request.swing_mode is not None:
            self.device.swing_mode = _coerce_enum(AC.SwingMode, request.swing_mode)
        if request.target_temperature is not None:
            self.device.target_temperature = request.target_temperature
        if request.eco is not None:
            self.device.eco = request.eco
        if request.turbo is not None:
            self.device.turbo = request.turbo
        if request.sleep is not None:
            self.device.sleep = request.sleep
        if request.display_on is not None:
            self.device.display_on = request.display_on
        self.device.beep = False
        await self.device.apply()
        return await self.refresh()

    def _to_state(self, last_error: str | None) -> DeviceState:
        device = self.device
        modes = enum_list(_attr(device, "supported_operation_modes", default=[]))
        fans = enum_list(_attr(device, "supported_fan_speeds", default=[]))
        swings = enum_list(_attr(device, "supported_swing_modes", default=[]))
        return DeviceState(
            id=self.saved.id,
            name=self.saved.name,
            kind="midea",
            ip=self.saved.ip,
            port=self.saved.port,
            online=bool(_attr(device, "online", default=True)),
            supported=bool(_attr(device, "supported", default=True)),
            power=bool(_attr(device, "power_state", "power", default=False)),
            mode=enum_name(_attr(device, "operational_mode"), "cool"),
            fan_speed=enum_name(_attr(device, "fan_speed"), "auto"),
            swing_mode=enum_name(_attr(device, "swing_mode"), "off"),
            target_temperature=float(
                _attr(device, "target_temperature", default=24.0) or 24.0
            ),
            indoor_temperature=_attr(device, "indoor_temperature"),
            outdoor_temperature=_attr(device, "outdoor_temperature"),
            eco=bool(_attr(device, "eco", default=False)),
            turbo=bool(_attr(device, "turbo", default=False)),
            sleep=bool(_attr(device, "sleep", default=False)),
            display_on=bool(_attr(device, "display_on", default=True)),
            min_target_temperature=float(
                _attr(device, "min_target_temperature", default=16.0)
            ),
            max_target_temperature=float(
                _attr(device, "max_target_temperature", default=30.0)
            ),
            supported_modes=modes
            or ["auto", "cool", "dry", "heat", "fan_only"],
            supported_fan_speeds=fans
            or ["auto", "silent", "low", "medium", "high", "max"],
            supported_swing_modes=swings
            or ["off", "vertical", "horizontal", "both"],
            supports_eco=bool(_attr(device, "supports_eco", default=True)),
            supports_turbo=bool(_attr(device, "supports_turbo", default=True)),
            supports_sleep=True,
            last_error=last_error,
            demo=False,
        )


async def discover_devices(host: str | None = None) -> list[DiscoverResult]:
    from msmart.discover import Discover

    if host:
        found = await Discover.discover_single(host)
        devices = [found] if found is not None else []
    else:
        devices = await Discover.discover()

    results: list[DiscoverResult] = []
    for device in devices:
        if device is None:
            continue
        device_type = _attr(device, "type")
        type_name = enum_name(device_type) if device_type is not None else None
        device_id = _attr(device, "id")
        results.append(
            DiscoverResult(
                ip=str(_attr(device, "ip")),
                port=int(_attr(device, "port", default=6444)),
                id=str(device_id) if device_id is not None else None,
                name=_attr(device, "name"),
                sn=_attr(device, "sn"),
                device_type=type_name,
                online=_attr(device, "online"),
                supported=_attr(device, "supported"),
                token=_attr(device, "token"),
                key=_attr(device, "key"),
                protocol="midea-lan",
            )
        )
    return results
