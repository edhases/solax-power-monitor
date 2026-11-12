# 06 — Testing strategy

## 1. Інструменти

- `pytest` + `pytest-asyncio` + `pytest-homeassistant-custom-component`.
- `ruff` (lint), `mypy` (опційно, type check).
- Фікстури: реальні JSON-відповіді інверторів у `tests/fixtures/`.
- Покриття: `pytest-cov`.

## 2. Структура тестів

```
tests/
├── conftest.py
├── fixtures/
│   ├── local_type3.json
│   ├── local_type15.json
│   ├── local_type14.json
│   ├── local_type100.json
│   ├── cloud_response.json
│   └── README.md
├── test_models.py          # чисті функції, без HA
├── test_local_client.py    # mock aiohttp
├── test_cloud_client.py
├── test_modbus_client.py
├── test_coordinator.py     # fake client
├── test_config_flow.py     # HA harness
├── test_sensor.py          # entity values
└── test_state_machine.py
```

## 3. Що тестуємо

### 3.1 models.py (найважливіше)
- Кожен декодер: вхідний fixture → очікуваний `SolaxData` (golden test).
- Масштабування, signed/unsigned.
- Невідомий тип → fallback + warning.
- Нічний режим (усі нулі).
- Короткий масив → помилка/None без crash.

### 3.2 Клієнти
- HTTP: mock response, timeout, auth, host-header.
- Cloud: rate limit backoff, code handling.
- Modbus: mock registers.

### 3.3 Coordinator
- Успішне оновлення, помилка, повтор, last_update_success.
- Зміна інтервалу.

### 3.4 Config flow
- Успішне створення, duplicate, invalid auth, no inverter found.
- Модель-вибір при >1 варіанті.

### 3.5 Sensor
- Значення з coordinator data, unavailable при None.
- State class / units.

### 3.6 State machine
- Код→стан таблиця.
- Знаки (charge/discharge, import/export).

## 4. Фікстури (реальні дані)

- Збирати з реальних інверторів (анонімізувати серійні номери).
- Мінімум: type 3, 4, 5, 14, 15, 16, 18, 19, 100, 102 + cloud.
- Зберігати як JSON з метаданими (type, firmware, дата збору).

## 5. CI

```yaml
- ruff check .
- ruff format --check .
- pytest --cov=custom_components/solax_ha --cov-fail-under=70
- gitleaks detect
```

## 6. Локальний запуск

```bash
pip install -r requirements-dev.txt
pytest -q
```

## 7. Golden tests

- `test_models.py` порівнює `SolaxData` з `expected` dict; при зміні декодера — оновлювати golden з review.

## 8. Що НЕ тестуємо

- HA core internals.
- Мережеві запити до реальних інверторів (тільки mock).