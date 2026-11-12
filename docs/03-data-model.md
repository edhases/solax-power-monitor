# 03 — Data model & entity catalog

## 1. Принцип

- Один нормалізований dataclass `SolaxData` (усі поля `Optional`, `None` якщо недоступно). Платформи читають типізовані атрибути — жодної логіки індексів у платформах.
- Індексна логіка ізольована в `models.py` (декодери по `type`).
- Детект моделі: `type` (також `Information[1]`) → декодер. Якщо невідомий тип → fallback на generic/legacy + попередження в логах.

## 2. Каталог сутностей

### 2.1 Sensor (енергія/потужність/напруга/струм)

| Ключ | Назва | Одиниця | device_class | state_class |
|---|---|---|---|---|
| `ac_power` | AC Power | W | power | measurement |
| `grid_power` | Grid Power | W | power | measurement |
| `grid_voltage_l1/l2/l3` | Grid Voltage L1/L2/L3 | V | voltage | measurement |
| `grid_current_l1/l2/l3` | Grid Current L1/L2/L3 | A | current | measurement |
| `grid_frequency_l1/l2/l3` | Grid Frequency | Hz | frequency | measurement |
| `pv1..pvN_voltage` | PV String N Voltage | V | voltage | measurement |
| `pv1..pvN_current` | PV String N Current | A | current | measurement |
| `pv1..pvN_power` | PV String N Power | W | power | measurement |
| `pv_power_total` | PV Power Total | W | power | measurement |
| `battery_voltage` | Battery Voltage | V | voltage | measurement |
| `battery_current` | Battery Current | A | current | measurement |
| `battery_power` | Battery Power | W | power | measurement (signed: +charge/-discharge або навпаки — зафіксувати конвенцію) |
| `battery_soc` | Battery SoC | % | battery | measurement |
| `battery_temp` | Battery Temperature | °C | temperature | measurement |
| `battery_remaining_energy` | Battery Remaining Energy | kWh | energy | measurement |
| `feed_in_power` | Feed-in Power | W | power | measurement |
| `feed_in_energy` | Feed-in Energy | kWh | energy | total_increasing |
| `consume_power` | Consumption Power | W | power | measurement |
| `consume_energy` | Consumption Energy | kWh | energy | total_increasing |
| `yield_today` | Yield Today | kWh | energy | total_increasing |
| `yield_total` | Yield Total | kWh | energy | total_increasing |
| `battery_charge_energy_today/total` | Battery Charge Energy | kWh | energy | total_increasing |
| `battery_discharge_energy_today/total` | Battery Discharge Energy | kWh | energy | total_increasing |
| `pv_energy_today/total` | PV Energy | kWh | energy | total_increasing |
| `eps_power_l1/l2/l3` | EPS Power | W | power | measurement |
| `eps_voltage_l1/l2/l3` | EPS Voltage | V | voltage | measurement |
| `eps_current_l1/l2/l3` | EPS Current | A | current | measurement |
| `inverter_temp` / `radiator_temp` | Inverter Temperature | °C | temperature | measurement |
| `run_mode` | Run Mode | — | — | — (sensor зі state mapping або окремий) |

### 2.2 Binary sensor

| Ключ | Назва | Логіка |
|---|---|---|
| `grid_connected` | Grid Connected | run_mode не в EPS/off-grid |
| `battery_charging` | Battery Charging | battery_power > 0 (за конвенцією) |
| `battery_discharging` | Battery Discharging | battery_power < 0 |
| `pv_producing` | PV Producing | pv_power_total > 0 |
| `feed_in_active` | Feeding In | feed_in_power > 0 |
| `consuming_from_grid` | Consuming From Grid | consume_power > 0 / grid_power sign |
| `inverter_fault` | Inverter Fault | status in {103,104} |
| `inverter_sleeping` | Inverter Sleeping | усі Data = 0 |

### 2.3 Select / Number / Switch / Button

| Платформа | Ключ | Призначення |
|---|---|---|
| select | `scan_interval` | 5/10/30/60/300 с (оновлює coordinator без reload) |
| number | `scan_interval_custom` | довільне значення в межах |
| switch | `entity_group_pv` | вмикати/вимикати групу PV-сенсорів (опційно) |
| button | `refresh` | примусове оновлення |
| button | `reconnect` | перепідключення |

(Розширювати за потребою; мінімум — scan_interval select + refresh button.)

### 2.4 Sensor зі state mapping (inverter status)

`inverter_status` — sensor з `device_class=None`, стан = назва режиму (Normal, Sleep, Fault, …). Додатково атрибут `status_code`.

## 3. Energy Dashboard мапінг (обов'язково)

- Solar production: `yield_total` (або `pv_energy_total`) — kWh, total_increasing.
- Grid consumption: `consume_energy` — kWh, total_increasing.
- Return to grid: `feed_in_energy` — kWh, total_increasing.
- Battery: charge/discharge energy (опційно).

## 4. Індекси Data-масиву (коротко)

Детальна таблиця індексів по сімействах — у файлі дослідження `research-data-indices.md`. Основні правила:

1. Детект по `type` (1–24, 100–102).
2. `type >= 8` → сучасний декодер (Data2), `type < 8` → legacy (Data1).
3. Індекси **різні** між X1/X3/Hybrid/String/A1/J1 — окремий декодер на сімейство.
4. Масштабування: напруги /10 або /100, струми /10, потужності цілі (або /10), енергії /10 або /100 (залежить від сімейства).
5. Signed/unsigned: потужності мережі/АКБ/feed-in — signed (two's complement 16/32-bit); енергії — unsigned 32-bit.
6. Валідація довжини `Data`: діапазон 100–310 (не точне значення).
7. Нічний режим: усі значення 0 → `sleeping=True`, сутності unavailable або last-known (опція).

## 5. Cloud vs Local відповідність

Cloud API повертає **іменовані** поля (`acpower`, `powerdc1..4`, `feedinpower`, `soc`, `batPower`, `consumeenergy`, `feedinenergy`, `inverterStatus`, `inverterType`), а не позиційний масив. Логічно ті самі поля → мапінг в єдиний `SolaxData`. Тип інвертора з `inverterType` (1–23).

## 6. Modbus відповідність

Modbus повертає регістри (holding/input). Мапінг регістр→поле за family-специфічним протоколом SolaX (окремі PDF). Реалізація в `api/modbus.py` з таблицею регістрів.

## 7. Правила розширення

- Нова модель: додати декодер у `models.py` + фікстуру + тест. Платформи не змінюються.
- Нова сутність: додати поле в `SolaxData` + entity description у платформі + (опційно) toggle у config.
- Новий метод: реалізувати `api/base.py` + гілка в config flow.