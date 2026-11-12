# 05 — State machine

## 1. Коди статусу інвертора (inverterStatus / run mode + 100)

| Код | Назва | Поведінка HA |
|---|---|---|
| 100 | Waiting | unavailable? ні; стан "Waiting" |
| 101 | Self-test | стан "Self-test" |
| 102 | Normal | нормальна робота |
| 103 | Recoverable fault | binary_sensor.inverter_fault = on, стан "Fault" |
| 104 | Permanent fault | binary_sensor.inverter_fault = on, стан "Permanent Fault" |
| 105 | Firmware upgrade | стан "Update" |
| 106 | EPS check | перехідний |
| 107 | EPS / Off-grid | binary_sensor.grid_connected = off |
| 108 | Self-test (Italian safety) | — |
| 109 | Sleep / Idle | binary_sensor.inverter_sleeping = on |
| 110 | Standby | стан "Standby" |
| 111 | PV wake-up battery | — |
| 112 | Generator check | — |
| 113 | Generator mode | — |
| 114 | Fast shutdown standby | — |
| 130–160 | VPP/TOU/Gen modes | стан текстом |

## 2. Нічний режим (sleeping)

- Усі `Data` = 0 (або Data відсутній) → `sleeping=True`.
- Сутності: за опцією `night_mode`: `unavailable` (default) / `last_known` / `zero`.
- Інтеграція не падає (оптимістичний старт).

## 3. Заряд/розряд АКБ

Конвенція: `battery_power > 0` → заряд (charging), `< 0` → розряд (discharging). (Зафіксувати в const і документувати; деякі моделі інвертують знак — нормалізувати в декодері.)

- `binary_sensor.battery_charging`: battery_power > threshold (напр. > 10 W).
- `binary_sensor.battery_discharging`: battery_power < -threshold.
- `battery_soc` → %.

## 4. Мережа: імпорт/експорт

- `grid_power > 0` → імпорт з мережі (consumption), `< 0` → експорт (feed-in). Або навпаки залежно від конвенції моделі — нормалізувати.
- `feed_in_power` → W експорту (≥0).
- `consume_power` → W імпорту (≥0).
- `binary_sensor.feed_in_active`: feed_in_power > threshold.
- `binary_sensor.consuming_from_grid`: consume_power > threshold.

## 5. Перехідні стани

- EPS check (106) → EPS mode (107): binary grid_connected перемикається.
- Generator check (112) → generator mode (113).
- Firmware upgrade (105): сутності unavailable, стан "Update".

## 6. Помилки

- HTTP timeout / порожня відповідь → `SolaxConnectionError` → coordinator `last_update_success=False` → сутності unavailable.
- Auth error → `SolaxAuthError` → reauth flow.
- Rate limit (cloud) → `SolaxRateLimitError` → backoff.
- Parse error → `SolaxParseError` → лог warning, сутності unavailable (не падіння).

## 7. Cloud backoff

- При 429 / code 1001: експоненційний retry (1, 2, 4, 8 хв), макс 30 хв.
- Логування без секретів.

## 8. Валідація станів (тести)

- Таблиця переходів код→стан покривається unit-тестами.
- Тести на знаки потужностей (charge/discharge, import/export).
- Тести нічного режиму.