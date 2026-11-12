# Research: Data array indices & inverter models

## 1. Детект моделі
- `type` (також `Information[1]`) ідентифікує сімейство.
- `type >= 8` → сучасний декодер (Data2), `type < 8` → legacy (Data1).
- Information layout різниться: modern `[1]=type,[2]=serial,[4]=dsp,[6]=arm,[9]=transport,[10]=dongleMod,[11]=dongleWork]`; legacy `[1]=type,[2]=?,[3]=serial,[5]=dsp,[7]=arm`.
- Індекси **не стабільні** між сімействами — окремий декодер на кожне.

## 2. Коди типу
1 X1-LX, 2 X-Hybrid, 3 X1-Hybrid/Fit, 4 X1-Boost/Air/Mini, 5 X3-Hybrid/Fit, 6 X3-20K/30K, 7 X3-MIC/PRO, 8 X1-Smart, 9 X1-AC, 10 A1-Hybrid, 11 A1-Fit, 12 A1-Grid, 13 J1-ESS, 14 X3-Hybrid-G4, 15 X1-Hybrid-G4, 16 X3-MIC/PRO-G2, 17 X1-SPT, 18 X1-Boost/Mini-G4, 19 A1-HYB-G2, 20 A1-AC-G2, 21 A1-SMT-G2, 22 X3-FTH, 23 X3-MGA-G2, 100/101 X3-big (string), 102 X1-Hybrid-LV.

## 3. Повні таблиці індексів
Детальні таблиці індексів для кожного сімейства (X1-Hybrid G4, X3-Hybrid G4/G5, X1/X3-Hybrid G1–G3, string/MIC, X1-AC, A1-Hybrid, J1-ESS, A1-Hybrid G2, big string, X1-Hybrid LV, X1-Boost/Air/Mini) — у файлі `03-data-model.md` (розділ 4) та в звіті субагента.

## 4. Допоміжні функції
- `read16BitSigned`: n≥32768 → n−65536.
- `read32BitUnsigned(a,b) = a + 65536*b`.
- `read32BitSigned(a,b)` зі знаком старшого слова.
- Масштабування: /10, /100 залежно від поля/сімейства.
- Енергії: /10 або /100.

## 5. Коди статусу
100 Waiting, 101 Self-test, 102 Normal, 103 Recoverable fault, 104 Permanent fault, 105 Firmware upgrade, 106 EPS check, 107 Off-grid, 108 Self-test (Italian), 109 Sleep, 110 Standby, 111 PV wake-up battery, 112 Gen check, 113 Gen run, 114 Fast shutdown standby, 130–160 VPP/TOU/Gen.

## 6. Практичні правила
1. Детект по `type`.
2. Валідація довжини Data: 100–310.
3. Нічний режим: усі нулі → sleeping.
4. Опційні індекси: 0/null → пропустити.
5. EPS override: у EPS-режимі (run mode 7) grid power = EPS power.