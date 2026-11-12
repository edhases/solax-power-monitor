# 04 — Config & settings

## 1. Config flow (перше налаштування)

### Крок 1: вибір методу
- Select: `local` / `cloud` / `modbus`.
- Disclaimer у тексті кроку.

### Крок 2 (local)
- `host` (IP dongle), `port` (default 80), `password` (serial dongle).
- Опційно: `username` (для нової прошивки з Basic Auth).
- Валідація: один probe-запит; перевірка host-header trick.

### Крок 2 (cloud)
- `token_id`, `serial_number` (dongle registration, 10 символів).
- `domain` (опційно, default global.solaxcloud.com).
- Валідація: GET/POST probe, перевірка code=0.

### Крок 2 (modbus)
- `host`, `port` (default 502), `unit_id` (default 1), `connection_type` (TCP/RTU).
- Для RTU: `serial_port`, `baudrate` (default 19200).
- Валідація: читання одного регістра.

### Крок 3 (спільний): вибір моделі (якщо auto-detect дав >1 варіант)
- Select з виявлених моделей. Якщо одна — пропускається.

### Фіналізація
- Отримати serial інвертора → unique_id = serial.
- Abort якщо вже налаштовано (reauth замість дублювання).
- Створити config entry з `{method, ...creds, model}`.

## 2. Options flow (повторне налаштування)

- `scan_interval`: select 5/10/30/60/300 с або custom number.
- `timeout`: 5–30 с.
- `model_override`: auto або ручний вибір (reload entry).
- `entity_groups`: toggle груп (PV, battery, grid, inverter, EPS, energy totals) — приховує сутності.
- `night_mode`: `unavailable` / `last_known` / `zero`.
- `energy_dashboard`: підтвердження мапінгу (інформаційний).

Зміна інтервалу → оновлює coordinator без reload (якщо можливо). Зміна методу/моделі → reload entry.

## 3. Збереження

- Config entry (HA шифрує at rest).
- Опції в `entry.options`.
- Нічого в YAML (крім Energy Dashboard, який HA зберігає сам).

## 4. Валідація та помилки

- `cannot_connect`, `invalid_auth`, `already_configured`, `no_inverter_found`, `unsupported_model`.
- Показувати зрозумілі повідомлення (strings.json + translations).

## 5. Reauth / Reconfigure

- При зміні пароля/токена — reauth flow (HA стандарт).
- При зміні IP — reconfigure.

## 6. Налаштування за замовчуванням

| Параметр | Значення |
|---|---|
| scan_interval | 10 с (local), 300 с (cloud), 5 с (modbus) |
| timeout | 10 с |
| model | auto |
| entity groups | усі увімкнені |
| night_mode | unavailable |

## 7. UX-принципи

- Мінімум обов'язкових полів.
- Підказки (description) для кожного поля.
- Валідація одразу, зрозумілі помилки.
- Не вимагати ручного YAML.