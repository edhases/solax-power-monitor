# 00 — Overview: SolaX Power Monitor (community)

## 1. Що це

Неофіційна community-інтеграція Home Assistant для інверторів SolaX. Підключає інвертор і виставляє **усі його сутності** (PV, батарея, мережа, інвертор, енергія) як сенсори/бінарні сенсори/елементи керування, сумісні з Energy Dashboard.

- **Display name:** "SolaX Power Monitor (community)"
- **GitHub repo:** `edhases/solax-power-monitor` (public)
- **HA domain:** `solax_ha`
- **Ліцензія:** MIT

## 2. Цільова аудиторія

- Власники інверторів SolaX (X1/X3, hybrid, string) з Pocket WiFi dongle або cloud-доступом.
- Користувачі Home Assistant, яким не вистачає офіційної інтеграції (обмежені моделі, нестабільне з'єднання, відсутність налаштувань).
- Ті, хто хоче локальний контроль без хмари та з власним інтервалом опитування.

## 3. Головні принципи

1. **Простота налаштування** — config flow з вибором одного методу підключення, мінімум обов'язкових полів.
2. **Багато налаштувань плагіна** — інтервал опитування, таймаут, вибір моделі, вмикання/вимикання категорій сутностей, Energy Dashboard мапінг.
3. **Перевірка станів** — коректна обробка нічного режиму, простою, помилок, заряду/розряду АКБ, імпорту/експорту мережі.
4. **Один запит — усі дані** — DataUpdateCoordinator, одна точка опитування.
5. **Оптимістичний старт** — інтеграція завантажується навіть коли інвертор спить (сутності unavailable, а не помилка).
6. **Без офіційної афіліації** — disclaimer обов'язковий.

## 4. Юридичний disclaimer

> "SolaX Power Monitor (community) is not an official product of SolaX Power Co., Ltd. The name 'SolaX' is used solely to denote device compatibility. All trademarks belong to their respective owners."

Розміщується в README.md, manifest.json (documentation/homepage), і в UI config flow (перший крок).

## 5. Глосарій

| Термін | Значення |
|---|---|
| Pocket WiFi (dongle) | Wi-Fi-модуль, що підключає інвертор до мережі; локальний HTTP API на порту 80 (іноді 8080) |
| Data array | Масив `Data` у відповіді локального API; індекси залежать від моделі інвертора |
| optType | Параметр запиту локального API (`ReadRealTimeData`) |
| Coordinator | HA DataUpdateCoordinator — єдина точка опитування |
| Config entry | Збережена конфігурація інтеграції в HA |
| Options flow | Повторне налаштування без перевстановлення |
| Energy Dashboard | Вбудований дашборд HA для енергії |

## 6. Підтримувані методи підключення (користувач обирає один)

1. **Локальний (Pocket WiFi)** — HTTP POST, без хмари, найшвидше (5–10 с).
2. **Хмарний (SolaX Cloud)** — REST API через token + serial, rate limits 6/хв.
3. **Modbus (TCP/RTU)** — прямий Modbus, найстабільніший, потребує pymodbus.

Деталі: `02-connection-methods.md`.

## 7. Підтримувані сімейства інверторів (план)

- X1 (однофазні): Mini, Air, Boost, Hybrid-G2/G3/G4
- X3 (трифазні): Mega, Hybrid-G2/G3/G4
- String / on-grid, Hybrid (з АКБ)
- (Майбутнє) Micro-inverters, батарейні системи

## 8. Метрики успіху

- Підключення без ручного редагування YAML.
- Усі сутності з'являються автоматично після налаштування.
- Коректна робота Energy Dashboard з 3 сенсорами (grid consumption, feed-in, solar yield).
- Нуль витоків секретів (gitleaks clean).
- Тести проходять у CI.

## 9. Посилання на інші документи

- Архітектура: `01-architecture.md`
- Методи підключення: `02-connection-methods.md`
- Модель даних/сутності: `03-data-model.md`
- Конфігурація: `04-config-and-settings.md`
- Стани: `05-state-machine.md`
- Тести: `06-testing-strategy.md`
- Фази: `07-development-phases.md`
- Безпека: `08-security-and-secrets.md`
- GitHub/CI: `09-github-and-ci.md`
- Внесок: `10-contributing.md`
- Проблеми: `11-troubleshooting.md`