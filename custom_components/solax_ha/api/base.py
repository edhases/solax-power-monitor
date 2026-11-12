"""Abstract base client for SolaX connections."""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from ..const import (
    SolaxAuthError,
    SolaxConnectionError,
    SolaxParseError,
    SolaxRateLimitError,
)

if TYPE_CHECKING:
    from ..models import RawInverterData

__all__ = [
    "SolaxAuthError",
    "SolaxClient",
    "SolaxConnectionError",
    "SolaxParseError",
    "SolaxRateLimitError",
]


class SolaxClient(abc.ABC):
    """Abstract interface for a SolaX data source."""

    def __init__(self, hass: HomeAssistant, *args: Any, **kwargs: Any) -> None:
        self.hass = hass

    @abc.abstractmethod
    async def async_get_data(self) -> RawInverterData:
        """Fetch and return raw inverter data."""

    @abc.abstractmethod
    async def async_validate(self) -> bool:
        """Validate the connection/credentials with a single probe request."""

    @abc.abstractmethod
    async def async_close(self) -> None:
        """Release any held resources (sessions, sockets)."""
