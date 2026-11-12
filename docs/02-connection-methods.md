# 02 — Connection methods (detailed)

## 1. Comparison

| Метод | Швидкість | Хмара | Стабільність | Складність | Залежності |
|---|---|---|---|---|---|
| Локальний (Pocket WiFi) | 5–10 с | Ні | Середня (dongle може зависати) | Низька | aiohttp (вбудований) |
| Хмарний (SolaX Cloud) | 5 хв | Так | Висока (але rate limits) | Низька | aiohttp |
| Modbus TCP/RTU | 1 с | Ні | Висока | Висока | pymodbus |

Користувач обирає **один** метод при налаштуванні. Перемикання — через options flow (з перезавантаженням entry).

## 2. Локальний метод (Pocket WiFi)

### 2.1 Transport
- HTTP plain, **POST**, порт 80 (іноді 8080).
- URL: `http://<dongle_ip>/` (або `http://<ip>/?optType=ReadRealTimeData`).
- Body (form-encoded): `optType=ReadRealTimeData&pwd=<PASSWORD>`.
- `PASSWORD` = реєстраційний номер dongle (serial Pocket WiFi), **не** серійний інвертора.

### 2.2 Host-header trick (нові прошивки 3.x)
Нові прошивки перевіряють `Host`. Без заголовка — порожня відповідь/таймаут.
```
curl -d "optType=ReadRealTimeData&pwd=SV2AMZFWPT" -X POST http://192.168.1.100 \
     -H "X-Forwarded-For: 5.8.8.8"
```
Надсилати `X-Forwarded-For: 5.8.8.8` (або `Host: 5.8.8.8`).

### 2.3 Відповідь
```json
{
  "sn": "SV********",
  "ver": "3.003.02",
  "type": 15,
  "Data": [2498, 38, 928, ...],
  "Information": [5.000, 15, "H4************", 8, 1.30, 0.00, 1.28, 1.04, 0.00, 1]
}
```
- `sn` — номер dongle; `ver` — прошивка; `type` — код сімейства (див. 03-data-model); `Data` — 100–300 чисел (залежить від моделі/прошивки, 200 на старих, 300 на нових ≥3.003.x); `Information[0]` = номінальна AC-потужність (кВт), `[1]` = тип (дублює `type`), `[2]` = серійний інвертора.
- Інші `optType`: `ReadSetData`, `setReg` (запис регістрів), `BatteryMinEnergy`, `SolarChargerUseMode`, `Password`, `ActivePowerLimit`.
- Відповідь ~1.0–1.5 с. Dongle може зависнути при частих запитах → мінімум 5 с між запитами, серіалізувати discovery.

### 2.4 Помилки
- Транспортні: порожня відповідь/таймаут (рекомендований timeout 4–10 с).
- Нічний режим: усі `Data` = 0 → не помилка, а стан `sleeping`.
- Pocket LAN dongles **не** підтримують локальний API взагалі.

### 2.5 Прошивки
- Pocket WiFi 2.x (~2.033.x): прямий доступ по IP працює з `X-Forwarded-For`.
- Pocket WiFi 3.x (~3.001–3.008.x): суворіша перевірка хоста; заголовок обов'язковий; ~1.2 с затримка.
- Блокування інтернету для dongle вимикає хмару, але локальний API працює (приватність).

### 2.6 Rate limits (практичні)
- Dongle не нав'язує ліміти, але: ≥5 с інтервал; серіалізувати запити (1 с пауза при discovery).

## 3. Хмарний метод (SolaX Cloud)

### 3.1 Endpoints
| Версія | URL | Метод |
|---|---|---|
| Legacy V1 | `https://www.solaxcloud.com:9443/proxy/api/getRealtimeInfo.do?tokenId={tokenId}&sn={sn}` | GET |
| V6.1 | `https://www.solaxcloud.com/proxyApp/proxy/api/getRealtimeInfo.do?tokenId={tokenId}&sn={sn}` | GET |
| V2.0 | `https://<domain>/api/v2/dataAccess/realtimeInfo/get` (домен з Service→API, напр. `global.solaxcloud.com`) | POST, `Content-Type: application/json`, body `{"wifiSn":"<SN>"}`, `tokenId` у **заголовках** |

