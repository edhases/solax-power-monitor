"""Data decoders for SolaX inverter families.

All index logic for the positional ``Data`` array returned by the local API
lives here. Platforms consume the normalized :class:`SolaxData` dataclass and
never touch indices directly.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from .const import SolaxData

_LOGGER = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Raw input
# ---------------------------------------------------------------------------


@dataclass
class RawInverterData:
    """Raw payload returned by a SolaX inverter."""

    sn: Any = ""
    ver: Any = ""
    type_code: int = 0
    data: list[Any] = field(default_factory=list)
    information: list[Any] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def safe_get(container: Any, idx: int, default: Any = None) -> Any:
    """Safely read index ``idx`` from a list-like container."""
    if container is None:
        return default
    try:
        if idx < 0:
            return default
        if len(container) <= idx:
            return default
        value = container[idx]
        if value is None:
            return default
        return value
    except (TypeError, IndexError, KeyError):
        return default


def read_signed16(value: Any) -> int | None:
    """Decode a signed 16-bit two's-complement value."""
    if value is None:
        return None
    try:
        n = int(float(value))
    except (TypeError, ValueError):
        return None
    if n >= 32768:
        n -= 65536
    return n


def read_unsigned32(a: Any, b: Any) -> int | None:
    """Combine two 16-bit words into an unsigned 32-bit value (a + 65536*b)."""
    if a is None or b is None:
        return None
    try:
        return int(float(a)) + 65536 * int(float(b))
    except (TypeError, ValueError):
        return None


def read_signed32(a: Any, b: Any) -> int | None:
    """Combine two 16-bit words into a signed 32-bit value."""
    if a is None or b is None:
        return None
    try:
        val = int(float(a)) + 65536 * int(float(b))
        hi = int(float(b))
    except (TypeError, ValueError):
        return None
    if hi >= 32768:
        val -= 4294967296
    return val


def is_night_data(data_list: Any) -> bool:
    """Return True when all values in *data_list* are zero (or empty)."""
    if not data_list:
        return True
    for value in data_list:
        try:
            if float(value) != 0:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _div(value: Any, denom: float) -> float | None:
    if value is None:
        return None
    try:
        return float(value) / denom
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def _int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _sum(*values: Any) -> float | None:
    nums = [v for v in values if v is not None]
    if not nums:
        return None
    try:
        return float(sum(nums))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Model names
# ---------------------------------------------------------------------------


MODEL_NAMES: dict[int, str] = {
    1: "X1-LX",
    2: "X-Hybrid",
    3: "X1-Hybrid/Fit",
    4: "X1-Boost/Air/Mini",
    5: "X3-Hybrid/Fit",
    6: "X3-20K/30K",
    7: "X3-MIC/PRO",
    8: "X1-Smart",
    9: "X1-AC",
    10: "A1-Hybrid",
    11: "A1-Fit",
    12: "A1-Grid",
    13: "J1-ESS",
    14: "X3-Hybrid-G4",
    15: "X1-Hybrid-G4",
    16: "X3-MIC/PRO-G2",
    17: "X1-SPT",
    18: "X1-Boost/Mini-G4",
    19: "A1-HYB-G2",
    20: "A1-AC-G2",
    21: "A1-SMT-G2",
    22: "X3-FTH",
    23: "X3-MGA-G2",
    24: "X3-Hybrid-G5",
    100: "X3-Big (String)",
    101: "X3-Big (String)",
    102: "X1-Hybrid-LV",
}


def model_name_for_type(type_code: int) -> str:
    """Return a human readable model name for a SolaX type code."""
    try:
        tc = int(type_code)
    except (TypeError, ValueError):
        return "Unknown"
    return MODEL_NAMES.get(tc, f"Unknown (type {tc})")


# ---------------------------------------------------------------------------
# Decoders
# ---------------------------------------------------------------------------


