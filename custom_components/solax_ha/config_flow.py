"""Config flow for the SolaX HA integration."""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import socket
from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.components import dhcp
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.const import (
    CONF_HOST,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_TIMEOUT,
    CONF_USERNAME,
)
from homeassistant.core import callback

from .const import (
    CONNECTION_TYPE_CLOUD,
    CONNECTION_TYPE_LOCAL,
    CONNECTION_TYPE_MODBUS,
    CONNECTION_TYPES,
    DEFAULT_SCAN_INTERVAL_CLOUD,
    DEFAULT_SCAN_INTERVAL_LOCAL,
    DEFAULT_SCAN_INTERVAL_MODBUS,
    DEFAULT_TIMEOUT,
    DOMAIN,
    SolaxAuthError,
    SolaxConnectionError,
    SolaxParseError,
)
from .models import MODEL_NAMES

_LOGGER = logging.getLogger(__name__)

CONF_METHOD = "method"
CONF_TOKEN_ID = "token_id"
CONF_SERIAL_NUMBER = "serial_number"
CONF_DOMAIN = "domain"
CONF_UNIT_ID = "unit_id"
CONF_CONNECTION_TYPE = "connection_type"
CONF_SERIAL_PORT = "serial_port"
CONF_BAUDRATE = "baudrate"
CONF_MODEL = "model"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MODEL_OVERRIDE = "model_override"
CONF_ENTITY_GROUP_PV = "entity_group_pv"
CONF_ENTITY_GROUP_BATTERY = "entity_group_battery"
CONF_ENTITY_GROUP_GRID = "entity_group_grid"
CONF_ENTITY_GROUP_INVERTER = "entity_group_inverter"
CONF_ENTITY_GROUP_EPS = "entity_group_eps"
CONF_ENTITY_GROUP_ENERGY = "entity_group_energy"
CONF_NIGHT_MODE = "night_mode"

DEFAULT_CLOUD_DOMAIN = "global.solaxcloud.com"
DEFAULT_MODBUS_PORT = 502
DEFAULT_MODBUS_UNIT_ID = 1
DEFAULT_BAUDRATE = 19200

ENTITY_GROUPS = [
    CONF_ENTITY_GROUP_PV,
    CONF_ENTITY_GROUP_BATTERY,
    CONF_ENTITY_GROUP_GRID,
    CONF_ENTITY_GROUP_INVERTER,
    CONF_ENTITY_GROUP_EPS,
    CONF_ENTITY_GROUP_ENERGY,
]


def _err_from_exception(err: Exception) -> str:
    if isinstance(err, SolaxAuthError):
        return "invalid_auth"
    if isinstance(err, (SolaxConnectionError, SolaxParseError)):
        return "cannot_connect"
    if isinstance(err, (TimeoutError, OSError, ValueError)):
        return "cannot_connect"
    return "unknown"


def _local_ipv4() -> str | None:
    """Best-effort discovery of this host's LAN IPv4 address."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return None
    finally:
        sock.close()


def _looks_like_solax_body(text: str) -> bool:
    """Return True if a response body looks like a SolaX dongle response."""
    if not text:
        return False
    stripped = text.strip()
    lowered = stripped.lower()
    # Dongles reply with e.g. ``0:code,message:"failed"}`` when the password
    # is missing/wrong, or with a JSON real-time payload when it is correct.
    if "code,message" in lowered:
        return True
    if any(token in lowered for token in ("solax", "pocket", "espressif", "opttype")):
        return True
    try:
        payload = json.loads(stripped)
    except (TypeError, ValueError):
        return False
    if not isinstance(payload, dict):
        return False
    if any(
        key in payload for key in ("Data", "data", "sn", "SN", "type", "Information", "information")
    ):
        return True
    exc = str(
        payload.get("exception") or payload.get("message") or payload.get("msg") or ""
    ).lower()
    return any(token in exc for token in ("pwd", "password", "solax", "inverter", "opttype"))


async def _async_probe_host(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if the host answers like a SolaX Pocket WiFi dongle.

    The dongle password is unknown during discovery, so we accept either a
    real-time payload (if the dongle allows passwordless reads) or a SolaX
    specific response/web page signature.
    """
    url = f"http://{host}:{port}/"
    headers = {"X-Forwarded-For": "5.8.8.8"}
    form = {"optType": "ReadRealTimeData", "pwd": ""}
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as session:
            try:
                async with session.post(url, data=form, headers=headers) as resp:
                    text = await resp.text(errors="ignore")
                    if resp.status < 500:
                        if _looks_like_solax_body(text):
                            return True
                        # A device answered on the API port with a body; if it is
                        # not SolaX there is no point in the GET fallback.
                        if text.strip():
                            return False
            except (TimeoutError, aiohttp.ClientError, OSError):
                pass

            try:
                async with session.get(url) as resp:
                    text = await resp.text(errors="ignore")
                    if _looks_like_solax_body(text):
                        return True
            except (TimeoutError, aiohttp.ClientError, OSError):
                return False
    except (TimeoutError, aiohttp.ClientError, OSError):
        return False
    return False


