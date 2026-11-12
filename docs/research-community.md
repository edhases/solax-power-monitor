# Research: Community SolaX solutions

## 1. GeroComp/Solax-local-API (HACS)
- Локальний HTTP, DHCP-автовиявлення (Espressif hostnames + /login перевірка).
- ~50 сенсорів, динамічний інтервал 6 с–5 хв (select entity), оптимістичний старт.
- Парсинг: `SENSOR_TYPES` таблиця [name, unit, device_class, index, coefficient, dtype], dtype 0–9.
- Hybrid G4 only (type 14/15). Чеська мова.

## 2. darrylcauldwell/ha-solax (HACS)
- aiosolax wrapper, config+options flow, 21 сенсорів, Basic Auth для нової прошивки.
- Інтервал 10–300 с через options (reload entry).

## 3. squishykid/solax (library)
- Основа офіційної інтеграції. 16 варіантів інверторів.
- Валідація schema (voluptuous), response_decoder з конвертерами (div10, div100, to_signed, pack_u16).

## 4. sirjackal/solax-inverter-api-proxy (Node.js)
- Проксі локального API → нормалізований JSON. X3-Hybrid-G4 only. Stale (2022).

## 5. samatild/SolaxAPItoHomeAssistantIntegration (Docker)
- Cloud API → Docker → JSON файл → HA REST sensors. Backoff rate limits. Ручний YAML.

## Порівняння
| Аспект | GeroComp | darrylcauldwell | squishykid | sirjackal | samatild |
|---|---|---|---|---|---|
| Transport | Local HTTP | Local HTTP | Local HTTP | Local proxy | Cloud |
| Discovery | DHCP | None | Auto-detect | None | None |
| Entities | ~50 | 21 | Core | None | None (manual) |
| Dynamic interval | Yes | Options | Fixed | N/A | Backoff |
| Inverter support | Hybrid G4 | aiosolax | 16 variants | X3-G4 | Cloud |

## Висновки для нашого проєкту
- Взяти найкраще: GeroComp (динамічний інтервал, discovery, багато сутностей) + darrylcauldwell (options flow, Basic Auth) + squishykid (багато моделей, schema validation).
- Додати: вибір методу (local/cloud/modbus), redaction, gitleaks, повна документація.