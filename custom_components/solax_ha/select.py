"""Select platform for the SolaX HA integration."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SolaxDataUpdateCoordinator
from .entity import SolaxEntity

SCAN_INTERVAL_OPTIONS = [5, 10, 30, 60, 300]


def _coordinator_from_entry(entry: ConfigEntry) -> SolaxDataUpdateCoordinator:
    runtime = getattr(entry, "runtime_data", None)
    if runtime is not None:
        coordinator = getattr(runtime, "coordinator", None)
        if coordinator is not None:
            return coordinator
    # Fallbacks for non-standard storage.
    domain_data = (
        getattr(getattr(entry, "hass", None), "data", {}).get(DOMAIN, {})
        if hasattr(entry, "hass")
        else {}
    )
    candidate = domain_data.get(entry.entry_id) if isinstance(domain_data, dict) else None
    if isinstance(candidate, dict):
        coordinator = candidate.get("coordinator")
    elif hasattr(candidate, "coordinator"):
        coordinator = getattr(candidate, "coordinator", None)
    if coordinator is not None:
        return coordinator
    raise RuntimeError("No coordinator found on config entry")


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolaX select entities."""
    coordinator = entry.runtime_data.coordinator
    async_add_entities([SolaxSelect(coordinator, entry)])


class SolaxSelect(SolaxEntity, SelectEntity):
    """Select entity for the polling scan interval."""

    _attr_translation_key = "scan_interval"

    def __init__(
        self,
        coordinator: SolaxDataUpdateCoordinator,
        entry: ConfigEntry,
    ) -> None:
        super().__init__(coordinator, key="scan_interval")
        data = getattr(coordinator, "data", None)
        serial = getattr(data, "serial_number", None) if data is not None else None
        if not serial:
            serial = getattr(entry, "unique_id", None)
        self._attr_unique_id = f"{serial or entry.entry_id}_scan_interval"
        self._attr_options = [str(value) for value in SCAN_INTERVAL_OPTIONS]

    @property
    def current_option(self) -> str | None:
        """Return the currently selected scan interval."""
        try:
            value = str(getattr(self.coordinator, "scan_interval", None))
        except Exception:
            return None
        if value in (self.options or []):
            return value
        # Fall back to the closest configured option if needed.
        return value if value is not None else None

    async def async_select_option(self, option: str) -> None:
        """Update the coordinator scan interval without reloading."""
        try:
            seconds = int(option)
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
SolaxScanIntervalSelect = SolaxSelect
