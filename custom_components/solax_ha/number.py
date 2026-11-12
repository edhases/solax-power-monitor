"""Number platform for the SolaX HA integration."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import SolaxDataUpdateCoordinator
from .entity import SolaxEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolaX number entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([SolaxNumber(coordinator, entry)])


class SolaxNumber(SolaxEntity, NumberEntity):
    """Number entity for a custom polling scan interval."""

    _attr_translation_key = "scan_interval_custom"

    def __init__(
        self,
        coordinator: SolaxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, key="scan_interval_custom", name="Custom Scan Interval")
        data = getattr(coordinator, "data", None)
        serial = getattr(data, "serial_number", None) if data is not None else None
        if not serial:
            serial = getattr(entry, "unique_id", None)
        self._attr_unique_id = f"{serial or entry.entry_id}_scan_interval_custom"
        self._attr_native_min_value = 1
        self._attr_native_max_value = 3600
        self._attr_native_step = 1
        self._attr_mode = NumberMode.BOX
        self._attr_native_unit_of_measurement = "s"

    @property
    def native_value(self) -> float | None:
        """Return the current scan interval."""
        try:
            return float(getattr(self.coordinator, "scan_interval", 0) or 0)
        except (TypeError, ValueError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update the coordinator scan interval without reloading."""
        try:
            seconds = int(value)
        except (TypeError, ValueError):
            return
        setter = getattr(self.coordinator, "set_scan_interval", None)
        if callable(setter):
            setter(seconds)
        else:
            self.coordinator.scan_interval = seconds
            if hasattr(self.coordinator, "update_interval"):
                from datetime import timedelta

                self.coordinator.update_interval = timedelta(seconds=seconds)
        self.async_write_ha_state()


# Convenience aliases.
SolaxScanIntervalNumber = SolaxNumber
SolaxCustomScanIntervalNumber = SolaxNumber
