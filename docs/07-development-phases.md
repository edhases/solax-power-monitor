# 07 — Development phases

## Фаза 0: Repo init (зараз)
- git init, .gitignore, README, LICENSE, hacs.json, manifest.json, CI, docs, tests skeleton.
- **DoD:** репо на GitHub (public), CI зелений (lint на порожньому), ≥10 md-документів.
- **Виконавець:** build mode (ця сесія).

## Фаза 1: Ядро
- manifest.json фінальний, const.py, entity.py, __init__.py з coordinator, config_flow (вибір методу + local creds), sensor.py skeleton з entity descriptions.
- **DoD:** встановлюється в HA, config flow проходить, coordinator опитує (mock), сутності з'являються.
- **Виконавець:** subagent (core).

## Фаза 2: Локальний клієнт
- api/local.py, models.py (декодери type 3,4,5,14,15,16,18,19,100,102), unit-тести на фікстурах.
- **DoD:** усі декодери проходять golden tests; coverage ≥80% для models.py.

## Фаза 3: Coordinator + sensor
- Реальний coordinator, sensor platform з усіма сутностями, availability, night mode.
- **DoD:** на реальному інверторі (або mock) усі сутності оновлюються; Energy Dashboard мапінг.

## Фаза 4: Options flow + модель-детект
- Повний options flow, auto-detect моделі, entity groups toggle.
- **DoD:** зміна інтервалу без reload; toggle груп працює.

## Фаза 5: Cloud адаптер
- api/cloud.py, backoff, rate limit, probe.
- **DoD:** cloud метод працює, backoff тестується.

## Фаза 6: Modbus адаптер
- api/modbus.py (опційна залежність), таблиця регістрів, RTU/TCP.
- **DoD:** Modbus метод працює на тестовому стенді/mock.

## Фаза 7: Додаткові платформи
- binary_sensor, select, number, switch, button.
- **DoD:** усі платформи завантажуються, сутності працюють.

## Фаза 8: Energy Dashboard + diagnostics
- diagnostics.py з redaction, energy мапінг, документація.
- **DoD:** diagnostics dump без секретів; Energy Dashboard налаштовується.

## Фаза 9: HACS + реліз
- hacs.json фінальний, release workflow, тег v0.1.0, GitHub release.
- **DoD:** HACS встановлює без помилок, реліз опублікований.

## Фаза 10: Документація/спільнота
- README повний, troubleshooting, contributing, переклади (uk, en).
- **DoD:** README достатній для самостійного налаштування.

## Залежності між фазами
0 → 1 → 2 → 3 → 4 → (5,6 паралельно) → 7 → 8 → 9 → 10.

## Виконання через субагентів
- Кожна фаза = окремий субагент (general) з чітким промптом + DoD.
- Перед фазою: перевірити попередню (тести зелені).
- Після фази: code review + оновлення docs.