# 09 — GitHub & CI

## 1. Структура репо
- Гілка `main` — стабільна.
- Feature branches: `feat/...`, `fix/...`.
- PR обов'язкові для змін (навіть для мейнтейнера — для історії).

## 2. Конвенція комітів
Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `chore:`, `refactor:`.

## 3. CI workflow (ci.yml)
```yaml
name: CI
on: [push, pull_request]
jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install ruff
      - run: ruff check .
      - run: ruff format --check .
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements-dev.txt
      - run: pytest --cov=custom_components/solax_ha --cov-fail-under=70
  secrets:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with: { fetch-depth: 0 }
      - uses: gitleaks/gitleaks-action@v2
```

## 4. Release workflow (release.yml)
- Тригер: push тегу `v*`.
- Створює GitHub Release з changelog.
- HACS підхоплює тег.

## 5. HACS
- `hacs.json` з `name`, `render_readme`, `homeassistant` (мін. версія).
- Репо має бути public.
- Додати як custom repository у HACS для тестування.

## 6. Іш'ю/PR шаблони
- Bug report: версія HA, модель інвертора, прошивка, логи (без секретів).
- Feature request: опис, use case.
- PR template: опис, тест-план, чекліст.

## 7. Версіонування
- SemVer. v0.1.0 — перший реліз.
- manifest.json `version` синхронізується з тегом (через release workflow або вручну).