### 3.2 Автентифікація
- `tokenId` — 23–24 символи з SolaxCloud → Service → API (прив'язаний до акаунту дистриб'ютора/інсталера; секрет!).
- `sn` — 10-символьний реєстраційний номер комунікаційного модуля (Pocket WiFi/LAN/4G), **не** серійний інвертора.

### 3.3 Rate limits
- Офіційний PDF (кінцевий користувач): **< 10 викликів/хв, < 10 000/день**.
- Інсталер/дистриб'ютор: **< 100/хв, < 100 000/день**.
- Сторонні джерела цитують 6/хв, 10 000/день (старіша/суворіша інтерпретація). Рекомендація: триматись ≤ 6/хв для безпеки. При перевищенні — HTTP 429, backoff.

### 3.4 Відповідь
```json
{
  "success": true,
  "exception": "Query success!",
  "result": {
    "inverterSN": "H34******6008",
    "sn": "SR******RM",
    "acpower": 152.0,
    "yieldtoday": 0.2,
    "yieldtotal": 2420.5,
    "feedinpower": 0,
    "feedinenergy": 0,
    "consumeenergy": 0,
    "soc": null,
    "inverterType": "4",
    "inverterStatus": "102",
    "uploadTime": "2024-08-20 09:21:43",
    "batPower": 0,
    "powerdc1": 0, "powerdc2": 0,
    "batStatus": "0"
  },
  "code": 0
}
```
Повний список полів result: inverterSN, sn, acpower, yieldtoday (kWh, 0.1), yieldtotal (kWh, 0.1), feedinpower (W), feedinenergy (kWh, 0.01), consumeenergy (kWh, 0.01), feedinpowerM2, feedinenergyM2, consumeenergyM2, soc (%), peps1/2/3 (W), epsfreq, batPower (W), powerdc1–4 (W), inverterType, inverterStatus, uploadTime, utcDateTime, batStatus (0=норма,1=помилка,2=відключено), timeZone, batcycle.

### 3.5 Коди помилок
| code | Значення |
|---|---|
| 0 | Успіх |
| 1001 | Інтерфейс не авторизований |
| 1002 | Помилка валідації параметрів |
| 1003 | Доступ до даних не авторизований |
| 1004 | Дублікат даних |
| 2001 | Операція не вдалась |
| 2002 | Дані не знайдено |

### 3.6 Коди статусу інвертора
100 Waiting, 101 Self-test, 102 Normal, 103 Recoverable fault, 104 Permanent fault, 105 Firmware upgrade, 106 EPS detection, 107 Off-grid, 108 Self-test (Italian safety), 109 Sleep, 110 Standby, 111 PV wake-up battery, 112 Generator detection, 113 Generator mode, 114 Fast shutdown standby, 130 VPP mode, 131 TOU-Self use, 132 TOU-Charging, 133 TOU-Discharging, 134 TOU-Battery off, 135 TOU-Peak shaving, 136 Normal generator, 137 Battery expansion, 138 On-grid battery heating, 139 EPS battery heating, 141–148 NormalMode variants, 150 Self Use, 151 Force Time Use, 152 Back Up, 153 Feedin Priority, 154 Demand, 155 ConstPower, 160 OpenADR.

