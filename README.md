# АВТОСНАБ Test Task

Асинхронный сервис на FastAPI, который принимает кадастровый номер, широту и долготу, отправляет данные на эмулируемый внешний сервер, сохраняет запрос и результат его обработки в PostgreSQL и предоставляет API для просмотра истории.

Запрос сохраняется в базе данных **до** обращения к внешнему сервису. Благодаря этому в истории остаются не только успешные операции, но и тайм-ауты или ошибки соединения.

## Соответствие тестовому заданию

### Обязательная часть

* Python 3.9+;
* FastAPI с асинхронными endpoint;
* PostgreSQL;
* прямые асинхронные запросы через `asyncpg`;
* raw SQL migrations;
* Dockerfile;
* Docker Compose;
* Pytest;
* `/query`;
* `/ping`;
* `/history`;
* `/result`;
* сохранение запроса и ответа внешнего сервера;
* README с инструкцией запуска.

### Дополнительные возможности

* отдельный Docker-сервис `emulator` — дополнительное задание №1;
* проверка доступности PostgreSQL через `/health`;
* фильтрация истории;
* пагинация;
* получение отдельной записи истории;
* сохранение ошибок и тайм-аутов;
* автоматические тесты;
* GitHub Actions;
* Swagger и ReDoc;
* PowerShell и Bash smoke tests.

Регистрация, авторизация и админ-панель в текущей версии не реализованы. Они не входят в обязательную часть задания.

## Стек

* Python 3.11
* FastAPI
* Uvicorn
* PostgreSQL 16
* asyncpg
* httpx
* Pydantic
* Pydantic Settings
* Docker
* Docker Compose
* Pytest
* pytest-asyncio
* Raw SQL migrations
* GitHub Actions

## Архитектура

```text
Client
  |
  v
FastAPI: POST /query
  |
  +--> PostgreSQL: INSERT status=processing
  |
  +--> ExternalServiceClient
  |       |
  |       v
  |    Emulator: POST /result
  |
  +--> PostgreSQL:
          UPDATE status=completed
          UPDATE status=timeout
          UPDATE status=failed
```

Основные компоненты:

```text
app/
├── config.py             # настройки приложения
├── database.py           # пул соединений и запуск миграций
├── crud.py               # запросы к PostgreSQL
├── external_client.py    # асинхронный HTTP-клиент
├── services.py           # бизнес-логика обработки запроса
├── schemas.py            # Pydantic-схемы
└── main.py               # FastAPI-приложение и endpoint

emulator/
└── main.py               # отдельный эмулятор внешнего сервера

migrations/
├── 001_create_requests_history.sql
└── 002_add_request_status_and_errors.sql

scripts/
├── smoke_test.ps1
└── smoke_test.sh

tests/
├── test_api.py
├── test_emulator.py
└── test_external_client.py
```

## API

| Метод  | Endpoint                | Назначение                                 |
| ------ | ----------------------- | ------------------------------------------ |
| `GET`  | `/ping`                 | Проверка запуска основного API             |
| `GET`  | `/health`               | Проверка API и подключения к PostgreSQL    |
| `POST` | `/query`                | Отправка запроса по кадастровому номеру    |
| `GET`  | `/history`              | Получение истории с фильтрами и пагинацией |
| `GET`  | `/history/{request_id}` | Получение одной записи истории             |
| `POST` | `/result`               | Основной endpoint эмулятора                |
| `GET`  | `/result`               | Упрощённый совместимый вызов эмулятора     |

## Быстрый запуск через Docker

### Требования

Перед запуском должны быть установлены:

* Docker;
* Docker Compose;
* запущенный Docker Engine или Docker Desktop.

### Запуск

```bash
docker compose up --build
```

Для запуска в фоновом режиме:

```bash
docker compose up --build -d
```

Docker Compose запускает три контейнера:

* `autosnab_app`;
* `autosnab_emulator`;
* `autosnab_postgres`.

Миграции применяются автоматически при запуске основного API.

