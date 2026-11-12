"""Data update coordinator for the SolaX HA integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntryAuthFailed
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DEFAULT_SCAN_INTERVAL_LOCAL,
    SolaxAuthError,
    SolaxConnectionError,
    SolaxData,
    SolaxParseError,
    SolaxRateLimitError,
    is_night_data,
)

_LOGGER = logging.getLogger(__name__)


class SolaxDataUpdateCoordinator(DataUpdateCoordinator[SolaxData]):
    """Poll a SolaX client and expose normalized :class:`SolaxData`."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: Any,
        scan_interval: int,
        night_mode: str = "unavailable",
    ) -> None:
        self.client = client
        self.night_mode = night_mode
        self.scan_interval = int(scan_interval or DEFAULT_SCAN_INTERVAL_LOCAL)
        super().__init__(
            hass,
            _LOGGER,
            name="solax_ha",
            update_interval=timedelta(seconds=self.scan_interval),
        )

    def set_scan_interval(self, seconds: int) -> None:
        """Update the polling interval without reloading the entry."""
        self.scan_interval = int(seconds)
        self.update_interval = timedelta(seconds=self.scan_interval)

    # Convenience aliases for callers/tests.
    def set_update_interval(self, seconds: int) -> None:
        self.set_scan_interval(seconds)

    def async_set_update_interval(self, seconds: int) -> None:
        self.set_scan_interval(seconds)

    def update_scan_interval(self, seconds: int) -> None:
        self.set_scan_interval(seconds)

    def async_set_scan_interval(self, seconds: int) -> None:
        self.set_scan_interval(seconds)

    async def _async_update_data(self) -> SolaxData:
        try:
            raw = await self.client.async_get_data()
        except SolaxAuthError as err:
            raise ConfigEntryAuthFailed(err) from err
        except (
            SolaxConnectionError,
            SolaxRateLimitError,
            SolaxParseError,
        ) as err:
            raise UpdateFailed(err) from err
        except Exception as err:  # noqa: BLE001
            raise UpdateFailed(err) from err

        if raw is None:
            raise UpdateFailed("No data returned by client")

        from .const import SolaxData

        if isinstance(raw, SolaxData):
            data = raw
        else:
            try:
                from . import models

                data = models.decode(raw)
            except Exception as err:  # noqa: BLE001
                raise SolaxParseError(err) from err

        self._classify_sleeping(data)
        return data

    def _classify_sleeping(self, data: SolaxData) -> None:
        """Classify night/sleep state when the client did not set it."""
        if getattr(data, "sleeping", None) is not None:
            return
        sleeping = False
        raw = getattr(data, "raw", None)
        if isinstance(raw, (list, tuple)):
            sleeping = is_night_data(list(raw))
        elif isinstance(raw, dict):
            candidate = raw.get("Data") if isinstance(raw, dict) else None
            if isinstance(candidate, (list, tuple)):
                sleeping = is_night_data(list(candidate))
        data.sleeping = bool(sleeping)
