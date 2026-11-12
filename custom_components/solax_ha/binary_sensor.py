"""Binary sensor platform for the SolaX HA integration."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import SolaxDataUpdateCoordinator
from .entity import SolaxEntity

BINARY_SENSOR_KEYS: list[str] = [
    "grid_connected",
    "battery_charging",
    "battery_discharging",
    "pv_producing",
    "feed_in_active",
    "consuming_from_grid",
    "inverter_fault",
    "inverter_sleeping",
]

BINARY_SENSOR_DESCRIPTIONS: dict[str, BinarySensorEntityDescription] = {
    "grid_connected": BinarySensorEntityDescription(
        key="grid_connected",
        name="Grid Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
    ),
    "battery_charging": BinarySensorEntityDescription(
        key="battery_charging",
        name="Battery Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    "battery_discharging": BinarySensorEntityDescription(
        key="battery_discharging",
        name="Battery Discharging",
        device_class=BinarySensorDeviceClass.BATTERY,
    ),
    "pv_producing": BinarySensorEntityDescription(
        key="pv_producing",
        name="PV Producing",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    "feed_in_active": BinarySensorEntityDescription(
        key="feed_in_active",
        name="Feeding In",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    "consuming_from_grid": BinarySensorEntityDescription(
        key="consuming_from_grid",
        name="Consuming From Grid",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    "inverter_fault": BinarySensorEntityDescription(
        key="inverter_fault",
        name="Inverter Fault",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
    "inverter_sleeping": BinarySensorEntityDescription(
        key="inverter_sleeping",
        name="Inverter Sleeping",
    ),
}


# Convenience aliases used by tests / external callers.
BINARY_SENSORS = [BINARY_SENSOR_DESCRIPTIONS[key] for key in BINARY_SENSOR_KEYS]


def _data_get(data: Any, attr: str) -> Any:
    """Read an attribute from coordinator data, supporting dataclass or dict."""
    if data is None:
        return None
    if hasattr(data, attr):
        return getattr(data, attr)
    if isinstance(data, dict):
        return data.get(attr)
    return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolaX binary sensors from a config entry."""
    coordinator: SolaxDataUpdateCoordinator | None = None
    runtime = getattr(entry, "runtime_data", None)
    if runtime is not None:
        coordinator = getattr(runtime, "coordinator", None)
    if coordinator is None:
        domain_data = hass.data.get(DOMAIN, {})
        # try a few common storage shapes
        candidate = domain_data.get(entry.entry_id) if isinstance(domain_data, dict) else None
        if isinstance(candidate, dict):
            coordinator = candidate.get("coordinator")
        elif hasattr(candidate, "coordinator"):
            coordinator = getattr(candidate, "coordinator", None)
    if coordinator is None:
        # last resort: scan hass.data values
        for value in domain_data.values() if isinstance(domain_data, dict) else []:
            if hasattr(value, "coordinator"):
                coordinator = getattr(value, "coordinator", None)
                if coordinator is not None:
                    break

    entities = [SolaxBinarySensor(coordinator, key) for key in BINARY_SENSOR_KEYS]
    async_add_entities(entities)


class SolaxBinarySensor(SolaxEntity, BinarySensorEntity):
    """A binary sensor for the SolaX integration."""

    def __init__(
        self,
        coordinator: SolaxDataUpdateCoordinator,
        key_or_description: Any = None,
        *,
        key: str | None = None,
        description: Any = None,
        name: str | None = None,
    ) -> None:
        if isinstance(key_or_description, BinarySensorEntityDescription):
            description = key_or_description
        elif isinstance(key_or_description, str):
            key = key_or_description
        elif key_or_description is not None and key is None and hasattr(key_or_description, "key"):
            # allow positional object with .key
            key = key_or_description.key
            description = key_or_description

        if description is not None and key is None:
            key = getattr(description, "key", None)

        if key is None:
            key = "unknown"

        if description is None:
            description = BINARY_SENSOR_DESCRIPTIONS.get(
                key, BinarySensorEntityDescription(key=key, name=key.replace("_", " ").title())
            )

        if name is None:
            name = getattr(description, "name", None)

        super().__init__(coordinator, key=key, name=name)
        self.key = key
        self._key = key
        self.entity_description = description

        # unique id
        serial = _data_get(getattr(coordinator, "data", None), "serial_number")
        if serial:
            self._attr_unique_id = f"{serial}_{key}"
        else:
            entry = getattr(coordinator, "config_entry", None)
            if entry is not None and getattr(entry, "entry_id", None):
                self._attr_unique_id = f"{entry.entry_id}_{key}"
            else:
                self._attr_unique_id = f"solax_{key}"

    @property
    def is_on(self) -> bool | None:
        """Return the binary state based on coordinator data."""
        data = getattr(self.coordinator, "data", None)
        if data is None:
            return None

        key = self._key

        if key == "grid_connected":
            code = _to_int(_data_get(data, "run_mode"))
            if code is None:
                code = _to_int(_data_get(data, "inverter_status"))
            if code is None:
                return None
            # EPS / off-grid
            return code not in (106, 107)

        if key == "battery_charging":
            power = _data_get(data, "battery_power")
            if power is None:
                return None
            try:
                return float(power) > 0
            except (TypeError, ValueError):
                return None

        if key == "battery_discharging":
            power = _data_get(data, "battery_power")
            if power is None:
                return None
            try:
                return float(power) < 0
            except (TypeError, ValueError):
                return None

        if key == "pv_producing":
            power = _data_get(data, "pv_power_total")
            if power is None:
                return None
            try:
                return float(power) > 0
            except (TypeError, ValueError):
                return None

        if key == "feed_in_active":
            power = _data_get(data, "feed_in_power")
            if power is None:
                return None
            try:
                return float(power) > 0
            except (TypeError, ValueError):
                return None

        if key == "consuming_from_grid":
            power = _data_get(data, "consume_power")
            if power is None:
                power = _data_get(data, "grid_power")
            if power is None:
                return None
            try:
                return float(power) > 0
            except (TypeError, ValueError):
                return None

        if key == "inverter_fault":
            code = _to_int(_data_get(data, "inverter_status"))
            if code is None:
                code = _to_int(_data_get(data, "run_mode"))
            if code is None:
                return None
            return code in (103, 104)

        if key == "inverter_sleeping":
            sleeping = _data_get(data, "sleeping")
            if sleeping is None:
                return None
            return bool(sleeping)

        # generic fallback: truthiness of a same-named field
        value = _data_get(data, key)
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        try:
            return bool(value)
        except Exception:
            return None
