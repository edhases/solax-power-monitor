"""Local (Pocket WiFi) SolaX client."""

from __future__ import annotations

import json
import logging
from typing import Any

import aiohttp
from homeassistant.core import HomeAssistant

from ..const import (
    SolaxAuthError,
    SolaxConnectionError,
    SolaxParseError,
)
from ..models import RawInverterData
from .base import SolaxClient

_LOGGER = logging.getLogger(__name__)

_DEFAULT_PORT = 80
_DEFAULT_TIMEOUT = 10


class SolaxLocalClient(SolaxClient):
    """Client for the local Pocket WiFi HTTP API."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int = _DEFAULT_PORT,
        password: str = "",
        username: str | None = None,
        timeout: int = _DEFAULT_TIMEOUT,
        **kwargs: Any,
    ) -> None:
        super().__init__(hass, **kwargs)
        self.hass = hass
        self.host = host
        self.port = port if port is not None else _DEFAULT_PORT
        self.password = password if password is not None else ""
        self.username = username
        self.timeout = timeout if timeout is not None else _DEFAULT_TIMEOUT
        self._session: aiohttp.ClientSession | None = None

    # ------------------------------------------------------------------
    # Session handling
    # ------------------------------------------------------------------
    def _build_url(self) -> str:
        port = self.port if self.port is not None else _DEFAULT_PORT
        return f"http://{self.host}:{port}/"

    def _ensure_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def async_validate(self) -> bool:
        """Probe the inverter with a single real-time data request."""
        await self.async_get_data()
        return True

    async def async_get_data(self) -> RawInverterData:
        """Fetch real-time data from the dongle and parse it."""
        session = self._ensure_session()
        url = self._build_url()
        headers = {"X-Forwarded-For": "5.8.8.8"}
        form = {"optType": "ReadRealTimeData", "pwd": self.password}
        timeout = aiohttp.ClientTimeout(total=self.timeout)

        try:
            async with session.post(url, data=form, headers=headers, timeout=timeout) as resp:
                status = resp.status
                if status in (401, 403):
                    raise SolaxAuthError(f"Authentication failed (HTTP {status})")
                if status >= 400:
                    raise SolaxConnectionError(f"Inverter returned HTTP {status}")

                text = await resp.text()
                if not text or not text.strip():
                    raise SolaxConnectionError("Empty response from inverter")

                try:
                    payload = json.loads(text)
                except (ValueError, TypeError) as err:
                    # Fall back to aiohttp's json decoder for odd content-types.
                    try:
                        payload = await resp.json(content_type=None)
                    except Exception:
                        raise SolaxParseError("Invalid JSON response from inverter") from err
        except SolaxAuthError:
            raise
        except SolaxConnectionError:
            raise
        except SolaxParseError:
            raise
        except TimeoutError as err:
            raise SolaxConnectionError("Timeout connecting to inverter") from err
        except aiohttp.ClientError as err:
            raise SolaxConnectionError(str(err)) from err
        except Exception as err:
            # Re-classify JSON errors raised above already handled; treat rest as parse.
            if isinstance(err, (SolaxAuthError, SolaxConnectionError, SolaxParseError)):
                raise
            raise SolaxParseError(str(err)) from err

        if not isinstance(payload, dict):
            raise SolaxParseError("Unexpected response payload type")

        # Detect explicit auth failures reported in-body.
        for key in ("error", "err", "message", "msg", "exception"):
            value = payload.get(key)
            if isinstance(value, str):
                lowered = value.lower()
                if any(
                    token in lowered
                    for token in ("password", "auth", "login", "unauthorized", "forbidden")
                ):
                    raise SolaxAuthError(value)

        success = payload.get("success")
        code = payload.get("code")
        if success is False or code in (1001, 1003):
            raise SolaxAuthError(
                str(payload.get("exception") or payload.get("message") or "Authentication failed")
            )

        # Extract fields.
        sn = payload.get("sn", payload.get("serial", payload.get("inverterSN", "")))
        ver = payload.get("ver", payload.get("version", payload.get("firmware", "")))
        type_code_raw = payload.get(
            "type", payload.get("type_code", payload.get("inverterType", 0))
        )
        try:
            type_code = int(float(type_code_raw))
        except (TypeError, ValueError):
            type_code = 0

        data_list = payload.get("Data", payload.get("data"))
        if data_list is None:
            data_list = []
        if not isinstance(data_list, list):
            raise SolaxParseError("Response 'Data' field is not a list")

        information = payload.get("Information", payload.get("information"))
        if information is None:
            information = []
        if not isinstance(information, list):
            information = list(information) if hasattr(information, "__iter__") else []

        return RawInverterData(
            sn=sn if sn is not None else "",
            ver=ver if ver is not None else "",
            type_code=type_code,
            data=list(data_list),
            information=list(information),
        )

    async def async_close(self) -> None:
        """Close the underlying aiohttp session."""
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None

    async def close(self) -> None:
        await self.async_close()
