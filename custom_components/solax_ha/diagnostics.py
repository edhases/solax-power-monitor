"""Diagnostics support for the SolaX HA integration."""

from __future__ import annotations

import logging
from dataclasses import asdict, is_dataclass
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Keys that must never appear in a diagnostics dump.
TO_REDACT = {
    "password",
    "pwd",
    "token_id",
    "token",
    "serial_number",
    "serial",
    "host",
}


def _to_dict(value: Any) -> Any:
    """Best-effort conversion of arbitrary runtime objects to plain dicts."""
    if value is None:
        return None
    if isinstance(value, dict):
        return {str(k): _to_dict(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_dict(v) for v in value]
    if is_dataclass(value) and not isinstance(value, type):
        try:
            return asdict(value)
        except Exception:
            pass
    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            result = to_dict()
            if isinstance(result, dict):
                return {str(k): _to_dict(v) for k, v in result.items()}
            return result
        except Exception:
            pass
    try:
        return {str(k): _to_dict(v) for k, v in vars(value).items()}
    except Exception:
        return value


def _client_info(client: Any) -> Any:
    """Collect non-sensitive-ish client attributes for diagnostics."""
    if client is None:
        return None
    info: dict[str, Any] = {"type": type(client).__name__}
    for attr in (
        "host",
        "port",
        "password",
        "username",
        "timeout",
        "token_id",
        "serial_number",
        "domain",
        "unit_id",
        "connection_type",
        "baudrate",
        "serial_port",
    ):
        if hasattr(client, attr):
            info[attr] = getattr(client, attr)
    # Avoid leaking the Home Assistant instance or other complex objects.
    info.pop("hass", None)
    return info


def _runtime_objects(hass: HomeAssistant, entry: ConfigEntry) -> tuple[Any, Any]:
    """Resolve (client, coordinator) from the entry, tolerating layouts."""
    runtime = getattr(entry, "runtime_data", None)
    client = getattr(runtime, "client", None) if runtime is not None else None
    coordinator = getattr(runtime, "coordinator", None) if runtime is not None else None

    if coordinator is None or client is None:
        try:
            domain_data = hass.data.get(DOMAIN, {}) if isinstance(hass.data, dict) else {}
            entry_data = domain_data.get(getattr(entry, "entry_id", None), {})
            if isinstance(entry_data, dict):
                client = client or entry_data.get("client")
                coordinator = coordinator or entry_data.get("coordinator")
        except Exception:
            pass

    return client, coordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    client, coordinator = _runtime_objects(hass, entry)

    coordinator_data = None
    if coordinator is not None:
        data = getattr(coordinator, "data", None)
        coordinator_data = _to_dict(data)

    client_info = _client_info(client)

    payload: dict[str, Any] = {
        "entry_data": dict(getattr(entry, "data", {}) or {}),
        "entry": dict(getattr(entry, "data", {}) or {}),
        "coordinator_data": coordinator_data,
        "data": coordinator_data,
        "client_info": client_info,
        "client": client_info,
    }

    # Coordinator-level metadata that is useful when debugging.
    if coordinator is not None:
        meta: dict[str, Any] = {}
        for attr in ("last_update_success", "scan_interval", "night_mode", "update_interval"):
            if hasattr(coordinator, attr):
                meta[attr] = getattr(coordinator, attr)
        if meta:
            payload["coordinator"] = meta

    return async_redact_data(payload, TO_REDACT)