async def _async_scan_network(port: int = 80) -> list[str]:
    """Scan the local /24 subnet for SolaX dongles."""
    local_ip = _local_ipv4()
    if not local_ip:
        return []
    prefix = local_ip.rsplit(".", 1)[0]
    hosts = [f"{prefix}.{i}" for i in range(1, 255) if f"{prefix}.{i}" != local_ip]
    semaphore = asyncio.Semaphore(64)

    async def _check(host: str) -> str | None:
        async with semaphore:
            return host if await _async_probe_host(host, port) else None

    results = await asyncio.gather(*(_check(host) for host in hosts))
    return [host for host in results if host]


class SolaxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for SolaX HA."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._models: list[str] = []
        self._dhcp_host: str | None = None
        self._found_hosts: list[str] = []

    # ------------------------------------------------------------------
    # User step
    # ------------------------------------------------------------------
    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            method = user_input[CONF_METHOD]
            self._data[CONF_METHOD] = method
            self._data["connection_type"] = method
            if method == CONNECTION_TYPE_LOCAL:
                return await self.async_step_local()
            if method == "discover":
                return await self.async_step_discover()
            if method == CONNECTION_TYPE_CLOUD:
                return await self.async_step_cloud()
            if method == CONNECTION_TYPE_MODBUS:
                return await self.async_step_modbus()

        schema = vol.Schema(
            {
                vol.Required(CONF_METHOD, default=CONNECTION_TYPE_LOCAL): vol.In(
                    [*CONNECTION_TYPES, "discover"]
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    # ------------------------------------------------------------------
    # Auto-discovery (DHCP + subnet scan)
    # ------------------------------------------------------------------
    async def async_step_dhcp(self, discovery_info: dhcp.DhcpServiceInfo) -> Any:
        """Handle a dongle discovered via DHCP."""
        self._dhcp_host = discovery_info.ip
        self._data[CONF_METHOD] = CONNECTION_TYPE_LOCAL
        self._data["connection_type"] = CONNECTION_TYPE_LOCAL
        return await self.async_step_local()

    async def async_step_discover(self, user_input: dict[str, Any] | None = None) -> Any:
        """Scan the LAN for SolaX dongles and let the user pick one."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input.get("host")
            if host:
                self._dhcp_host = host
                self._data[CONF_METHOD] = CONNECTION_TYPE_LOCAL
                self._data["connection_type"] = CONNECTION_TYPE_LOCAL
                return await self.async_step_local()

        found = await _async_scan_network()
        self._found_hosts = found

        if found:
            schema = vol.Schema(
                {
                    vol.Required("host", default=found[0]): vol.In(found),
                }
            )
            return self.async_show_form(
                step_id="discover",
                data_schema=schema,
                description_placeholders={"count": str(len(found))},
                errors=errors,
            )

        self._dhcp_host = None
        return self.async_show_form(
            step_id="discover",
            data_schema=vol.Schema({vol.Optional("host"): str}),
            description_placeholders={"count": "0"},
            errors={"base": "no_inverter_found"},
        )

    # ------------------------------------------------------------------
    # Local
    # ------------------------------------------------------------------
    async def async_step_local(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input.get(CONF_PORT, 80)
            password = user_input.get(CONF_PASSWORD, "")
            username = user_input.get(CONF_USERNAME) or None

            # Lazy import.
            from .api.local import SolaxLocalClient

            client = SolaxLocalClient(
                hass=self.hass,
                host=host,
                port=port,
                password=password,
                username=username,
                timeout=DEFAULT_TIMEOUT,
            )
            try:
                raw = await client.async_validate()
            except Exception as err:
                errors["base"] = _err_from_exception(err)
                await _safe_close(client)
            else:
                await _safe_close(client)
                serial = _serial_from_raw(raw)
                if serial:
                    await self.async_set_unique_id(str(serial))
                    self._abort_if_unique_id_configured()

                type_code = getattr(raw, "type_code", 0)
                try:
                    type_code = int(type_code)
                except (TypeError, ValueError):
                    type_code = 0
                model = MODEL_NAMES.get(type_code, f"Unknown (type {type_code})")

                self._data.update(
                    {
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_PASSWORD: password,
                        CONF_USERNAME: username,
                        "host": host,
                        "port": port,
                        "password": password,
                        "username": username,
                    }
                )
                if serial:
                    self._data["serial_number"] = str(serial)
                    self._data["inverter_serial"] = str(serial)

                self._models = [model]
                # If multiple candidates were somehow detected, allow selection.
                if len(self._models) > 1:
                    self._data["model"] = self._models[0]
                    return await self.async_step_select_model()

                self._data["model"] = model
                return self._create_entry_from_data(serial or host)

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=80): int,
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_USERNAME): str,
            }
        )
        suggested = dict(user_input or {})
        if self._dhcp_host and CONF_HOST not in suggested:
            suggested[CONF_HOST] = self._dhcp_host
        return self.async_show_form(
            step_id="local",
            data_schema=self.add_suggested_values_to_schema(schema, suggested),
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Cloud
    # ------------------------------------------------------------------
    async def async_step_cloud(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            token_id = user_input[CONF_TOKEN_ID]
            serial_number = user_input[CONF_SERIAL_NUMBER]
            domain = user_input.get(CONF_DOMAIN) or DEFAULT_CLOUD_DOMAIN

            try:
                serial, type_code = await self._probe_cloud(token_id, serial_number, domain)
            except Exception as err:
                errors["base"] = _err_from_exception(err)
            else:
                if serial:
                    await self.async_set_unique_id(str(serial))
                    self._abort_if_unique_id_configured()

                model = None
                if type_code is not None:
                    try:
                        model = MODEL_NAMES.get(int(type_code))
                    except (TypeError, ValueError):
                        model = None
                if model is None:
                    model = "auto"

                self._data.update(
                    {
                        CONF_TOKEN_ID: token_id,
                        CONF_SERIAL_NUMBER: serial_number,
                        CONF_DOMAIN: domain,
                        "token_id": token_id,
                        "serial_number": serial_number,
                        "domain": domain,
                    }
                )
                if serial:
                    self._data["inverter_serial"] = str(serial)
                self._models = [model] if model and model != "auto" else []
                if len(self._models) > 1:
                    self._data["model"] = self._models[0]
                    return await self.async_step_select_model()

                self._data["model"] = model
                return self._create_entry_from_data(serial or serial_number)

        schema = vol.Schema(
            {
                vol.Required(CONF_TOKEN_ID): str,
                vol.Required(CONF_SERIAL_NUMBER): str,
                vol.Optional(CONF_DOMAIN, default=DEFAULT_CLOUD_DOMAIN): str,
            }
        )
        return self.async_show_form(
            step_id="cloud",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def _probe_cloud(self, token_id: str, serial_number: str, domain: str) -> tuple[Any, Any]:
        import aiohttp

        url = f"https://{domain}/api/v2/dataAccess/realtimeInfo/get"
        headers = {"tokenId": token_id, "Content-Type": "application/json"}
        body = {"wifiSn": serial_number}
        timeout = aiohttp.ClientTimeout(total=15)
        session = aiohttp.ClientSession(timeout=timeout)
        try:
            async with session.post(url, json=body, headers=headers) as resp:
                status = resp.status
                if status in (401, 403):
                    raise SolaxAuthError(f"HTTP {status}")
                text = await resp.text()
                if not text or not text.strip():
                    raise SolaxConnectionError("Empty response from cloud")
                try:
                    payload = json.loads(text)
                except (ValueError, TypeError) as err:
                    raise SolaxParseError("Invalid JSON from cloud") from err
        finally:
            await session.close()

        if not isinstance(payload, dict):
            raise SolaxParseError("Unexpected cloud payload")

        code = payload.get("code")
        success = payload.get("success", True)
        if code in (1001, 1002, 1003):
            raise SolaxAuthError(str(payload.get("exception") or "Auth failed"))
        if success is False:
            raise SolaxConnectionError(str(payload.get("exception") or "Request failed"))
        if code not in (0, None):
            raise SolaxConnectionError(str(payload.get("exception") or f"Cloud error code {code}"))

        result = payload.get("result") or {}
        serial = result.get("inverterSN") or result.get("inverterSn") or result.get("sn")
        type_code = result.get("inverterType")
        return serial, type_code

    # ------------------------------------------------------------------
    # Modbus
    # ------------------------------------------------------------------
    async def async_step_modbus(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input.get(CONF_HOST, "")
            port = user_input.get(CONF_PORT, DEFAULT_MODBUS_PORT)
            unit_id = user_input.get(CONF_UNIT_ID, DEFAULT_MODBUS_UNIT_ID)
            conn_type = user_input.get(CONF_CONNECTION_TYPE, "tcp")
            serial_port = user_input.get(CONF_SERIAL_PORT)
            baudrate = user_input.get(CONF_BAUDRATE, DEFAULT_BAUDRATE)

            try:
                await self._probe_modbus(host, port, unit_id, conn_type, serial_port, baudrate)
            except Exception as err:
                errors["base"] = _err_from_exception(err)
            else:
                uid = f"{host}:{port}:{unit_id}"
                await self.async_set_unique_id(uid)
                self._abort_if_unique_id_configured()

                self._data.update(
                    {
                        CONF_HOST: host,
                        CONF_PORT: port,
                        CONF_UNIT_ID: unit_id,
                        CONF_CONNECTION_TYPE: conn_type,
                        CONF_SERIAL_PORT: serial_port,
                        CONF_BAUDRATE: baudrate,
                        "host": host,
                        "port": port,
                        "unit_id": unit_id,
                        "connection_type": conn_type,
                        "serial_port": serial_port,
                        "baudrate": baudrate,
                    }
                )
                self._data["model"] = "auto"
                return self._create_entry_from_data(uid)

        schema = vol.Schema(
            {
                vol.Optional(CONF_HOST, default=""): str,
                vol.Optional(CONF_PORT, default=DEFAULT_MODBUS_PORT): int,
                vol.Optional(CONF_UNIT_ID, default=DEFAULT_MODBUS_UNIT_ID): int,
                vol.Required(CONF_CONNECTION_TYPE, default="tcp"): vol.In(["tcp", "rtu"]),
                vol.Optional(CONF_SERIAL_PORT): str,
                vol.Optional(CONF_BAUDRATE, default=DEFAULT_BAUDRATE): int,
            }
        )
        return self.async_show_form(
            step_id="modbus",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def _probe_modbus(
        self,
        host: str,
        port: Any,
        unit_id: Any,
        conn_type: str,
        serial_port: str | None,
        baudrate: Any,
    ) -> None:
        def _sync() -> None:
            try:
                from pymodbus.client import ModbusSerialClient, ModbusTcpClient
            except Exception as err:
                raise SolaxConnectionError("pymodbus is not installed") from err

            if conn_type in ("rtu", "RTU"):
                client = ModbusSerialClient(
                    port=serial_port, baudrate=baudrate or DEFAULT_BAUDRATE, timeout=5
                )
            else:
                client = ModbusTcpClient(
                    host=host, port=int(port or DEFAULT_MODBUS_PORT), timeout=5
                )

            connected = False
            try:
                connected = bool(client.connect())
            except Exception as err:
                raise SolaxConnectionError(str(err)) from err
            if not connected:
                raise SolaxConnectionError("Cannot connect to Modbus device")

            try:
                rr = None
                last_exc: Exception | None = None
                for kwargs in ({"slave": int(unit_id)}, {"unit": int(unit_id)}, {}):
                    try:
                        rr = client.read_holding_registers(0, count=1, **kwargs)
                        break
                    except TypeError as exc:
                        last_exc = exc
                        continue
                if rr is None:
                    if last_exc is not None:
                        raise SolaxConnectionError(str(last_exc))
                    raise SolaxConnectionError("Read failed")
                if getattr(rr, "isError", lambda: False)():
                    raise SolaxConnectionError("Modbus read error")
            finally:
                with contextlib.suppress(Exception):
                    client.close()

        await self.hass.async_add_executor_job(_sync)

    # ------------------------------------------------------------------
    # Select model
    # ------------------------------------------------------------------
    async def async_step_select_model(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            self._data["model"] = user_input[CONF_MODEL]
            serial = self._data.get("inverter_serial") or self._data.get("serial_number")
            return self._create_entry_from_data(serial or self._data.get(CONF_HOST, "SolaX"))

        choices = self._models if self._models else ["auto"]
        schema = vol.Schema({vol.Required(CONF_MODEL, default=choices[0]): vol.In(choices)})
        return self.async_show_form(step_id="select_model", data_schema=schema, errors=errors)

    # ------------------------------------------------------------------
    # Reauth
    # ------------------------------------------------------------------
    async def async_step_reauth(self, user_input: dict[str, Any] | None = None) -> Any:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        self._reauth_entry = entry
        method = (entry.data or {}).get(CONF_METHOD) or (entry.data or {}).get("connection_type")
        if method == CONNECTION_TYPE_LOCAL:
            return await self._reauth_local(entry, user_input)
        if method == CONNECTION_TYPE_CLOUD:
            return await self._reauth_cloud(entry, user_input)
        if method == CONNECTION_TYPE_MODBUS:
            return await self._reauth_modbus(entry, user_input)
        # Fallback: update generic.
        if user_input is not None:
            self.hass.config_entries.async_update_entry(entry, data={**entry.data, **user_input})
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_show_form(step_id="reauth", data_schema=vol.Schema({}))

    async def _reauth_local(self, entry: ConfigEntry, user_input):
        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(entry.data or {})
            data[CONF_PASSWORD] = user_input.get(CONF_PASSWORD, data.get(CONF_PASSWORD, ""))
            data[CONF_USERNAME] = user_input.get(CONF_USERNAME, data.get(CONF_USERNAME))
            data["password"] = data[CONF_PASSWORD]
            data["username"] = data[CONF_USERNAME]
            # validate
            from .api.local import SolaxLocalClient

            client = SolaxLocalClient(
                hass=self.hass,
                host=data.get(CONF_HOST, data.get("host")),
                port=data.get(CONF_PORT, data.get("port", 80)),
                password=data[CONF_PASSWORD],
                username=data[CONF_USERNAME],
                timeout=DEFAULT_TIMEOUT,
            )
            try:
                await client.async_validate()
            except Exception as err:
                errors["base"] = _err_from_exception(err)
                await _safe_close(client)
            else:
                await _safe_close(client)
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema(
            {
                vol.Required(CONF_PASSWORD): str,
                vol.Optional(CONF_USERNAME): str,
            }
        )
        return self.async_show_form(
            step_id="reauth",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def _reauth_cloud(self, entry: ConfigEntry, user_input):
        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(entry.data or {})
            data[CONF_TOKEN_ID] = user_input.get(CONF_TOKEN_ID, data.get(CONF_TOKEN_ID))
            data["token_id"] = data[CONF_TOKEN_ID]
            domain = data.get(CONF_DOMAIN, data.get("domain", DEFAULT_CLOUD_DOMAIN))
            serial_number = data.get(CONF_SERIAL_NUMBER, data.get("serial_number"))
            try:
                await self._probe_cloud(data[CONF_TOKEN_ID], serial_number, domain)
            except Exception as err:
                errors["base"] = _err_from_exception(err)
            else:
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reauth_successful")

        schema = vol.Schema({vol.Required(CONF_TOKEN_ID): str})
        return self.async_show_form(
            step_id="reauth",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def _reauth_modbus(self, entry: ConfigEntry, user_input):
        if user_input is not None:
            await self.hass.config_entries.async_reload(entry.entry_id)
            return self.async_abort(reason="reauth_successful")
        return self.async_show_form(step_id="reauth", data_schema=vol.Schema({}))

    # ------------------------------------------------------------------
    # Reconfigure
    # ------------------------------------------------------------------
    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> Any:
        entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        errors: dict[str, str] = {}
        if user_input is not None:
            data = dict(entry.data or {})
            data.update(user_input)
            # normalize
            if CONF_HOST in user_input:
                data["host"] = user_input[CONF_HOST]
            if CONF_PORT in user_input:
                data["port"] = user_input[CONF_PORT]
            method = data.get(CONF_METHOD) or data.get("connection_type")
            # validate for local
            if method == CONNECTION_TYPE_LOCAL:
                from .api.local import SolaxLocalClient

                client = SolaxLocalClient(
                    hass=self.hass,
                    host=data.get(CONF_HOST, data.get("host")),
                    port=data.get(CONF_PORT, data.get("port", 80)),
                    password=data.get(CONF_PASSWORD, data.get("password", "")),
                    username=data.get(CONF_USERNAME, data.get("username")),
                    timeout=DEFAULT_TIMEOUT,
                )
                try:
                    await client.async_validate()
                except Exception as err:
                    errors["base"] = _err_from_exception(err)
                    await _safe_close(client)
                else:
                    await _safe_close(client)
                    self.hass.config_entries.async_update_entry(entry, data=data)
                    await self.hass.config_entries.async_reload(entry.entry_id)
                    return self.async_abort(reason="reconfigure_successful")
            else:
                self.hass.config_entries.async_update_entry(entry, data=data)
                await self.hass.config_entries.async_reload(entry.entry_id)
                return self.async_abort(reason="reconfigure_successful")

        # Build schema based on method
        method = (entry.data or {}).get(CONF_METHOD) or (entry.data or {}).get("connection_type")
        if method == CONNECTION_TYPE_LOCAL:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_HOST, default=entry.data.get(CONF_HOST, entry.data.get("host"))
                    ): str,
                    vol.Optional(
                        CONF_PORT, default=entry.data.get(CONF_PORT, entry.data.get("port", 80))
                    ): int,
                    vol.Optional(
                        CONF_PASSWORD,
                        default=entry.data.get(CONF_PASSWORD, entry.data.get("password", "")),
                    ): str,
                    vol.Optional(
                        CONF_USERNAME,
                        default=entry.data.get(CONF_USERNAME, entry.data.get("username")),
                    ): str,
                }
            )
        elif method == CONNECTION_TYPE_CLOUD:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_TOKEN_ID,
                        default=entry.data.get(CONF_TOKEN_ID, entry.data.get("token_id")),
                    ): str,
                    vol.Optional(
                        CONF_DOMAIN,
                        default=entry.data.get(
                            CONF_DOMAIN, entry.data.get("domain", DEFAULT_CLOUD_DOMAIN)
                        ),
                    ): str,
                }
            )
        else:
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_HOST, default=entry.data.get(CONF_HOST, entry.data.get("host", ""))
                    ): str,
                    vol.Optional(
                        CONF_PORT,
                        default=entry.data.get(
                            CONF_PORT, entry.data.get("port", DEFAULT_MODBUS_PORT)
                        ),
                    ): int,
                }
            )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=schema,
            errors=errors,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_entry_from_data(self, title: Any) -> Any:
        data = dict(self._data)
        # Ensure method stored.
        method = data.get(CONF_METHOD, data.get("connection_type", CONNECTION_TYPE_LOCAL))
        data.setdefault("method", method)
        data.setdefault("connection_type", method)
        # Default scan interval by method.
        if method == CONNECTION_TYPE_CLOUD:
            default_interval = DEFAULT_SCAN_INTERVAL_CLOUD
        elif method == CONNECTION_TYPE_MODBUS:
            default_interval = DEFAULT_SCAN_INTERVAL_MODBUS
        else:
            default_interval = DEFAULT_SCAN_INTERVAL_LOCAL
        data.setdefault("scan_interval", default_interval)
        data.setdefault(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        return self.async_create_entry(title=str(title), data=data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> SolaxOptionsFlow:
        return SolaxOptionsFlow(config_entry)


class SolaxOptionsFlow(OptionsFlow):
    """Handle options flow."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> Any:
        return await self.async_step_options(user_input)

    async def async_step_options(self, user_input: dict[str, Any] | None = None) -> Any:
        errors: dict[str, str] = {}
        if user_input is not None:
            # validate timeout
            try:
                to = int(user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT))
            except (TypeError, ValueError):
                to = DEFAULT_TIMEOUT
            if to < 5 or to > 30:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title="", data=user_input)

        current = {**self.config_entry.data, **(self.config_entry.options or {})}
        default_interval = current.get(
            CONF_SCAN_INTERVAL,
            current.get("scan_interval", DEFAULT_SCAN_INTERVAL_LOCAL),
        )
        default_timeout = current.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        default_model = current.get(CONF_MODEL_OVERRIDE, "auto")
        default_night = current.get(CONF_NIGHT_MODE, "unavailable")

        model_choices = ["auto", *sorted(set(MODEL_NAMES.values()))]

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_SCAN_INTERVAL,
                    default=default_interval,
                ): vol.In([5, 10, 30, 60, 300]),
                vol.Optional(CONF_TIMEOUT, default=default_timeout): vol.All(
                    int, vol.Range(min=5, max=30)
                ),
                vol.Optional(CONF_MODEL_OVERRIDE, default=default_model): vol.In(model_choices),
                vol.Optional(
                    CONF_ENTITY_GROUP_PV,
                    default=current.get(CONF_ENTITY_GROUP_PV, True),
                ): bool,
                vol.Optional(
                    CONF_ENTITY_GROUP_BATTERY,
                    default=current.get(CONF_ENTITY_GROUP_BATTERY, True),
                ): bool,
                vol.Optional(
                    CONF_ENTITY_GROUP_GRID,
                    default=current.get(CONF_ENTITY_GROUP_GRID, True),
                ): bool,
                vol.Optional(
                    CONF_ENTITY_GROUP_INVERTER,
                    default=current.get(CONF_ENTITY_GROUP_INVERTER, True),
                ): bool,
                vol.Optional(
                    CONF_ENTITY_GROUP_EPS,
                    default=current.get(CONF_ENTITY_GROUP_EPS, True),
                ): bool,
                vol.Optional(
                    CONF_ENTITY_GROUP_ENERGY,
                    default=current.get(CONF_ENTITY_GROUP_ENERGY, True),
                ): bool,
                vol.Optional(CONF_NIGHT_MODE, default=default_night): vol.In(
                    ["unavailable", "last_known", "zero"]
                ),
            }
        )
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )


def _serial_from_raw(raw: Any) -> Any:
    info = getattr(raw, "information", None)
    if isinstance(info, (list, tuple)) and len(info) >= 3 and info[2] not in (None, ""):
        return info[2]
    sn = getattr(raw, "sn", None)
    if sn not in (None, ""):
        return sn
    if isinstance(raw, dict):
        info = raw.get("Information", raw.get("information"))
        if isinstance(info, (list, tuple)) and len(info) >= 3 and info[2] not in (None, ""):
            return info[2]
        sn = raw.get("sn", raw.get("serial", raw.get("inverterSN")))
        if sn not in (None, ""):
            return sn
    return None


async def _safe_close(client: Any) -> None:
    closer = getattr(client, "async_close", None) or getattr(client, "close", None)
    if callable(closer):
        try:
            result = closer()
            if hasattr(result, "__await__"):
                await result
        except Exception:
            pass
