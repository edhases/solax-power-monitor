"""Switch platform for the SolaX HA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SolaxDataUpdateCoordinator
from .entity import SolaxEntity

SWITCH_GROUPS: list[str] = [
    "entity_group_pv",
    "entity_group_battery",
    "entity_group_grid",
    "entity_group_inverter",
    "entity_group_eps",
    "entity_group_energy",
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolaX switch entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([SolaxSwitch(coordinator, entry, key) for key in SWITCH_GROUPS])


class SolaxSwitch(SolaxEntity, SwitchEntity):
    """In-memory toggle for an entity group (informational, no persistence)."""

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
        self._is_on = True

    @property
    def available(self) -> bool:
        """Switches are always available."""
        return True

    @property
    def is_on(self) -> bool:
        """Return the in-memory toggle state."""
        return bool(self._is_on)

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the toggle on."""
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the toggle off."""
        self._is_on = False
        self.async_write_ha_state()


# Convenience aliases.
SolaxEntityGroupSwitch = SolaxSwitch
SolaxGroupSwitch = SolaxSwitch
