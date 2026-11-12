"""Button platform for the SolaX HA integration."""

from __future__ import annotations

import contextlib
import inspect

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SolaxDataUpdateCoordinator
from .entity import SolaxEntity

BUTTON_KEYS: list[str] = [
    "refresh",
    "reconnect",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolaX button entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([SolaxButton(coordinator, entry, key) for key in BUTTON_KEYS])


class SolaxButton(SolaxEntity, ButtonEntity):
    """Button entity for refresh / reconnect actions."""

    def __init__(
        self,
        coordinator: SolaxDataUpdateCoordinator,
        entry: ConfigEntry,
        key: str,
    ) -> None:
        super().__init__(coordinator, key=key)
        self._key = key
        data = getattr(coordinator, "data", None)
        serial = getattr(data, "serial_number", None) if data is not None else None
        if not serial:
            serial = getattr(entry, "unique_id", None)
        self._attr_unique_id = f"{serial or entry.entry_id}_{key}"
        self._attr_translation_key = key

    async def async_press(self) -> None:
        """Handle a button press."""
        coordinator = self.coordinator
        if self._key == "refresh":
            requester = getattr(coordinator, "async_request_refresh", None)
            if callable(requester):
                await requester()
            return

        if self._key == "reconnect":
            client = getattr(coordinator, "client", None)
            reconnected = False
            if client is not None:
                for method_name in (
                    "async_reconnect",
                    "reconnect",
                    "async_connect",
                    "connect",
                ):
                    method = getattr(client, method_name, None)
                    if callable(method):
                        try:
                            result = method()
                            if inspect.isawaitable(result):
                                await result
                            reconnected = True
                            break
                        except Exception:
                            continue
                if not reconnected:
                    validator = getattr(client, "async_validate", None)
                    if callable(validator):
                        try:
                            result = validator()
                            if inspect.isawaitable(result):
                                await result
                        except Exception:
                            pass
            requester = getattr(coordinator, "async_request_refresh", None)
            if callable(requester):
                with contextlib.suppress(Exception):
                    await requester()


class SolaxRefreshButton(SolaxButton):
    """Convenience subclass for the refresh button."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "refresh")


class SolaxReconnectButton(SolaxButton):
    """Convenience subclass for the reconnect button."""

    def __init__(self, coordinator, entry):
        super().__init__(coordinator, entry, "reconnect")