def _normalize_raw(raw: Any) -> RawInverterData:
    if isinstance(raw, RawInverterData):
        return raw
    if isinstance(raw, dict):
        type_code = raw.get("type", raw.get("type_code", raw.get("inverterType", 0)))
        try:
            type_code = int(type_code)
        except (TypeError, ValueError):
            type_code = 0
        return RawInverterData(
            sn=raw.get("sn", raw.get("serial", raw.get("inverterSN", ""))),
            ver=raw.get("ver", raw.get("version", "")),
            type_code=type_code,
            data=list(raw.get("Data", raw.get("data", [])) or []),
            information=list(raw.get("Information", raw.get("information", [])) or []),
        )
    # duck-typed
    data = getattr(raw, "data", None)
    if data is None:
        data = getattr(raw, "Data", [])
    info = getattr(raw, "information", None)
    if info is None:
        info = getattr(raw, "Information", [])
    tc = getattr(raw, "type_code", None)
    if tc is None:
        tc = getattr(raw, "type", 0)
    try:
        tc = int(tc)
    except (TypeError, ValueError):
        tc = 0
    return RawInverterData(
        sn=getattr(raw, "sn", getattr(raw, "serial", "")),
        ver=getattr(raw, "ver", getattr(raw, "version", "")),
        type_code=tc,
        data=list(data or []),
        information=list(info or []),
    )


def _common_setup(solax: SolaxData, raw: RawInverterData, data: list[Any]) -> None:
    solax.serial_number = None
    info = raw.information or []
    if len(info) >= 3 and info[2] not in (None, ""):
        solax.serial_number = str(info[2])
    elif raw.sn not in (None, ""):
        solax.serial_number = str(raw.sn)
    solax.inverter_type = raw.type_code
    solax.upload_time = None
    if len(info) >= 10:
        # Information[9] sometimes carries transport/dongle info; keep as upload_time if numeric-ish
        pass
    solax.sleeping = is_night_data(data)
    solax.raw = list(data)


# ---------------------------------------------------------------------------
# Individual family decoders
# ---------------------------------------------------------------------------


def _decode_type_3(solax: SolaxData, data: list[Any]) -> None:
    """X1-Hybrid / Fit G1-G3 (type 3)."""
    solax.yield_today = _div(safe_get(data, 13), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 11), safe_get(data, 12)), 10.0)
    pv1_power = safe_get(data, 7)
    pv2_power = safe_get(data, 8)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.battery_power = read_signed16(safe_get(data, 18))
    solax.feed_in_power = read_signed32(safe_get(data, 48), safe_get(data, 49))
    solax.grid_power = read_signed16(safe_get(data, 2))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 50), safe_get(data, 51)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 52), safe_get(data, 53)), 100.0)
    solax.run_mode = _int(safe_get(data, 10))
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 43))
    solax.pv1_voltage = _div(safe_get(data, 3), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 4), 10.0)
    solax.pv1_current = _div(safe_get(data, 5), 10.0)
    solax.pv2_current = _div(safe_get(data, 6), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 44), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 45)), 10.0)
    solax.battery_soc = _int(safe_get(data, 20))
    solax.battery_voltage = _div(safe_get(data, 16), 100.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 19)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 9), 100.0)


def _decode_type_4_8(solax: SolaxData, data: list[Any]) -> None:
    """X1-Boost / Air / Mini / Smart (type 4 or 8)."""
    solax.yield_today = _div(safe_get(data, 13), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 11), safe_get(data, 12)), 10.0)
    pv1_power = safe_get(data, 7)
    pv2_power = safe_get(data, 8)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.feed_in_power = read_signed32(safe_get(data, 48), safe_get(data, 49))
    solax.grid_power = read_signed16(safe_get(data, 2))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 50), safe_get(data, 51)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 52), safe_get(data, 53)), 100.0)
    solax.run_mode = _int(safe_get(data, 10))
    solax.inverter_status = solax.run_mode
    solax.pv1_voltage = _div(safe_get(data, 3), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 4), 10.0)
    solax.pv1_current = _div(safe_get(data, 5), 10.0)
    solax.pv2_current = _div(safe_get(data, 6), 10.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 9), 100.0)


