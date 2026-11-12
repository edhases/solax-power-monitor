# 01 — Architecture

## 1. High-level

```
┌──────────────────────────────────────────────────────────────┐
│  Home Assistant                                              │
│  ┌────────────┐   ┌──────────────┐   ┌──────────────────┐    │
│  │ config_flow│──▶│ __init__.py  │──▶│ DataUpdateCoord. │    │
│  │ options    │   │ setup/unload │   │ (single poll)    │    │
│  └────────────┘   └──────┬───────┘   └────────┬─────────┘    │
│                          │                   │              │
│              ┌───────────┴──────┐            │              │
│              ▼                  ▼            ▼              │
│        ┌──────────┐     ┌────────────┐  ┌──────────────┐    │
│        │ platforms│     │ api/       │  │ entity base  │    │
│        │ sensor,  │◀────│ base.py    │  │ device info  │    │
│        │ binary,  │     │ local.py   │  └──────────────┘    │
│        │ select,  │     │ cloud.py   │                      │
│        │ number,  │     │ modbus.py  │                      │
│        │ switch,  │     └─────┬──────┘                      │
│        │ button   │           │                             │
│        └──────────┘           ▼                             │
│                         Inverter / Cloud / Modbus           │
└──────────────────────────────────────────────────────────────┘
```

## 2. Directory layout (runtime)

```
custom_components/solax_ha/
├── __init__.py          # setup, unload, coordinator, services
├── manifest.json
├── const.py             # constants, connection types, status maps, entity defs
├── config_flow.py       # user + options flow
├── coordinator.py       # DataUpdateCoordinator subclass
├── entity.py            # SolaxEntity base (device info, availability)
├── sensor.py
├── binary_sensor.py
├── select.py
├── number.py
├── switch.py
├── button.py
├── api/
│   ├── __init__.py
│   ├── base.py          # abstract SolaxClient protocol
│   ├── local.py         # Pocket WiFi HTTP
│   ├── cloud.py         # SolaX Cloud REST
│   └── modbus.py        # pymodbus TCP/RTU
├── models.py            # inverter type → decoder mapping
├── diagnostics.py       # redacted diagnostics dump
├── services.yaml
├── strings.json
└── translations/{en,uk,...}.json
```

## 3. Module responsibilities

| Module | Responsibility |
|---|---|
| `const.py` | Domain, connection type enum, status-code maps, entity key constants, defaults (scan interval 10s, timeout 10s) |
| `api/base.py` | Abstract interface: `async_get_data() -> SolaxData`, `async_validate()`, `close()` |
| `api/local.py` | HTTP POST to dongle, header trick, JSON parse, Data array, returns raw dict |
| `api/cloud.py` | Cloud REST, rate-limit/backoff, token+sn |
| `api/modbus.py` | pymodbus read holding/input registers, decode |
| `models.py` | `type` code → decoder class; per-model index extraction into normalized `SolaxData` |
| `coordinator.py` | Polls client, classifies states, exposes `data`, handles errors, optimistic start |
| `entity.py` | Base entity: device info (manufacturer/model/serial), availability based on coordinator success |
| `config_flow.py` | Step 1 method choice; method-specific credentials; validation; options flow |
| `sensor.py` etc. | Platform setup, entity descriptions, value extraction from normalized data |

## 4. Data flow

1. Config entry created → `__init__.async_setup_entry` creates client (by method) + coordinator.
2. Coordinator first refresh (optimistic: errors don't abort setup; entities become unavailable).
3. Coordinator polls every `scan_interval` → client fetches raw → `models` decodes into `SolaxData` dataclass.
4. Platforms read `coordinator.data` and update entity states.
5. Options change → coordinator interval updated without reload (where possible); method change → reload entry.

## 5. Normalized data model (`SolaxData`)

A single dataclass holding all normalized fields with `None` for unavailable. Platforms read typed attributes; no index logic in platforms. This isolates model-specific indexing in `models.py`.

Fields (illustrative): `grid_voltage`, `grid_current`, `grid_power`, `grid_frequency`, `pv1_voltage`, `pv1_current`, `pv1_power`, ..., `battery_voltage`, `battery_current`, `battery_power`, `battery_soc`, `battery_temp`, `battery_status`, `feed_in_power`, `feed_in_energy`, `consume_power`/`consume_energy`, `yield_today`, `yield_total`, `inverter_status`, `inverter_type`, `eps_power`, `run_mode`, `upload_time`, `raw` (optional, for diagnostics).

## 6. Error & availability strategy

- Client raises typed exceptions: `SolaxConnectionError`, `SolaxAuthError`, `SolaxRateLimitError`, `SolaxParseError`.
- Coordinator catches and sets `last_update_success=False`; entities become unavailable (not unknown).
- Night mode: if Data all zeros → mark `sleeping=True`, entities show last known or unavailable per option.
- Cloud rate limit → backoff with exponential retry, log warning.

## 7. Concurrency & locking

- One coordinator per config entry; no parallel polling.
- Local dongle: serialize requests; ≥5 s gap; timeout 10 s.
- Discovery (config flow validation) uses a single probe request.

## 8. Testing boundaries

- `api/*` tested with mocked HTTP/Modbus.
- `models.py` tested with real JSON fixtures (pure functions, no HA).
- `coordinator.py` tested with fake client.
- `config_flow.py` tested via HA test harness.

## 9. Extension points

- Adding a new inverter model: add decoder in `models.py` + fixture + test. No platform changes.
- Adding a new connection method: implement `api/base.py` interface + config flow branch.
- Adding a new entity: add to `entity descriptions` in platform + `SolaxData` field.