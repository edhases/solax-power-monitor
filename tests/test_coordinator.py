"""Tests for the Solax data update coordinator."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from homeassistant.config_entries import ConfigEntryAuthFailed
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.update_coordinator import UpdateFailed

    from custom_components.solax_ha.const import (
        SolaxAuthError,
        SolaxConnectionError,
        SolaxData,
    )
    from custom_components.solax_ha.coordinator import SolaxDataUpdateCoordinator
except Exception:
    pytest.skip("Home Assistant not available", allow_module_level=True)


class FakeClient:
    """Minimal client stand-in for the coordinator."""

    def __init__(self, result=None, exc=None) -> None:
        self.result = result
        self.exc = exc

    async def async_get_data(self):
        if self.exc is not None:
            raise self.exc
        return self.result


async def test_coordinator_success(hass: HomeAssistant) -> None:
    data = SolaxData()
    client = FakeClient(result=data)
    coordinator = SolaxDataUpdateCoordinator(hass, client, 10)

    result = await coordinator._async_update_data()

    assert result is data


async def test_coordinator_error_raises_update_failed(hass: HomeAssistant) -> None:
    client = FakeClient(exc=SolaxConnectionError("boom"))
    coordinator = SolaxDataUpdateCoordinator(hass, client, 10)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()


async def test_coordinator_auth_raises_config_entry_auth_failed(
    hass: HomeAssistant,
) -> None:
    client = FakeClient(exc=SolaxAuthError("auth"))
    coordinator = SolaxDataUpdateCoordinator(hass, client, 10)

    with pytest.raises(ConfigEntryAuthFailed):
        await coordinator._async_update_data()


async def test_coordinator_night_classification(hass: HomeAssistant) -> None:
    data = SolaxData(sleeping=None, raw=[0, 0, 0])
    client = FakeClient(result=data)
    coordinator = SolaxDataUpdateCoordinator(hass, client, 10)

    result = await coordinator._async_update_data()

    assert result.sleeping is True


async def test_coordinator_no_data_raises_update_failed(hass: HomeAssistant) -> None:
    client = FakeClient(result=None)
    coordinator = SolaxDataUpdateCoordinator(hass, client, 10)

    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()