def _decode_type_5(solax: SolaxData, data: list[Any]) -> None:
    """X3-Hybrid / Fit G1-G3 (type 5)."""
    solax.yield_today = _div(safe_get(data, 21), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 19), safe_get(data, 20)), 10.0)
    pv1_power = safe_get(data, 13)
    pv2_power = safe_get(data, 14)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.battery_power = read_signed16(safe_get(data, 26))
    solax.feed_in_power = read_signed32(safe_get(data, 65), safe_get(data, 66))
    solax.grid_power = _sum(
        read_signed16(safe_get(data, 6)),
        read_signed16(safe_get(data, 7)),
        read_signed16(safe_get(data, 8)),
    )
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 67), safe_get(data, 68)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 69), safe_get(data, 70)), 100.0)
    solax.run_mode = _int(safe_get(data, 18))
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 60))
    solax.eps_power_l2 = read_signed16(safe_get(data, 61))
    solax.eps_power_l3 = read_signed16(safe_get(data, 62))
    solax.pv1_voltage = _div(safe_get(data, 9), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 10), 10.0)
    solax.pv1_current = _div(safe_get(data, 11), 10.0)
    solax.pv2_current = _div(safe_get(data, 12), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 54), 10.0)
    solax.eps_voltage_l2 = _div(safe_get(data, 55), 10.0)
    solax.eps_voltage_l3 = _div(safe_get(data, 56), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 57)), 10.0)
    solax.eps_current_l2 = _div(read_signed16(safe_get(data, 58)), 10.0)
    solax.eps_current_l3 = _div(read_signed16(safe_get(data, 59)), 10.0)
    solax.battery_soc = _int(safe_get(data, 28))
    solax.battery_voltage = _div(safe_get(data, 24), 100.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 27)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_voltage_l2 = _div(safe_get(data, 1), 10.0)
    solax.grid_voltage_l3 = _div(safe_get(data, 2), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 3)), 10.0)
    solax.grid_current_l2 = _div(read_signed16(safe_get(data, 4)), 10.0)
    solax.grid_current_l3 = _div(read_signed16(safe_get(data, 5)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 15), 100.0)
    solax.grid_frequency_l2 = _div(safe_get(data, 16), 100.0)
    solax.grid_frequency_l3 = _div(safe_get(data, 17), 100.0)


def _decode_type_9(solax: SolaxData, data: list[Any]) -> None:
    """X1-AC (type 9)."""
    solax.yield_today = _div(safe_get(data, 13), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 11), safe_get(data, 12)), 10.0)
    solax.battery_power = read_signed16(safe_get(data, 16))
    solax.feed_in_power = read_signed32(safe_get(data, 44), safe_get(data, 45))
    solax.grid_power = read_signed16(safe_get(data, 2))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 46), safe_get(data, 47)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 48), safe_get(data, 49)), 100.0)
    solax.run_mode = _int(safe_get(data, 10))
    solax.inverter_status = solax.run_mode
    solax.battery_soc = _int(safe_get(data, 18))
    solax.battery_voltage = _div(safe_get(data, 14), 100.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 17)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 9), 100.0)


