# 11 — Troubleshooting

## 1. "Failed to connect" / таймаут
- Перевірити IP dongle, порт (80/8080).
- Додати заголовок `X-Forwarded-For: 5.8.8.8` (нові прошивки).
- Dongle може бути заблокований інтернетом — перевірити.
- Pocket LAN dongles не підтримують локальний API.
- Timeout збільшити до 15 с.

## 2. Інвертор спить (ніч)
- Це нормально: сутності стають unavailable або показують last-known (залежно від опції).
- Інтеграція не падає.

## 3. Rate limit (cloud)
- Зменшити частоту до 5 хв.
- Перевірити token_id (23–24 символи) і serial dongle (10 символів).
- code 1001/1003 → перевірити права акаунта.

## 4. Невірні індекси Data (невідома модель)
- Перевірити `type` у відповіді.
- Додати декодер (див. 10-contributing).
- Логи покажуть fallback warning.

## 5. Помилкові значення (батарея >1000°C тощо)
- Часто через невідповідність індексів або scaled integers.
- Перевірити scaling (/10, /100) і signed/unsigned.
- Відкрити issue з анонімізованим JSON.

## 6. Energy Dashboard не показує дані
- Перевірити state_class (total_increasing) і device_class (energy).
- Перевірити що сенсори мають одиницю kWh.
- Скинути статистику HA якщо були помилки.

## 7. Modbus не підключається
- Перевірити порт 502, unit_id.
- pymodbus встановлений?
- Інвертор не має нативного Modbus TCP — потрібен моніторинг-модуль.

## 8. Діагностика
- Settings → System → Logs.
- Enable debug logging для `custom_components.solax_ha`.
- Diagnostics dump (redacted) — завантажити з UI.

## 9. Часті питання
- **Чи можна одночасно local і cloud?** Ні, один метод на entry; можна створити два entries (різні unique_id? ні, serial той самий → abort). Планується мульти-метод у майбутньому.
- **Чи є запис (write) налаштувань?** Не в v0.1; можливо пізніше через setReg.