# 08 — Security & secrets

## 1. .gitignore (обов'язково)
```
.env
*.key
secrets.yaml
__pycache__/
*.pyc
.pytest_cache/
.venv/
dist/
build/
*.egg-info/
.idea/
.vscode/
```

## 2. .env.example (єдиний файл з секретами-плейсхолдерами)
```
SOLAX_HOST=192.168.1.100
SOLAX_PASSWORD=your_dongle_serial
SOLAX_TOKEN_ID=your_token_id
```

## 3. Правила коду
- Ніяких креденшіалів у коді, тестах, фікстурах.
- Серійні номери в фікстурах анонімізувати (замінювати на `REDACTED`).
- Логи: не виводити паролі/токени; використовувати redaction у diagnostics.

## 4. diagnostics.py
- HA стандартний diagnostics; redact поля: password, token_id, serial (частково), host (опційно).
- Використовувати `async_redact_data` з HA.

## 5. gitleaks
- У CI (`.github/workflows/ci.yml`): `gitleaks detect --source . --verbose`.
- Pre-commit хук — ні (щоб не дратувати локально), але рекомендувати розробникам.

## 6. GitHub Secret Scanning
- Увімкнути в налаштуваннях репо (Settings → Security → Secret scanning).
- Push protection — увімкнути.

## 7. Відповідь на витік
- Негайно ротувати креденшіал (змінити пароль dongle / token).
- `git filter-repo` або BFG для видалення з історії.
- Force-push (з підтвердженням).
- Повідомити користувачів.

## 8. Залежності
- Мінімізувати залежності (тільки pymodbus опційно).
- Періодично оновлювати, перевіряти CVE.

## 9. Безпека cloud-токена
- token_id прив'язаний до акаунту дистриб'ютора/інсталера — не публікувати.
- Документувати ротацію.