def _decode_type_14(solax: SolaxData, data: list[Any]) -> None:
    """X3-Hybrid G4/G5 (type 14 or 24)."""
    solax.yield_today = _div(safe_get(data, 70), 10.0)
    # type 14 uses Data[68/69]; type 24 uses 71/72. Try 68/69 first.
    ut = read_unsigned32(safe_get(data, 68), safe_get(data, 69))
    if ut is None:
        ut = read_unsigned32(safe_get(data, 71), safe_get(data, 72))
    solax.yield_total = _div(ut, 10.0)
    pv1_power = safe_get(data, 14)
    pv2_power = safe_get(data, 15)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.battery_power = read_signed16(safe_get(data, 41))
    solax.feed_in_power = read_signed32(safe_get(data, 34), safe_get(data, 35))
    solax.grid_power = _sum(
        read_signed16(safe_get(data, 6)),
        read_signed16(safe_get(data, 7)),
        read_signed16(safe_get(data, 8)),
    )
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 86), safe_get(data, 87)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 88), safe_get(data, 89)), 100.0)
    solax.run_mode = _int(safe_get(data, 19))
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 29))
    solax.eps_power_l2 = read_signed16(safe_get(data, 30))
    solax.eps_power_l3 = read_signed16(safe_get(data, 31))
    solax.pv1_voltage = _div(safe_get(data, 10), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 11), 10.0)
    solax.pv1_current = _div(safe_get(data, 12), 10.0)
    solax.pv2_current = _div(safe_get(data, 13), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 23), 10.0)
    solax.eps_voltage_l2 = _div(safe_get(data, 24), 10.0)
    solax.eps_voltage_l3 = _div(safe_get(data, 25), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 26)), 10.0)
    solax.eps_current_l2 = _div(read_signed16(safe_get(data, 27)), 10.0)
    solax.eps_current_l3 = _div(read_signed16(safe_get(data, 28)), 10.0)
    solax.battery_soc = _int(safe_get(data, 103))
    # battery voltage: type 14 uses read32 unsigned 169/170 /100; type 24 uses Data[39]/100
    bv = read_unsigned32(safe_get(data, 169), safe_get(data, 170))
    if bv is None:
        bv_raw = safe_get(data, 39)
        solax.battery_voltage = _div(bv_raw, 100.0)
    else:
        solax.battery_voltage = _div(bv, 100.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 105)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_voltage_l2 = _div(safe_get(data, 1), 10.0)
    solax.grid_voltage_l3 = _div(safe_get(data, 2), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 3)), 10.0)
    solax.grid_current_l2 = _div(read_signed16(safe_get(data, 4)), 10.0)
    solax.grid_current_l3 = _div(read_signed16(safe_get(data, 5)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 16), 100.0)
    solax.grid_frequency_l2 = _div(safe_get(data, 17), 100.0)
    solax.grid_frequency_l3 = _div(safe_get(data, 18), 100.0)


def _decode_type_15(solax: SolaxData, data: list[Any]) -> None:
    """X1-Hybrid G4/G5 (type 15 or 23)."""
    solax.yield_today = _div(safe_get(data, 13), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 11), safe_get(data, 12)), 10.0)
    pv1_power = safe_get(data, 8)
    pv2_power = safe_get(data, 9)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.battery_power = read_signed16(safe_get(data, 16))
    solax.feed_in_power = read_signed32(safe_get(data, 32), safe_get(data, 33))
    solax.grid_power = read_signed16(safe_get(data, 2))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 34), safe_get(data, 35)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 36), safe_get(data, 37)), 100.0)
    solax.run_mode = _int(safe_get(data, 10))
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 28))
    solax.pv1_voltage = _div(safe_get(data, 4), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 5), 10.0)
    solax.pv1_current = _div(safe_get(data, 6), 10.0)
    solax.pv2_current = _div(safe_get(data, 7), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 29), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 30)), 10.0)
    solax.battery_soc = _int(safe_get(data, 18))
    solax.battery_voltage = _div(safe_get(data, 14), 100.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 17)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 3), 100.0)


def _decode_type_16(solax: SolaxData, data: list[Any]) -> None:
    """X3-MIC / PRO G2 (type 16)."""
    solax.yield_today = _div(safe_get(data, 24), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 22), safe_get(data, 23)), 10.0)
    pv1_power = safe_get(data, 15)
    pv2_power = safe_get(data, 16)
    pv3_power = safe_get(data, 17)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv3_power = _int(pv3_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power, pv3_power)
    solax.feed_in_power = read_signed32(safe_get(data, 72), safe_get(data, 73))
    solax.grid_power = _sum(
        read_signed16(safe_get(data, 6)),
        read_signed16(safe_get(data, 7)),
        read_signed16(safe_get(data, 8)),
    )
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 74), safe_get(data, 75)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 76), safe_get(data, 77)), 100.0)
    solax.run_mode = _int(safe_get(data, 21))
    solax.inverter_status = solax.run_mode
    solax.pv1_voltage = _div(safe_get(data, 9), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 10), 10.0)
    solax.pv3_voltage = _div(safe_get(data, 11), 10.0)
    solax.pv1_current = _div(safe_get(data, 12), 10.0)
    solax.pv2_current = _div(safe_get(data, 13), 10.0)
    solax.pv3_current = _div(safe_get(data, 14), 10.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_voltage_l2 = _div(safe_get(data, 1), 10.0)
    solax.grid_voltage_l3 = _div(safe_get(data, 2), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 3)), 10.0)
    solax.grid_current_l2 = _div(read_signed16(safe_get(data, 4)), 10.0)
    solax.grid_current_l3 = _div(read_signed16(safe_get(data, 5)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 18), 100.0)
    solax.grid_frequency_l2 = _div(safe_get(data, 19), 100.0)
    solax.grid_frequency_l3 = _div(safe_get(data, 20), 100.0)


