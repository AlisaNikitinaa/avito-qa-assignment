# Тестовое задание QA — Авито

В [BUGS.md](BUGS.md) описаны расхождения на скриншотах из задания 1 и результаты проверки API. Для задания 2 выбран вариант 2.1. Покрытие описано в [TESTCASES.md](TESTCASES.md).

## Запуск

Нужны Python 3.10+ и доступ к тестовому стенду. Выполняйте команды из папки с `requirements.txt`.

### Windows (PowerShell)

```powershell
py -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
& .\.venv\Scripts\python.exe -m pytest -q --tb=short
```

Команда `source` относится к Bash. В PowerShell команды выше запускают Python из окружения напрямую, поэтому активация не нужна. Если окружение создано под именем `.venv-win`, используйте это имя в пути.

Если зеркало PyPI не отвечает и установка зависимостей завершается таймаутом, повторите установку через официальный PyPI:

```powershell
& .\.venv\Scripts\python.exe -m pip install --index-url https://pypi.org/simple --timeout 30 -r requirements.txt
```

После успешной установки повторите запуск тестов. Ошибка `No module named pytest` означает, что pytest ещё не установлен в выбранном окружении.

### Linux и macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q --tb=short
```

По умолчанию используется `https://qa-internship.avito.com`. Другой адрес можно задать переменной `BASE_URL`. Тесты создают уникальных пользователей, получают Bearer-токены и удаляют созданные объявления. В условиях нет ручки удаления пользователей.

## Результат

Прогон на стенде 26 ноября 2026 г., Python 3.12 — 24 проверки прошли, 6 упали за 25,01 с.

- API-06 — [API-BUG-02](BUGS.md#api-bug-02).
- API-09, две версии статистики — [API-BUG-01](BUGS.md#api-bug-01).
- API-10, три счётчика — [API-BUG-03](BUGS.md#api-bug-03).

Повторный прогон на Windows — 24 проверки прошли, 6 упали за 14,82 с. Воспроизвелись те же расхождения, которые описаны в BUGS.md.
