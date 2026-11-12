"""Shared test fixtures for solax_ha."""
import json
import pathlib

import pytest


FIXTURES = pathlib.Path(__file__).parent / "fixtures"


def load_fixture(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def fixtures_dir():
    return FIXTURES