### Адреса после запуска

* API: `http://localhost:8000`
* Swagger: `http://localhost:8000/docs`
* ReDoc: `http://localhost:8000/redoc`
* Emulator API: `http://localhost:8001`
* Emulator Swagger: `http://localhost:8001/docs`

Проверка состояния контейнеров:

```bash
docker compose ps
```

## Проверка API

### Ping

```bash
curl http://localhost:8000/ping
```

Ответ:

```json
{
  "status": "ok"
}
```

### Health check

```bash
curl http://localhost:8000/health
```

Endpoint проверяет не только запуск FastAPI, но и доступность PostgreSQL.

## Отправка запроса

```bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{
    "cadastral_number": "66:41:0101001:123",
    "latitude": 56.8389,
    "longitude": 60.6057
  }'
```

Эмулятор может обрабатывать запрос до 60 секунд. Это ожидаемое поведение, а не зависание приложения.

Пример успешного ответа:

```json
{
  "id": 1,
  "cadastral_number": "66:41:0101001:123",
  "latitude": 56.8389,
  "longitude": 60.6057,
  "status": "completed",
  "result": true,
  "external_response": {
    "result": true
  },
  "error_message": null,
  "created_at": "2026-07-11T12:00:00Z",
  "completed_at": "2026-07-11T12:00:04Z",
  "duration_ms": 4012
}
```

Значения `true` и `false` являются корректными успешными ответами внешнего сервера.

## Обработка ошибок

Запрос сначала сохраняется со статусом:

```text
processing
```

После обращения к внешнему сервису запись получает один из статусов:

* `completed` — внешний сервер успешно вернул `true` или `false`;
* `timeout` — внешний сервер не ответил за установленное время;
* `failed` — ошибка соединения, HTTP-ошибка или некорректный ответ.

При тайм-ауте API возвращает:

```text
504 Gateway Timeout
```

При другой ожидаемой ошибке внешнего сервиса:

```text
502 Bad Gateway
```

При этом запись не удаляется и остаётся доступной через `/history`.

## История запросов

### Вся история

```bash
curl "http://localhost:8000/history"
```

### Фильтр по кадастровому номеру

```bash
curl "http://localhost:8000/history?cadastral_number=66:41:0101001:123"
```

### Фильтр по статусу

```bash
curl "http://localhost:8000/history?status=completed"
```

### Пагинация

```bash
curl "http://localhost:8000/history?limit=20&offset=0"
```

### Комбинированный запрос

```bash
curl "http://localhost:8000/history?status=completed&limit=20&offset=0"
```

### Получение одной записи

```bash
curl "http://localhost:8000/history/1"
```

## Эмулятор внешнего сервера

В дополнение к встроенному `/result` Docker Compose запускает отдельный сервис `emulator`.

Основной API обращается к нему по внутреннему Docker-адресу:

```text
http://emulator:8001/result
```

Эмулятор:

1. получает кадастровый номер и координаты;
2. асинхронно ожидает случайное время;
3. возвращает случайное значение `true` или `false`.

Задержка регулируется переменными окружения:

```env
EMULATOR_MIN_DELAY_SECONDS=0
EMULATOR_MAX_DELAY_SECONDS=60
```

Для быстрой локальной демонстрации максимальную задержку можно временно уменьшить до `5`.

В автоматических тестах используется задержка `0`, поэтому тесты не ожидают реальных 60 секунд.

## Переменные окружения

Пример настроек находится в `.env.example`.

### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

### Linux и macOS

```bash
cp .env.example .env
```

### Запуск внутри Docker Compose

Внутри Docker используются имена сервисов:

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/autosnab_db
EXTERNAL_SERVER_URL=http://emulator:8001/result
EXTERNAL_TIMEOUT_SECONDS=65
EMULATOR_MIN_DELAY_SECONDS=0
EMULATOR_MAX_DELAY_SECONDS=60
```

### Локальный запуск вне Docker

При запуске API непосредственно на компьютере используются локальные адреса:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autosnab_db
EXTERNAL_SERVER_URL=http://127.0.0.1:8001/result
EXTERNAL_TIMEOUT_SECONDS=65
EMULATOR_MIN_DELAY_SECONDS=0
EMULATOR_MAX_DELAY_SECONDS=60
```