def _decode_type_18_22(solax: SolaxData, data: list[Any]) -> None:
    """X1-Boost / Mini G4 (type 18 or 22)."""
    solax.yield_today = _div(safe_get(data, 21), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 19), safe_get(data, 20)), 10.0)
    pv1_power = safe_get(data, 13)
    pv2_power = safe_get(data, 14)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.feed_in_power = read_signed32(safe_get(data, 72), safe_get(data, 73))
    solax.grid_power = read_signed16(safe_get(data, 3))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 74), safe_get(data, 75)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 76), safe_get(data, 77)), 100.0)
    solax.run_mode = _int(safe_get(data, 10))
    solax.inverter_status = solax.run_mode
    solax.pv1_voltage = _div(safe_get(data, 4), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 5), 10.0)
    solax.pv1_current = _div(safe_get(data, 8), 10.0)
    solax.pv2_current = _div(safe_get(data, 9), 10.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 2), 100.0)


def _decode_type_19_21(solax: SolaxData, data: list[Any]) -> None:
    """A1-Hybrid G2 (type 19/20/21)."""
    solax.yield_today = _div(safe_get(data, 43), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 41), safe_get(data, 42)), 10.0)
    pv1_power = safe_get(data, 19)
    pv2_power = safe_get(data, 20)
    pv3_power = safe_get(data, 21)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv3_power = _int(pv3_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power, pv3_power)
    solax.battery_power = read_signed16(safe_get(data, 91))
    solax.feed_in_power = read_signed32(safe_get(data, 28), safe_get(data, 29))
    solax.grid_power = read_signed16(safe_get(data, 6))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 33), safe_get(data, 34)), 10.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 35), safe_get(data, 36)), 10.0)
    solax.run_mode = _int(read_signed16(safe_get(data, 10)))  # read8BitUnsigned in docs; safe
    # read8BitUnsigned
    rm = safe_get(data, 10)
    if rm is not None:
        try:
            solax.run_mode = int(float(rm)) % 256
        except (TypeError, ValueError):
            solax.run_mode = _int(rm)
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 27))
    solax.pv1_voltage = _div(safe_get(data, 11), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 12), 10.0)
    solax.pv3_voltage = _div(safe_get(data, 13), 10.0)
    solax.pv1_current = _div(safe_get(data, 15), 10.0)
    solax.pv2_current = _div(safe_get(data, 16), 10.0)
    solax.pv3_current = _div(safe_get(data, 17), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 24), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 25)), 10.0)
    solax.battery_soc = _int(safe_get(data, 93))
    solax.battery_voltage = _div(safe_get(data, 89), 100.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 92)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 4), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 5)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 7), 100.0)


