"""Smoke tests for the Solax decoders (run in CI with HA available)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# HA may not be installed locally; skip gracefully.
try:
    from custom_components.solax_ha.models import RawInverterData, decode, is_night_data
    from custom_components.solax_ha.const import SolaxData
except Exception:  # noqa: BLE001
    import pytest

    pytest.skip("Home Assistant not available", allow_module_level=True)


def test_decode_type_15_does_not_crash():
    raw = RawInverterData(
        sn="DONGLE123",
        ver="3.003.02",
        type_code=15,
        data=[0] * 60,
        information=[5.0, 15, "INV123", 8, 1.3, 0.0, 1.28, 1.04, 0.0, 1],
    )
    result = decode(raw)
    assert isinstance(result, SolaxData)
    assert result.sleeping is True


def test_is_night_data():
    assert is_night_data([0, 0, 0]) is True
    assert is_night_data([1, 0, 0]) is False
    assert is_night_data([]) is True


def test_decode_unknown_type_no_crash():
    raw = RawInverterData(sn="x", ver="1", type_code=999, data=[1, 2, 3], information=[])
    result = decode(raw)
    assert isinstance(result, SolaxData)