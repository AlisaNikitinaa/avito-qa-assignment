# Тестовое задание QA — Авито

В [BUGS.md](BUGS.md) описаны расхождения на скриншотах из задания 1 и результаты проверки API. Для задания 2 выбран вариант 2.1. Покрытие описано в [TESTCASES.md](TESTCASES.md).

## Запуск

Нужны Python 3.10+ и доступ к стенду. Из корня репозитория:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q --tb=short
```

В Windows PowerShell активируйте окружение командой `.venv\Scripts\Activate.ps1`.

По умолчанию используется `https://qa-internship.avito.com`. Другой адрес можно задать переменной `BASE_URL`. Тесты создают уникальных пользователей и получают Bearer-токены. Фикстура удаляет созданные объявления. В условиях нет ручки удаления пользователей.

## Результат

Прогон на стенде 26 ноября 2026 г., Python 3.12 — 24 проверки прошли, 6 упали за 25,01 с.

- API-06 — [API-BUG-02](BUGS.md#api-bug-02).
- API-09, две версии статистики — [API-BUG-01](BUGS.md#api-bug-01).
- API-10, три счётчика — [API-BUG-03](BUGS.md#api-bug-03).