def _decode_type_10_12(solax: SolaxData, data: list[Any]) -> None:
    """A1-Hybrid / Fit / Grid (type 10/11/12)."""
    solax.yield_today = _div(safe_get(data, 13), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 11), safe_get(data, 12)), 10.0)
    pv1_power = safe_get(data, 7)
    pv2_power = safe_get(data, 8)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    pv3_power = safe_get(data, 126)
    pv4_power = safe_get(data, 127)
    solax.pv3_power = _int(pv3_power)
    solax.pv4_power = _int(pv4_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power, pv3_power, pv4_power)
    solax.battery_power = read_signed16(safe_get(data, 18))
    solax.feed_in_power = read_signed32(safe_get(data, 48), safe_get(data, 49))
    solax.grid_power = read_signed16(safe_get(data, 2))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 50), safe_get(data, 51)), 10.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 52), safe_get(data, 53)), 10.0)
    solax.run_mode = _int(safe_get(data, 10))
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 43))
    solax.pv1_voltage = _div(safe_get(data, 3), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 4), 10.0)
    solax.pv3_voltage = _div(safe_get(data, 122), 10.0)
    solax.pv4_voltage = _div(safe_get(data, 123), 10.0)
    solax.pv1_current = _div(safe_get(data, 5), 10.0)
    solax.pv2_current = _div(safe_get(data, 6), 10.0)
    solax.pv3_current = _div(safe_get(data, 124), 10.0)
    solax.pv4_current = _div(safe_get(data, 125), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 44), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 45)), 10.0)
    solax.battery_soc = _int(safe_get(data, 20))
    solax.battery_voltage = _div(safe_get(data, 16), 100.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 19)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 9), 100.0)


def _decode_type_13_17(solax: SolaxData, data: list[Any]) -> None:
    """J1-ESS (type 13 or 17)."""
    solax.yield_today = _div(safe_get(data, 36), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 34), safe_get(data, 35)), 10.0)
    pv1_power = safe_get(data, 10)
    pv2_power = safe_get(data, 13)
    pv3_power = safe_get(data, 16)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv3_power = _int(pv3_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power, pv3_power)
    solax.battery_power = read_signed16(safe_get(data, 105))
    solax.feed_in_power = read_signed16(safe_get(data, 29))
    solax.grid_power = _sum(
        read_signed16(safe_get(data, 2)),
        read_signed16(safe_get(data, 5)),
    )
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 52), safe_get(data, 53)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 54), safe_get(data, 55)), 100.0)
    solax.run_mode = _int(safe_get(data, 17))
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 21))
    solax.eps_power_l2 = read_signed16(safe_get(data, 25))
    solax.pv1_voltage = _div(safe_get(data, 8), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 11), 10.0)
    solax.pv3_voltage = _div(safe_get(data, 14), 10.0)
    solax.pv1_current = _div(safe_get(data, 9), 10.0)
    solax.pv2_current = _div(safe_get(data, 12), 10.0)
    solax.pv3_current = _div(safe_get(data, 15), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 19), 10.0)
    solax.eps_voltage_l2 = _div(safe_get(data, 23), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 20)), 10.0)
    solax.eps_current_l2 = _div(read_signed16(safe_get(data, 24)), 10.0)
    solax.battery_soc = _int(safe_get(data, 80))
    solax.battery_voltage = _div(read_signed16(safe_get(data, 106)), 10.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 82)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_voltage_l2 = _div(safe_get(data, 3), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_current_l2 = _div(read_signed16(safe_get(data, 4)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 7), 100.0)


def _decode_type_100_101(solax: SolaxData, data: list[Any]) -> None:
    """Big string inverter (type 100/101)."""
    solax.yield_today = _div(read_signed16(safe_get(data, 48)), 10.0)
    solax.yield_total = _div(read_signed32(safe_get(data, 46), safe_get(data, 47)), 10.0)
    solax.grid_power = _sum(
        read_signed32(safe_get(data, 33), safe_get(data, 34)),
        read_signed32(safe_get(data, 35), safe_get(data, 36)),
        read_signed32(safe_get(data, 37), safe_get(data, 38)),
    )
    solax.run_mode = _int(safe_get(data, 56))
    solax.inverter_status = solax.run_mode
    # PV strings up to 4 (voltage/current)
    for i in range(1, 5):
        # indices: Vdc1=87, Idc1=88 etc with step 2
        base = 85 + i * 2
        v = read_signed16(safe_get(data, base))
        c = read_signed16(safe_get(data, base + 1))
        setattr(solax, f"pv{i}_voltage", _div(v, 10.0))
        setattr(solax, f"pv{i}_current", _div(c, 10.0))
    solax.grid_voltage_l1 = _div(safe_get(data, 27), 10.0)
    solax.grid_voltage_l2 = _div(safe_get(data, 28), 10.0)
    solax.grid_voltage_l3 = _div(safe_get(data, 29), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 30)), 10.0)
    solax.grid_current_l2 = _div(read_signed16(safe_get(data, 31)), 10.0)
    solax.grid_current_l3 = _div(read_signed16(safe_get(data, 32)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 39), 100.0)


