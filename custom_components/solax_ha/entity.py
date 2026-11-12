"""Base entity for the SolaX HA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import SolaxDataUpdateCoordinator


class SolaxEntity(CoordinatorEntity[SolaxDataUpdateCoordinator]):
    """Common base class for all SolaX entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SolaxDataUpdateCoordinator,
        key: str | None = None,
        name: str | None = None,
    ) -> None:
        super().__init__(coordinator)
        self._key = key
        if name is not None:
            self._attr_name = name

    @property
    def available(self) -> bool:
        """Available when coordinator succeeded and inverter is not sleeping (configurable)."""
        if not super().available:
            return False
        data = self.coordinator.data
        if data is None:
            return False
        if getattr(data, "sleeping", False):
            mode = getattr(self.coordinator, "night_mode", "unavailable")
            if mode == "unavailable":
                return False
        return True

    @property
    def device_info(self) -> DeviceInfo:
        """Return device info, keyed by inverter serial number."""
        data = self.coordinator.data
        serial: str | None = None
        model: Any = None
        if data is not None:
            serial = getattr(data, "serial_number", None)
            model = getattr(data, "inverter_type", None)
        identifiers = {(DOMAIN, serial)} if serial else {(DOMAIN, "unknown")}
        return DeviceInfo(
            identifiers=identifiers,
            manufacturer=MANUFACTURER,
            model=str(model) if model is not None else None,
            sw_version=None,
        )
