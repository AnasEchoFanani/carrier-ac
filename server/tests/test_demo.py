import asyncio

from carrier_ac.demo import DemoAirConditioner
from carrier_ac.models import ControlRequest


def test_demo_cools_toward_setpoint() -> None:
    async def run() -> None:
        unit = DemoAirConditioner()
        before = await unit.refresh()
        assert before.power is True
        assert before.mode == "cool"

        after = await unit.apply(
            ControlRequest(target_temperature=20, power=True, mode="cool")
        )
        assert after.target_temperature == 20
        assert after.indoor_temperature is not None
        assert after.indoor_temperature < (before.indoor_temperature or 99)

    asyncio.run(run())


def test_demo_rejects_bad_mode() -> None:
    async def run() -> None:
        unit = DemoAirConditioner()
        try:
            await unit.apply(ControlRequest(mode="ion"))
            raise AssertionError("expected ValueError")
        except ValueError as exc:
            assert "Unsupported mode" in str(exc)

    asyncio.run(run())


def test_demo_power_off_drifts_toward_room() -> None:
    async def run() -> None:
        unit = DemoAirConditioner()
        await unit.apply(ControlRequest(power=True, target_temperature=18, mode="cool"))
        cool = await unit.refresh()
        off = await unit.apply(ControlRequest(power=False))
        assert off.power is False
        assert off.indoor_temperature is not None
        assert cool.indoor_temperature is not None
        assert off.indoor_temperature >= cool.indoor_temperature

    asyncio.run(run())
