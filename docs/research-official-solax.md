# Research: Official SolaX API & documentation

(Скорочений звіт субагента; повний текст збережено в сесії. Нижче — ключові висновки.)

## 1. Local API (Pocket WiFi)
- HTTP POST, порт 80, body `optType=ReadRealTimeData&pwd=<dongle serial>`.
- Відповідь: `{sn, ver, type, Data:[...], Information:[...]}`.
- Host-header trick: `X-Forwarded-For: 5.8.8.8` для прошивок 3.x.
- Data length 100–300 (200 старі, 300 нові ≥3.003.x).
- Rate: ≥5 с між запитами; dongle може зависнути.
- Pocket LAN dongles не підтримують локальний API.

## 2. Cloud API
- Legacy V1: `https://www.solaxcloud.com:9443/proxy/api/getRealtimeInfo.do?tokenId=&sn=`
- V6.1: `https://www.solaxcloud.com/proxyApp/proxy/api/getRealtimeInfo.do?...`
- V2.0: POST `https://<domain>/api/v2/dataAccess/realtimeInfo/get`, tokenId у заголовках.
- Rate limits: <10/хв, <10 000/день (енд-юзер); <100/хв, <100 000/день (інсталер).
- Коди помилок: 0 успіх, 1001–1004, 2001, 2002.
- Коди статусу інвертора: 100–114, 130–160.
- Коди типу інвертора: 1–23.

## 3. Modbus
- RTU (19200,8,N,1) або TCP порт 502, unit ID 0x01.
- Функції 0x03/0x04/0x06/0x10, max 125/123 регістрів.
- Big-Endian. EEPROM ~1 000 000 циклів.
- Кожне сімейство має окремий PDF від SolaX.

## 4. Джерела
- nazar-pc/solax-local-api-docs
- squishykid/solax
- SolaXCloud User API PDFs (V6.1, V7.1, V2.0)
- SolaX Help Center (rate limits)
- SolaX Modbus protocol PDFs
- community.home-assistant.io threads