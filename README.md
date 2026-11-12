# SolaX Power Monitor (community)

[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Home Assistant custom integration for SolaX inverters. Connects an inverter with all its entities, with a choice of connection method (local / cloud / Modbus), many plugin settings, and robust handling of meter, generation, and battery states.

> **Disclaimer:** This is NOT an official product of SolaX Power Co., Ltd. The name "SolaX" is used solely to denote device compatibility. All trademarks belong to their respective owners.

## Features

- Choice of one connection method: **Local** (Pocket WiFi), **Cloud** (SolaX Cloud API), **Modbus** (TCP/RTU).
- All inverter entities: PV strings, battery, grid, inverter, EPS, energy totals.
- Configurable scan interval, timeout, model override, entity groups.
- Energy Dashboard compatible (solar production, grid consumption, feed-in).
- Optimistic startup (loads even when inverter is asleep).
- Night/sleep handling, fault states, charge/discharge detection.

## Installation (HACS)

1. Add this repository as a custom repository in HACS.
2. Install "SolaX Power Monitor (community)".
3. Restart Home Assistant.
4. Add integration via Settings → Devices & Services → Add Integration → SolaX Power Monitor (community).

## Manual installation

Copy `custom_components/solax_ha` to your Home Assistant `custom_components` directory, then restart.

## Auto-discovery

- **DHCP:** Home Assistant automatically detects Pocket WiFi dongles on your network (Espressif hostname/MAC) and offers to configure them with the IP pre-filled.
- **Network scan:** choose the `discover` connection method to scan your local subnet for dongles; pick the found device, then enter the dongle password.
- The inverter model is detected automatically from the API response (`type`).

## Configuration

- **Local:** host (dongle IP), port (default 80), password (dongle registration number). Optional username for newer firmware.
- **Cloud:** token_id, serial number (dongle registration), domain (optional).
- **Modbus:** host, port (default 502), unit_id, TCP/RTU.

## Documentation

See `docs/` for architecture, connection methods, data model, config, state machine, testing, phases, security, CI, contributing, troubleshooting, and research notes.

## Security

No secrets are stored in this repository. Credentials live in HA config entries. See `docs/08-security-and-secrets.md`.

## License

MIT — see [LICENSE](LICENSE).