### 3.7 Коди типу інвертора (Cloud inverterType)
1 X1-LX, 2 X-Hybrid, 3 X1-Hybrid/Fit, 4 X1-Boost/Air/Mini, 5 X3-Hybrid/Fit, 6 X3-20K/30K, 7 X3-MIC/PRO, 8 X1-Smart, 9 X1-AC, 10 A1-Hybrid, 11 A1-Fit, 12 A1-Grid, 13 J1-ESS, 14 X3-Hybrid-G4, 15 X1-Hybrid-G4, 16 X3-MIC/PRO-G2, 17 X1-SPT, 18 X1-Boost/Mini-G4, 19 A1-Hybrid-G2, 20 A1-AC-G2, 21 A1-SMT-G2, 22 X3-FTH, 23 X3-MGA-G2.

## 4. Modbus метод

### 4.1 Транспорт
- Modbus RTU over RS485 (19200, 8, N, 1, slave addr 1) **або** Modbus TCP через моніторинг-модуль на **порті 502** (unit ID 0x01). Сам інвертор не має нативного Modbus TCP — моніторинг-модуль проксує.
- Функції: 0x03 Read Holding, 0x04 Read Input, 0x06 Write Single, 0x10 Write Multiple. Макс 125 регістрів/читання, 123/запис.
- Big-Endian (Motorola) byte order.

### 4.2 Карта регістрів (energy-storage інвертори)
- Holding 0x0000–0x01FF (модель/конфіг), 0x0300–0x04FF (модель АКБ)
- Input 0x0000–0x017F (реальний час), 0x01DD–0x02ED (паралельна система)
- Write 0x0000–0x02FF (single), 0x0000–0x007B / 0x007C–0x008A / 0x00A0–0x00A8 (multiple, вкл. VPP-контроль)

### 4.3 Ключові real-time input регістри (приклади)
PvPowerSum @50 (U32), OnGridPowerSum @52 (S32), OffGridPowerSum @54, BatPowerSum @56, BatSystemSOC @60, напруги/струми/потужності по фазах, PV1–6 напруга/струм/потужність, battery1/2 напруга/струм/потужність/температура/SOC/SOH, енергії (feed-in/consume/solar/bat charge-discharge today/total), EPS-потужність, дані лічильника.

### 4.4 Конфіг/holding регістри
Серійний інвертора, назва заводу/інвертора, тип, номінальна потужність, версії прошивок (DSP/ARM major/minor/full, версія Modbus-протоколу), RTC, пароль розблокування, вихідний перемикач, паролі користувача/розширені, мова, режим роботи, SOC/мережевий заряд, % експорту, макс. струм АКБ, макс. зарядний/розрядний струм, макс. SOC заряду, вибір лічильника/CT тощо.

### 4.5 Обмеження EEPROM
Регістри з ★ записуються в EEPROM; ~1 000 000 циклів запису сумарно — уникати частих записів.

### 4.6 Цикл опитування
~1 с рекомендовано; зв'язатись з SolaX для актуального Modbus-протоколу під конкретне сімейство (вони публікують окремі PDF: X1/X3 Hybrid G4, X3-MEGA/X3-FORTH, X3-MGA-50K-G2 тощо). Повна CSV-карта регістрів доступна від спільноти (voltrus.id).

### 4.7 Залежності
- `pymodbus` (опційна, встановлюється лише якщо обрано Modbus).
- Обробка big-endian, signed/unsigned конвертації.

## 5. Порівняння з офіційною інтеграцією HA

Офіційна інтеграція `solax` у HA core підтримує обмежений набір моделей і має відомі проблеми зі стабільністю з'єднання (issue #135511). Ця community-інтеграція:
- Підтримує вибір методу (local/cloud/modbus).
- Має динамічний інтервал, оптимістичний старт, модель-детект.
- Дає більше налаштувань і сутностей.

## 6. Рекомендації для реалізації

- Валідувати з'єднання в config flow одним probe-запитом.
- Зберігати метод + креденшіали в config entry.
- Cloud: backoff при 429, експоненційний retry, мін. інтервал 5 хв.
- Local: timeout 10 с, ≥5 с між запитами, header trick.
- Modbus: timeout 5 с, reconnect on failure, optional dep.