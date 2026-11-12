"""Sensor platform for the SolaX HA integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import STATUS_CODES, SolaxData
from .coordinator import SolaxDataUpdateCoordinator
from .entity import SolaxEntity


@dataclass
class SolaxSensorEntityDescription(SensorEntityDescription):
    """Sensor description with a value extractor and optional entity group."""

    value_fn: Callable[[SolaxData], Any] = lambda data: None
    group: str | None = None


def _status_name(code: Any) -> str | None:
    if code is None:
        return None
    try:
        code_int = int(code)
    except (TypeError, ValueError):
        return str(code)
    return STATUS_CODES.get(code_int, f"Unknown ({code_int})")


def _group_for_key(key: str) -> str:
    if key.startswith("pv"):
        return "pv"
    if key.startswith("battery"):
        return "battery"
    if key.startswith("eps"):
        return "eps"
    if key.startswith("grid") or key.startswith("feed_in") or key.startswith("consume"):
        return "grid"
    return "inverter"


# ---------------------------------------------------------------------------
# Sensor descriptions
# ---------------------------------------------------------------------------

SENSOR_DESCRIPTIONS: list[SolaxSensorEntityDescription] = [
    # Grid
    SolaxSensorEntityDescription(
        key="grid_voltage_l1",
        name="Grid Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_voltage_l1,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_voltage_l2",
        name="Grid Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_voltage_l2,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_voltage_l3",
        name="Grid Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_voltage_l3,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_current_l1",
        name="Grid Current L1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_current_l1,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_current_l2",
        name="Grid Current L2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_current_l2,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_current_l3",
        name="Grid Current L3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_current_l3,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_power",
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_power,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_frequency_l1",
        name="Grid Frequency L1",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_frequency_l1,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_frequency_l2",
        name="Grid Frequency L2",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_frequency_l2,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="grid_frequency_l3",
        name="Grid Frequency L3",
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.grid_frequency_l3,
        group="grid",
    ),
    # PV strings
    SolaxSensorEntityDescription(
        key="pv1_voltage",
        name="PV1 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv1_voltage,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv1_current",
        name="PV1 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv1_current,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv1_power",
        name="PV1 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv1_power,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv2_voltage",
        name="PV2 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv2_voltage,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv2_current",
        name="PV2 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv2_current,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv2_power",
        name="PV2 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv2_power,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv3_voltage",
        name="PV3 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv3_voltage,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv3_current",
        name="PV3 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv3_current,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv3_power",
        name="PV3 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv3_power,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv4_voltage",
        name="PV4 Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv4_voltage,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv4_current",
        name="PV4 Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv4_current,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv4_power",
        name="PV4 Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv4_power,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv_power_total",
        name="PV Power Total",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.pv_power_total,
        group="pv",
    ),
    # Battery
    SolaxSensorEntityDescription(
        key="battery_voltage",
        name="Battery Voltage",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_voltage,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_current",
        name="Battery Current",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_current,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_power",
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_power,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_soc",
        name="Battery SoC",
        native_unit_of_measurement="%",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_soc,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_temp",
        name="Battery Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.battery_temp,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_remaining_energy",
        name="Battery Remaining Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=None,
        value_fn=lambda data: data.battery_remaining_energy,
        group="battery",
    ),
    # Feed-in / consume
    SolaxSensorEntityDescription(
        key="feed_in_power",
        name="Feed-in Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.feed_in_power,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="feed_in_energy",
        name="Feed-in Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.feed_in_energy,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="consume_power",
        name="Consumption Power",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.consume_power,
        group="grid",
    ),
    SolaxSensorEntityDescription(
        key="consume_energy",
        name="Consumption Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.consume_energy,
        group="grid",
    ),
    # Yield
    SolaxSensorEntityDescription(
        key="yield_today",
        name="Yield Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.yield_today,
        group="inverter",
    ),
    SolaxSensorEntityDescription(
        key="yield_total",
        name="Yield Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.yield_total,
        group="inverter",
    ),
    # Battery energy
    SolaxSensorEntityDescription(
        key="battery_charge_energy_today",
        name="Battery Charge Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.battery_charge_energy_today,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_charge_energy_total",
        name="Battery Charge Energy Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.battery_charge_energy_total,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_discharge_energy_today",
        name="Battery Discharge Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.battery_discharge_energy_today,
        group="battery",
    ),
    SolaxSensorEntityDescription(
        key="battery_discharge_energy_total",
        name="Battery Discharge Energy Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.battery_discharge_energy_total,
        group="battery",
    ),
    # PV energy
    SolaxSensorEntityDescription(
        key="pv_energy_today",
        name="PV Energy Today",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.pv_energy_today,
        group="pv",
    ),
    SolaxSensorEntityDescription(
        key="pv_energy_total",
        name="PV Energy Total",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.pv_energy_total,
        group="pv",
    ),
    # EPS
    SolaxSensorEntityDescription(
        key="eps_power_l1",
        name="EPS Power L1",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_power_l1,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_power_l2",
        name="EPS Power L2",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_power_l2,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_power_l3",
        name="EPS Power L3",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_power_l3,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_voltage_l1",
        name="EPS Voltage L1",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_voltage_l1,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_voltage_l2",
        name="EPS Voltage L2",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_voltage_l2,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_voltage_l3",
        name="EPS Voltage L3",
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_voltage_l3,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_current_l1",
        name="EPS Current L1",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_current_l1,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_current_l2",
        name="EPS Current L2",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_current_l2,
        group="eps",
    ),
    SolaxSensorEntityDescription(
        key="eps_current_l3",
        name="EPS Current L3",
        native_unit_of_measurement=UnitOfElectricCurrent.AMPERE,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.eps_current_l3,
        group="eps",
    ),
    # Temperatures
    SolaxSensorEntityDescription(
        key="inverter_temp",
        name="Inverter Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.inverter_temp,
        group="inverter",
    ),
    SolaxSensorEntityDescription(
        key="radiator_temp",
        name="Radiator Temperature",
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.radiator_temp,
        group="inverter",
    ),
    # Status
    SolaxSensorEntityDescription(
        key="run_mode",
        name="Run Mode",
        value_fn=lambda data: data.run_mode,
        group="inverter",
    ),
    SolaxSensorEntityDescription(
        key="inverter_status",
        name="Inverter Status",
        value_fn=lambda data: _status_name(data.inverter_status),
        group="inverter",
    ),
]


class SolaxSensor(SolaxEntity, SensorEntity):
    """A SolaX sensor entity."""

    def __init__(
        self,
        coordinator: SolaxDataUpdateCoordinator,
        description: SolaxSensorEntityDescription,
        serial: str | None = None,
    ) -> None:
        super().__init__(coordinator, key=description.key, name=description.name)
        self.entity_description = description
        sn = serial
        if not sn:
            data = coordinator.data
            sn = getattr(data, "serial_number", None) if data is not None else None
        if not sn:
            sn = "unknown"
        self._attr_unique_id = f"{sn}-{description.key}"

    @property
    def native_value(self) -> Any:
        data = self.coordinator.data
        if data is None:
            return None
        try:
            return self.entity_description.value_fn(data)
        except Exception:
            return None

    @property
    def available(self) -> bool:
        if not super().available:
            return False
        data = self.coordinator.data
        if data is None:
            return False
        try:
            value = self.entity_description.value_fn(data)
        except Exception:
            value = None
        return value is not None


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up SolaX sensor entities."""
    coordinator: SolaxDataUpdateCoordinator = entry.runtime_data.coordinator

    options = {**(entry.data or {}), **(entry.options or {})}

    def group_enabled(name: str) -> bool:
        return bool(options.get(f"entity_group_{name}", True))

    serial: str | None = None
    data = coordinator.data
    if data is not None:
        serial = getattr(data, "serial_number", None)
    if not serial:
        serial = getattr(entry, "unique_id", None)

    # When the inverter is awake we only create entities for fields that are
    # actually reported by this model. This avoids a wall of "unavailable"
    # entities for fields that do not exist on the device.
    skip_missing = data is not None and not getattr(data, "sleeping", False)

    entities: list[SolaxSensor] = []
    active_keys: set[str] = set()
    for description in SENSOR_DESCRIPTIONS:
        group = description.group or _group_for_key(description.key)
        if group is not None and not group_enabled(group):
            continue
        if skip_missing:
            try:
                if description.value_fn(data) is None:
                    continue
            except Exception:
                continue
        active_keys.add(description.key)
        entities.append(SolaxSensor(coordinator, description, serial))

    # Drop registry entries for sensors this model no longer exposes, so a
    # reload cleans up entities that were removed by the availability filter.
    if skip_missing and serial:
        from homeassistant.helpers import entity_registry as er

        registry = er.async_get(hass)
        for reg_entry in er.async_entries_for_config_entry(registry, entry.entry_id):
            if reg_entry.domain != "sensor":
                continue
            unique_id = reg_entry.unique_id or ""
            if unique_id.startswith(f"{serial}-"):
                key = unique_id[len(serial) + 1 :]
                if key not in active_keys:
                    registry.async_remove(reg_entry.entity_id)

    async_add_entities(entities)
