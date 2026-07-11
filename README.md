# АВТОСНАБ Test Task

Асинхронный FastAPI-сервис, который принимает кадастровый номер, широту и долготу, отправляет данные на эмулируемый внешний сервер, сохраняет запрос и итог его обработки в PostgreSQL и предоставляет историю запросов.

## Что реализовано

- `POST /query` — приём и обработка запроса;
- `GET /ping` — проверка запуска API;
- `GET /health` — проверка API и PostgreSQL;
- `GET /history` — история с фильтрами и пагинацией;
- `GET /history/{request_id}` — отдельная запись истории;
- `GET/POST /result` — встроенный совместимый эмулятор;
- отдельный Docker-сервис `emulator`, закрывающий дополнительное задание №1;
- асинхронные HTTP-запросы через `httpx.AsyncClient`;
- PostgreSQL и прямые асинхронные запросы через `asyncpg`;
- raw SQL migrations;
- сохранение успешных ответов, тайм-аутов и ошибок;
- Pydantic-валидация;
- Swagger и ReDoc;
- unit/API tests и GitHub Actions.

## Стек

- Python 3.11
- FastAPI
- PostgreSQL 16
- asyncpg
- httpx
- Pydantic Settings
- Docker / Docker Compose
- Pytest
- Raw SQL migrations

## Архитектура

```text
Client
  -> FastAPI /query
      -> INSERT status=processing
      -> ExternalServiceClient
          -> separate emulator service /result
      -> UPDATE completed / timeout / failed
      -> PostgreSQL
```

Запись создаётся **до** вызова внешнего сервиса. Поэтому попытка не пропадает из истории даже при тайм-ауте или сетевой ошибке.

## Запуск через Docker

```bash
docker compose up --build
```

После запуска:

- API: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- Emulator Swagger: `http://localhost:8001/docs`

Миграции применяются автоматически при старте API.

## Быстрая проверка

### Ping

```bash
curl http://localhost:8000/ping
```

### Отправка запроса

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "cadastral_number": "66:41:0101001:123",
    "latitude": 56.8389,
    "longitude": 60.6057
  }'
```

Успешный ответ:

```json
{
  "id": 1,
  "cadastral_number": "66:41:0101001:123",
  "latitude": 56.8389,
  "longitude": 60.6057,
  "status": "completed",
  "result": true,
  "external_response": {"result": true},
  "error_message": null,
  "created_at": "2026-07-11T12:00:00Z",
  "completed_at": "2026-07-11T12:00:04Z",
  "duration_ms": 4012
}
```

При тайм-ауте API возвращает `504`, но запись сохраняется в PostgreSQL со статусом `timeout`. При другой ожидаемой ошибке внешнего сервера возвращается `502`, а запись получает статус `failed`.

## История

Вся история:

```bash
curl "http://localhost:8000/history"
```

Фильтр по кадастровому номеру:

```bash
curl "http://localhost:8000/history?cadastral_number=66:41:0101001:123"
```

Фильтр по статусу и пагинация:

```bash
curl "http://localhost:8000/history?status=completed&limit=20&offset=0"
```

Статусы:

- `processing`
- `completed`
- `timeout`
- `failed`

## Эмулятор внешнего сервера

Docker Compose запускает отдельный сервис `emulator` на порту `8001`. Основной API обращается к нему по внутреннему адресу:

```text
http://emulator:8001/result
```

Задержка регулируется переменными:

```env
EMULATOR_MIN_DELAY_SECONDS=0
EMULATOR_MAX_DELAY_SECONDS=60
```

Для быстрой локальной демонстрации можно установить максимум `5`, а в тестах используется задержка `0`.

## Переменные окружения

Скопируйте пример:

```bash
cp .env.example .env
```

Основные параметры:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autosnab_db
EXTERNAL_SERVER_URL=http://127.0.0.1:8001/result
EXTERNAL_TIMEOUT_SECONDS=65
EMULATOR_MIN_DELAY_SECONDS=0
EMULATOR_MAX_DELAY_SECONDS=60
```

## Миграции

Миграции находятся в `migrations/` и применяются в алфавитном порядке. Выполненные файлы фиксируются в `schema_migrations`, поэтому повторно не запускаются.

`002_add_request_status_and_errors.sql` безопасно обновляет существующую таблицу из первой версии проекта и сохраняет ранее созданные записи.

## Тесты

Локально:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pytest
```

С покрытием:

```bash
pytest --cov=app --cov=emulator --cov-report=term-missing
```

Через Docker:

```bash
docker compose run --rm app pytest
```

Тесты проверяют:

- `/ping`;
- валидацию кадастрового номера и координат;
- успешные результаты `true` и `false`;
- сохранение timeout и failed;
- фильтрацию и пагинацию истории;
- строгую проверку ответа внешнего сервера;
- работу отдельного emulator endpoint.

## Остановка

```bash
docker compose down
```

Удаление данных PostgreSQL:

```bash
docker compose down -v
```

## Принятые решения по неоднозначностям ТЗ

1. `/query` принимает кадастровый номер, широту и долготу, поскольку эти три значения перечислены в основном описании задания.
2. `/result` принимает `POST` с теми же данными. Для совместимости также оставлен `GET`.
3. Внешний timeout равен 65 секундам, потому что эмулятор может обрабатывать запрос до 60 секунд.
4. Ошибочные запросы сохраняются в истории так же, как успешные.
5. Авторизация и админ-панель не добавлены в основное ядро, чтобы не усложнять проверку обязательной функциональности. Они могут быть реализованы отдельным следующим этапом.

## Smoke test

После запуска Docker Compose можно проверить основной E2E-сценарий одной командой.

Windows PowerShell:

```powershell
./scripts/smoke_test.ps1
```

Linux/macOS:

```bash
./scripts/smoke_test.sh
```
