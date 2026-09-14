from __future__ import annotations

import json
import os
from pathlib import Path

from .models import SavedDevice

DEFAULT_DIR_NAME = "carrier-ac"


def config_dir() -> Path:
    override = os.environ.get("CARRIER_AC_HOME")
    if override:
        path = Path(override).expanduser()
    else:
        path = Path.home() / ".config" / DEFAULT_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    return path


def devices_path() -> Path:
    return config_dir() / "devices.json"


def load_saved_devices() -> list[SavedDevice]:
    path = devices_path()
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    items = raw.get("devices", raw if isinstance(raw, list) else [])
    return [SavedDevice.model_validate(item) for item in items]


def save_devices(devices: list[SavedDevice]) -> None:
    payload = {"devices": [device.model_dump() for device in devices]}
    devices_path().write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
