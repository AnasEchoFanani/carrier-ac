from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys

import uvicorn

from .demo import DEMO_ID
from .models import ControlRequest, SavedDevice
from .registry import DeviceRegistry, demo_enabled


def _print(data: object) -> None:
    print(json.dumps(data, indent=2, default=str))


async def _discover(host: str | None) -> int:
    registry = DeviceRegistry()
    found = await registry.discover(host)
    if not found:
        print("No Carrier/Midea air conditioners answered on this subnet.", file=sys.stderr)
        print("The PC and indoor unit must share a LAN. Discovery uses UDP 6445.", file=sys.stderr)
        return 1
    _print([item.model_dump() for item in found])
    return 0


async def _add(ip: str, name: str | None) -> int:
    registry = DeviceRegistry()
    await registry.startup()
    state = await registry.add_midea(
        SavedDevice(id=ip, name=name or f"Carrier {ip}", kind="midea", ip=ip)
    )
    _print(state.model_dump())
    return 0


async def _demo() -> int:
    registry = DeviceRegistry()
    await registry.startup()
    state = await registry.enable_demo()
    _print(state.model_dump())
    return 0


async def _status(device_id: str | None) -> int:
    registry = DeviceRegistry()
    await registry.startup()
    if device_id:
        state = await registry.refresh(device_id)
        _print(state.model_dump())
        return 0
    states = await registry.refresh_all()
    if not states:
        print("No saved devices. Run: carrier-ac discover", file=sys.stderr)
        return 1
    _print([item.model_dump() for item in states])
    return 0


async def _set(args: argparse.Namespace) -> int:
    registry = DeviceRegistry()
    await registry.startup()
    device_id = args.id
    if not device_id:
        saved = registry.list_saved()
        if len(saved) == 1:
            device_id = saved[0].id
        elif any(item.id == DEMO_ID for item in saved):
            device_id = DEMO_ID
        else:
            print("Pass --id when more than one unit is saved.", file=sys.stderr)
            return 1
    request = ControlRequest(
        power=args.power,
        mode=args.mode,
        fan_speed=args.fan,
        swing_mode=args.swing,
        target_temperature=args.temp,
        eco=args.eco,
        turbo=args.turbo,
        sleep=args.sleep,
    )
    state = await registry.apply(device_id, request)
    _print(state.model_dump())
    return 0


def _bool_arg(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "on", "yes"}:
        return True
    if normalized in {"0", "false", "off", "no"}:
        return False
    raise argparse.ArgumentTypeError("expected on/off")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="carrier-ac",
        description="Discover and control Carrier air conditioners from Arch Linux.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    discover = sub.add_parser("discover", help="Broadcast-scan the LAN for Carrier/Midea units")
    discover.add_argument("host", nargs="?", help="Optional IP or hostname to probe")

    add = sub.add_parser("add", help="Save and authenticate a unit by IP")
    add.add_argument("ip")
    add.add_argument("--name")

    sub.add_parser("demo", help="Save a simulated living-room unit")

    status = sub.add_parser("status", help="Read saved unit state")
    status.add_argument("--id")

    control = sub.add_parser("set", help="Change power, mode, fan, or setpoint")
    control.add_argument("--id")
    control.add_argument("--power", type=_bool_arg)
    control.add_argument("--mode", choices=["auto", "cool", "dry", "heat", "fan_only"])
    control.add_argument("--fan", choices=["auto", "silent", "low", "medium", "high", "max"])
    control.add_argument("--swing", choices=["off", "vertical", "horizontal", "both"])
    control.add_argument("--temp", type=float)
    control.add_argument("--eco", type=_bool_arg)
    control.add_argument("--turbo", type=_bool_arg)
    control.add_argument("--sleep", type=_bool_arg)

    serve = sub.add_parser("serve", help="Run the local HTTP API used by the dashboard")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=43148)
    serve.add_argument("--demo", action="store_true", help="Load the simulated living-room unit")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "serve":
        if args.demo:
            os.environ["CARRIER_AC_DEMO"] = "1"
        print(f"Carrier AC API on http://{args.host}:{args.port}")
        if demo_enabled():
            print("Demo living-room unit will be loaded.")
        uvicorn.run(
            "carrier_ac.app:app",
            host=args.host,
            port=args.port,
            factory=False,
        )
        return

    commands = {
        "discover": lambda: _discover(args.host),
        "add": lambda: _add(args.ip, args.name),
        "demo": _demo,
        "status": lambda: _status(args.id),
        "set": lambda: _set(args),
    }
    try:
        code = asyncio.run(commands[args.command]())
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    raise SystemExit(code)


if __name__ == "__main__":
    main()