def _decode_type_102(solax: SolaxData, data: list[Any]) -> None:
    """X1-Hybrid LV (type 102)."""
    solax.yield_today = _div(safe_get(data, 18), 10.0)
    solax.yield_total = _div(read_unsigned32(safe_get(data, 14), safe_get(data, 15)), 10.0)
    pv1_power = safe_get(data, 9)
    pv2_power = safe_get(data, 10)
    solax.pv1_power = _int(pv1_power)
    solax.pv2_power = _int(pv2_power)
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.battery_power = read_signed16(safe_get(data, 22))
    solax.feed_in_power = read_signed32(safe_get(data, 29), safe_get(data, 30))
    solax.grid_power = read_signed16(safe_get(data, 2))
    solax.feed_in_energy = _div(read_unsigned32(safe_get(data, 31), safe_get(data, 32)), 100.0)
    solax.consume_energy = _div(read_unsigned32(safe_get(data, 33), safe_get(data, 34)), 100.0)
    solax.run_mode = _int(safe_get(data, 12))
    solax.inverter_status = solax.run_mode
    solax.eps_power_l1 = read_signed16(safe_get(data, 43))
    solax.pv1_voltage = _div(safe_get(data, 5), 10.0)
    solax.pv2_voltage = _div(safe_get(data, 7), 10.0)
    solax.pv1_current = _div(safe_get(data, 6), 10.0)
    solax.pv2_current = _div(safe_get(data, 8), 10.0)
    solax.eps_voltage_l1 = _div(safe_get(data, 41), 10.0)
    solax.eps_current_l1 = _div(read_signed16(safe_get(data, 42)), 10.0)
    solax.battery_soc = _int(
        safe_get(data, 18)
    )  # docs: BatteryCapacity Data[18] (same as yield_today? odd); keep
    solax.battery_voltage = _div(safe_get(data, 20), 10.0)
    solax.battery_temp = _div(read_signed16(safe_get(data, 17)), 1.0)
    solax.grid_voltage_l1 = _div(safe_get(data, 0), 10.0)
    solax.grid_current_l1 = _div(read_signed16(safe_get(data, 1)), 10.0)
    solax.grid_frequency_l1 = _div(safe_get(data, 3), 100.0)


