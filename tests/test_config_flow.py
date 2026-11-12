"""Tests for the SolaX config flow."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

try:
    from homeassistant.core import HomeAssistant
    from homeassistant.data_entry_flow import FlowResultType

    from custom_components.solax_ha.config_flow import SolaxConfigFlow  # noqa: F401
    from custom_components.solax_ha.const import CONNECTION_TYPE_LOCAL, DOMAIN
except Exception:
    pytest.skip("Home Assistant not available", allow_module_level=True)


async def test_user_step_returns_form(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_local_step_validation_success(hass: HomeAssistant) -> None:
    raw = SimpleNamespace(
        type_code=15,
        information=[None, None, "SERIAL1"],
        sn="SERIAL1",
        data=[],
    )

    client = MagicMock()
    client.async_validate = AsyncMock()
    client.async_get_data = AsyncMock(return_value=raw)
    client.async_close = AsyncMock()

    with patch(
        "custom_components.solax_ha.api.local.SolaxLocalClient",
        return_value=client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"method": CONNECTION_TYPE_LOCAL}
        )
        assert result["type"] == FlowResultType.FORM
        assert result["step_id"] == "local"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "1.2.3.4", "password": "secret"},
        )

    assert result["type"] == FlowResultType.CREATE_ENTRY


async def test_local_step_validation_failure(hass: HomeAssistant) -> None:
    client = MagicMock()
    client.async_validate = AsyncMock(side_effect=ValueError("nope"))
    client.async_close = AsyncMock()

    with patch(
        "custom_components.solax_ha.api.local.SolaxLocalClient",
        return_value=client,
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": "user"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"method": CONNECTION_TYPE_LOCAL}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"host": "1.2.3.4", "password": "secret"},
        )

    assert result["type"] == FlowResultType.FORM
    assert result["step_id"] == "local"
    assert result.get("errors", {}).get("base") == "cannot_connect"
