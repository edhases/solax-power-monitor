"""Constants for the SolaX HA integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

DOMAIN = "solax_ha"
# Manufacturer string. Disclaimer: this is an unofficial community integration,
# not affiliated with or endorsed by SolaX Power.
MANUFACTURER = "SolaX Power"

DEFAULT_SCAN_INTERVAL_LOCAL = 10
DEFAULT_SCAN_INTERVAL_CLOUD = 300
DEFAULT_SCAN_INTERVAL_MODBUS = 5
DEFAULT_TIMEOUT = 10

CONNECTION_TYPE_LOCAL = "local"
CONNECTION_TYPE_CLOUD = "cloud"
CONNECTION_TYPE_MODBUS = "modbus"
CONNECTION_TYPES = [
    CONNECTION_TYPE_LOCAL,
    CONNECTION_TYPE_CLOUD,
    CONNECTION_TYPE_MODBUS,
]

# Inverter status codes (inverterStatus / run mode). See docs/05-state-machine.md.
STATUS_CODES: dict[int, str] = {
    100: "Waiting",
    101: "Self-test",
    102: "Normal",
    103: "Recoverable fault",
    104: "Permanent fault",
    105: "Firmware upgrade",
    106: "EPS check",
    107: "EPS / Off-grid",
    108: "Self-test (Italian safety)",
    109: "Sleep / Idle",
    110: "Standby",
    111: "PV wake-up battery",
    112: "Generator check",
    113: "Generator mode",
    114: "Fast shutdown standby",
}
for _code in range(130, 161):
    if _code not in STATUS_CODES:
        STATUS_CODES[_code] = f"VPP/TOU/Gen mode {_code}"
# Override well-known ones for clarity.
STATUS_CODES.update(
    {
        130: "VPP mode",
        131: "TOU-Self use",
        132: "TOU-Charging",
        133: "TOU-Discharging",
        134: "TOU-Battery off",
        135: "TOU-Peak shaving",
        136: "Normal generator",
        137: "Battery expansion",
        138: "On-grid battery heating",
        139: "EPS battery heating",
        150: "Self Use",
        151: "Force Time Use",
        152: "Back Up",
        153: "Feedin Priority",
        154: "Demand",
        155: "ConstPower",
        160: "OpenADR",
    }
)
for _code in range(141, 149):
    STATUS_CODES[_code] = f"NormalMode {_code - 140}"


class SolaxConnectionError(Exception):
    """Raised when the inverter cannot be reached."""


class SolaxAuthError(Exception):
    """Raised when authentication fails."""


class SolaxRateLimitError(Exception):
    """Raised when a rate limit is hit."""


class SolaxParseError(Exception):
    """Raised when a response cannot be parsed."""


def is_night_data(data_list) -> bool:
    """Return True when all values in *data_list* are zero (night/sleep)."""
    if not data_list:
        return True
    for value in data_list:
        try:
            if float(value) != 0:
                return False
        except (TypeError, ValueError):
            return False
    return True


@dataclass
class SolaxData:
    """Normalized inverter data. All fields optional (None if unavailable)."""

    # Grid
    grid_voltage_l1: Optional[float] = None
    grid_voltage_l2: Optional[float] = None
    grid_voltage_l3: Optional[float] = None
    grid_current_l1: Optional[float] = None
    grid_current_l2: Optional[float] = None
    grid_current_l3: Optional[float] = None
    grid_power: Optional[float] = None
    grid_frequency_l1: Optional[float] = None
    grid_frequency_l2: Optional[float] = None
    grid_frequency_l3: Optional[float] = None

    # PV strings
    pv1_voltage: Optional[float] = None
    pv1_current: Optional[float] = None
    pv1_power: Optional[float] = None
    pv2_voltage: Optional[float] = None
    pv2_current: Optional[float] = None
    pv2_power: Optional[float] = None
    pv3_voltage: Optional[float] = None
    pv3_current: Optional[float] = None
    pv3_power: Optional[float] = None
    pv4_voltage: Optional[float] = None
    pv4_current: Optional[float] = None
    pv4_power: Optional[float] = None
    pv_power_total: Optional[float] = None

    # Battery
    battery_voltage: Optional[float] = None
    battery_current: Optional[float] = None
    battery_power: Optional[float] = None
    battery_soc: Optional[float] = None
    battery_temp: Optional[float] = None
    battery_remaining_energy: Optional[float] = None
    battery_status: Optional[Any] = None

    # Grid energy / power
    feed_in_power: Optional[float] = None
    feed_in_energy: Optional[float] = None
    consume_power: Optional[float] = None
    consume_energy: Optional[float] = None

    # Yield
    yield_today: Optional[float] = None
    yield_total: Optional[float] = None

    # Battery energy
    battery_charge_energy_today: Optional[float] = None
    battery_charge_energy_total: Optional[float] = None
    battery_discharge_energy_today: Optional[float] = None
    battery_discharge_energy_total: Optional[float] = None

    # PV energy
    pv_energy_today: Optional[float] = None
    pv_energy_total: Optional[float] = None

    # EPS
    eps_power_l1: Optional[float] = None
    eps_power_l2: Optional[float] = None
    eps_power_l3: Optional[float] = None
    eps_voltage_l1: Optional[float] = None
    eps_voltage_l2: Optional[float] = None
    eps_voltage_l3: Optional[float] = None
    eps_current_l1: Optional[float] = None
    eps_current_l2: Optional[float] = None
    eps_current_l3: Optional[float] = None

    # Temperatures
    inverter_temp: Optional[float] = None
    radiator_temp: Optional[float] = None

    # Status
    run_mode: Optional[Any] = None
    inverter_status: Optional[Any] = None
    inverter_type: Optional[Any] = None
    upload_time: Optional[Any] = None
    serial_number: Optional[str] = None
    sleeping: Optional[bool] = None

    # Diagnostics
    raw: Any = field(default=None)
