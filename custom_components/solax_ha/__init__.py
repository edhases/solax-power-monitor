"""SolaX HA integration setup."""

from __future__ import annotations

import importlib
import inspect
import logging
from dataclasses import dataclass
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from .const import (
    CONNECTION_TYPE_CLOUD,
    CONNECTION_TYPE_LOCAL,
    CONNECTION_TYPE_MODBUS,
    DEFAULT_SCAN_INTERVAL_CLOUD,
    DEFAULT_SCAN_INTERVAL_LOCAL,
    DEFAULT_SCAN_INTERVAL_MODBUS,
    DEFAULT_TIMEOUT,
)
from .coordinator import SolaxDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "binary_sensor", "select", "number", "switch", "button"]


@dataclass
class SolaxRuntimeData:
    """Runtime objects stored on the config entry."""

    client: Any
    coordinator: SolaxDataUpdateCoordinator


SolaxConfigEntry = ConfigEntry[SolaxRuntimeData]


def _default_scan_interval(connection_type: str) -> int:
    return {
        CONNECTION_TYPE_LOCAL: DEFAULT_SCAN_INTERVAL_LOCAL,
        CONNECTION_TYPE_CLOUD: DEFAULT_SCAN_INTERVAL_CLOUD,
        CONNECTION_TYPE_MODBUS: DEFAULT_SCAN_INTERVAL_MODBUS,
    }.get(connection_type, DEFAULT_SCAN_INTERVAL_LOCAL)


async def _create_local_client(hass: HomeAssistant, entry: ConfigEntry, timeout: int) -> Any:
    """Import and instantiate the local client, tolerating parallel development."""
    try:
        module = importlib.import_module("custom_components.solax_ha.api.local")
    except Exception as err:
        raise ConfigEntryNotReady("Local API module is not available yet") from err

    # Prefer an explicit factory if the module provides one.
    for factory_name in ("create_client", "get_client", "async_create_client", "build_client"):
        factory = getattr(module, factory_name, None)
        if callable(factory):
            try:
                result = factory(hass, entry)
                if inspect.isawaitable(result):
                    result = await result
                return result
            except TypeError:
                continue

    # Discover a client class.
    client_cls = getattr(module, "SolaxLocalClient", None)
    if client_cls is None:
        for name in ("SolaxLocalApi", "LocalClient", "SolaxClient", "SolaxApi", "SolaxLocal"):
            client_cls = getattr(module, name, None)
            if client_cls is not None:
                break
    if client_cls is None:
        for name, obj in vars(module).items():
            if isinstance(obj, type) and ("Client" in name or "Api" in name):
                client_cls = obj
                break
    if client_cls is None:
        raise ConfigEntryNotReady("No local client class found in api.local")

    data = dict(entry.data or {})
    host = data.get(CONF_HOST, data.get("host"))
    port = data.get(CONF_PORT, data.get("port", 80))
    password = data.get(CONF_PASSWORD, data.get("password", data.get("pwd")))
    username = data.get(CONF_USERNAME, data.get("username"))

    strategies = [
        lambda: client_cls(
            hass=hass,
            host=host,
            port=port,
            password=password,
            username=username,
            timeout=timeout,
        ),
        lambda: client_cls(hass, host, port, password, username=username, timeout=timeout),
        lambda: client_cls(host, port, password, username=username, timeout=timeout),
        lambda: client_cls(hass, entry),
        lambda: client_cls(entry),
    ]
    last_exc: Exception | None = None
    for strategy in strategies:
        try:
            return strategy()
        except TypeError as exc:
            last_exc = exc
            continue
    raise ConfigEntryNotReady("Could not instantiate local client") from last_exc


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up SolaX HA from a config entry."""
    data = dict(entry.data or {})
    connection_type = (
        data.get("connection_type")
        or data.get("connection_method")
        or data.get("method")
        or data.get("conn_type")
        or CONNECTION_TYPE_LOCAL
    )

    options = dict(entry.options or {})
    data = dict(entry.data or {})
    timeout = int(options.get(CONF_TIMEOUT, data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)))
    default_interval = _default_scan_interval(connection_type)
    scan_interval = int(options.get("scan_interval", data.get("scan_interval", default_interval)))
    night_mode = options.get("night_mode", data.get("night_mode", "unavailable"))

    if connection_type != CONNECTION_TYPE_LOCAL:
        raise ConfigEntryNotReady(f"Connection method {connection_type!r} is not implemented yet")

    client = await _create_local_client(hass, entry, timeout)
    coordinator = SolaxDataUpdateCoordinator(hass, client, scan_interval, night_mode)
    entry.runtime_data = SolaxRuntimeData(client=client, coordinator=coordinator)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryNotReady:
        _LOGGER.warning("Initial refresh failed; continuing optimistically")
    except Exception as err:
        _LOGGER.warning("Initial refresh failed: %s", err)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        runtime = getattr(entry, "runtime_data", None)
        client = getattr(runtime, "client", None) if runtime is not None else None
        if client is not None:
            closer = getattr(client, "async_close", None) or getattr(client, "close", None)
            if callable(closer):
                try:
                    result = closer()
                    if inspect.isawaitable(result):
                        await result
                except Exception:
                    _LOGGER.exception("Error closing SolaX client")
    return unload_ok
