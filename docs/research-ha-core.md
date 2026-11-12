# Research: Home Assistant core `solax` integration

## 1. Джерело
`homeassistant/components/solax/` у home-assistant/core; залежність `solax==3.2.4` (squishykid/solax).

## 2. Архітектура
- Локальний HTTP, iot_class local_polling.
- Config flow: IP/port/password → discover усіх варіантів → якщо >1, вибір моделі → finalize з serial як unique_id.
- Coordinator: порожній підклас, інтервал hard-coded 30 с.
- Платформа: тільки sensor. Одна сутність на ключ `response_decoder()`.
- Entity name: `f"{manufacturer} {serial} {key}"`; unique id `f"{serial}-{idx}"`.

## 3. Підтримувані моделі (16)
qvolt_hyb_g3_3p, x1, x1_boost, x1_g4_series, x1_hybrid_gen4, x1_lite_lv, x1_mini, x1_mini_v34, x1_smart, x3, x3_evc, x3_hybrid_g4, x3_mic_pro_g2, x3_ultra, x3_v34, x_hybrid.

## 4. Детект моделі
- Entry points `solax.inverter`.
- `build_all_variants` (POST query/body, X-Forwarded-For, GET для XHybrid).
- Discovery паралельно, schema validation (voluptuous); `isinstance` → model name.

## 5. Відомі проблеми
- #135511: X1-Hybrid-G3 (type 3) не підтримується.
- #175394: поломка в HA 2026.7 (sensor state-class validation).
- #145182: нова прошивка dongle вимагає username+password (config flow тільки password).
- #130742: daily/total sensors state class переплутані.
- #120424: запит на налаштовуваний інтервал (не реалізовано).

## 6. Висновки
- Тонка обгортка над `solax` library; уся модель-специфічна логіка там.
- Sensor-only, 30 с hard-coded, без options flow інтервалу.
- Головні больові точки: непідтримані моделі, auth зміни, state-class mismatch, core-регресії.