def _decode_legacy(solax: SolaxData, data: list[Any]) -> None:
    """Legacy Data1 mapping for type < 8 (and unknown fallback)."""
    solax.pv1_current = _try_float(safe_get(data, 0))
    solax.pv2_current = _try_float(safe_get(data, 1))
    solax.pv1_voltage = _try_float(safe_get(data, 2))
    solax.pv2_voltage = _try_float(safe_get(data, 3))
    solax.grid_current_l1 = _try_float(safe_get(data, 4))
    solax.grid_voltage_l1 = _try_float(safe_get(data, 5))
    solax.grid_power = _try_float(safe_get(data, 6))
    solax.yield_today = _try_float(safe_get(data, 8))
    solax.yield_total = _try_float(safe_get(data, 9))
    solax.feed_in_power = _try_float(safe_get(data, 10))
    pv1_power = safe_get(data, 11)
    pv2_power = safe_get(data, 12)
    solax.pv1_power = _int(pv1_power) if pv1_power is not None else None
    solax.pv2_power = _int(pv2_power) if pv2_power is not None else None
    solax.pv_power_total = _sum(pv1_power, pv2_power)
    solax.battery_voltage = _try_float(safe_get(data, 13))
    solax.battery_power = _try_float(safe_get(data, 15))
    solax.battery_temp = _try_float(safe_get(data, 16))
    solax.battery_soc = _int(safe_get(data, 21))
    solax.feed_in_energy = _try_float(safe_get(data, 41))
    solax.consume_energy = _try_float(safe_get(data, 42))
    solax.grid_power = (
        _try_float(safe_get(data, 43)) if safe_get(data, 43) is not None else solax.grid_power
    )
    # phase powers override total only if present? keep grid_power as Data[6] for legacy (already set)
    solax.grid_current_l2 = _try_float(safe_get(data, 46))
    solax.grid_current_l3 = _try_float(safe_get(data, 47))
    solax.grid_voltage_l2 = _try_float(safe_get(data, 48))
    solax.grid_voltage_l3 = _try_float(safe_get(data, 49))
    solax.grid_frequency_l1 = _try_float(safe_get(data, 50))
    solax.grid_frequency_l2 = _try_float(safe_get(data, 51))
    solax.grid_frequency_l3 = _try_float(safe_get(data, 52))
    solax.eps_voltage_l1 = _try_float(safe_get(data, 53))
    solax.eps_current_l1 = _try_float(safe_get(data, 54))
    solax.eps_power_l1 = _try_float(safe_get(data, 55))
    solax.run_mode = _int(safe_get(data, 68))
    solax.inverter_status = solax.run_mode
    solax.eps_voltage_l2 = _try_float(safe_get(data, 87))
    solax.eps_current_l2 = _try_float(safe_get(data, 88))
    solax.eps_power_l2 = _try_float(safe_get(data, 89))
    solax.eps_voltage_l3 = _try_float(safe_get(data, 90))
    solax.eps_current_l3 = _try_float(safe_get(data, 91))
    solax.eps_power_l3 = _try_float(safe_get(data, 92))


def _try_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def decode(raw: Any) -> SolaxData:
    """Decode a raw inverter payload into a normalized :class:`SolaxData`."""
    raw_n = _normalize_raw(raw)
    data = list(raw_n.data or [])
    solax = SolaxData()
    _common_setup(solax, raw_n, data)

    tc = raw_n.type_code
    try:
        if tc in (3, 5):
            if tc == 3:
                _decode_type_3(solax, data)
            else:
                _decode_type_5(solax, data)
        elif tc in (4, 8):
            _decode_type_4_8(solax, data)
        elif tc == 9:
            _decode_type_9(solax, data)
        elif tc in (14, 24):
            _decode_type_14(solax, data)
        elif tc in (15, 23):
            _decode_type_15(solax, data)
        elif tc == 16:
            _decode_type_16(solax, data)
        elif tc in (18, 22):
            _decode_type_18_22(solax, data)
        elif tc in (19, 20, 21):
            _decode_type_19_21(solax, data)
        elif tc in (10, 11, 12):
            _decode_type_10_12(solax, data)
        elif tc in (13, 17):
            _decode_type_13_17(solax, data)
        elif tc in (100, 101):
            _decode_type_100_101(solax, data)
        elif tc == 102:
            _decode_type_102(solax, data)
        elif tc < 8:
            _decode_legacy(solax, data)
        else:
            _LOGGER.warning("Unknown SolaX inverter type %s; using generic fallback", tc)
            try:
                _decode_legacy(solax, data)
            except Exception:
                _LOGGER.exception("Generic fallback failed for type %s", tc)
    except Exception as exc:
        _LOGGER.exception("Decoder failed for type %s: %s", tc, exc)

    if tc not in MODEL_NAMES and tc >= 0:
        _LOGGER.warning("Unknown SolaX inverter type code: %s", tc)

    # Local API reports raw run modes (0-13); the cloud exposes them as
    # 100-113. Normalize so the shared status table works for both.
    if solax.run_mode is not None and solax.inverter_status is not None:
        try:
            if int(solax.inverter_status) == int(solax.run_mode) and int(solax.run_mode) < 100:
                solax.inverter_status = int(solax.run_mode) + 100
        except (TypeError, ValueError):
            pass

    return solax