Тайм-аут основного API установлен в 65 секунд, потому что эмулятор может обрабатывать запрос до 60 секунд.

## Миграции

Миграции находятся в каталоге:

```text
migrations/
```

Они применяются автоматически в алфавитном порядке.

Информация о выполненных миграциях сохраняется в таблице:

```text
schema_migrations
```

Поэтому уже применённые SQL-файлы повторно не запускаются.

Миграция:

```text
002_add_request_status_and_errors.sql
```

обновляет существующую таблицу первой версии проекта и сохраняет ранее созданные записи.

Она добавляет:

* статус обработки;
* возможность хранить `NULL` до получения результата;
* ответ внешнего сервера;
* сообщение об ошибке;
* время завершения;
* длительность обработки.

## Локальный запуск тестов

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pytest -v
```

### Linux и macOS

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
pytest -v
```

Ожидаемый результат:

```text
19 passed
```

## Покрытие тестами

```bash
pytest --cov=app --cov=emulator --cov-report=term-missing
```

Тесты проверяют:

* `/ping`;
* валидацию кадастрового номера;
* валидацию широты и долготы;
* успешный результат `true`;
* успешный результат `false`;
* сохранение запроса;
* сохранение статуса `timeout`;
* сохранение статуса `failed`;
* фильтрацию истории;
* пагинацию;
* получение отдельной записи;
* строгую проверку ответа внешнего сервера;
* некорректный JSON;
* неправильный тип поля `result`;
* работу отдельного emulator endpoint.

## Тесты внутри Docker

При уже запущенных контейнерах:

```bash
docker compose exec app pytest -v
```

Одноразовый запуск тестового контейнера:

```bash
docker compose run --rm app pytest -v
```

## Smoke test

После запуска Docker Compose основной E2E-сценарий можно проверить одной командой.

Smoke test выполняет:

1. `GET /ping`;
2. `POST /query`;
3. ожидание ответа эмулятора;
4. `GET /history`;
5. проверку сохранённой записи.

### Windows PowerShell

```powershell
.\scripts\smoke_test.ps1
```

### Linux и macOS

```bash
chmod +x scripts/smoke_test.sh
./scripts/smoke_test.sh
```

Ожидаемый результат:

```text
+ Smoke test passed
```

Во время ручной проверки был успешно выполнен запрос с длительностью около 57 секунд, что подтверждает работу сценария с обработкой до 60 секунд.

## GitHub Actions

Workflow находится в:

```text
.github/workflows/tests.yml
```

При отправке изменений и создании Pull Request автоматически запускаются тесты проекта.

## Остановка

Остановить контейнеры:

```bash
docker compose down
```

Остановить контейнеры и удалить данные PostgreSQL:

```bash
docker compose down -v
```

Команда с `-v` полностью удаляет Docker volume с базой данных.

## Принятые решения по неоднозначностям ТЗ

1. `/query` принимает кадастровый номер, широту и долготу, поскольку все три значения перечислены в основном описании задания.
2. Основной метод эмулятора — `POST /result`, потому что ему передаются данные запроса.
3. Для совместимости также доступен `GET /result`.
4. Внешний тайм-аут установлен в 65 секунд, поскольку обработка на эмуляторе может занимать до 60 секунд.
5. Запрос сохраняется до обращения к внешнему серверу.
6. Ошибочные запросы и тайм-ауты сохраняются в истории наравне с успешными.
7. `false` считается корректным результатом, а не ошибкой.
8. Отдельный эмулятор реализован как самостоятельный Docker-сервис.
9. Авторизация и админ-панель не добавлены в обязательное ядро, чтобы не усложнять первичную проверку сервиса.

