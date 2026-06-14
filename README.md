# АВТОСНАБ Test Task

FastAPI-сервис для обработки запросов с кадастровым номером, широтой и долготой.

Сервис принимает данные, эмулирует обращение к внешнему серверу, получает результат `true` или `false`, сохраняет запрос и результат в PostgreSQL и предоставляет API для просмотра истории запросов.

## Стек

* Python 3.11
* FastAPI
* PostgreSQL
* asyncpg
* Docker
* Docker Compose
* Pytest
* Raw SQL migrations

## Возможности

* Проверка работоспособности сервера
* Приём кадастрового номера, широты и долготы
* Валидация входных данных
* Эмуляция внешнего сервера
* Сохранение запроса и результата в PostgreSQL
* Получение истории всех запросов
* Получение истории по кадастровому номеру
* Автоматическое применение SQL-миграций при старте приложения
* Swagger-документация

## Запуск проекта

Из корня проекта выполните команду:

```bash
docker compose up --build
```

После запуска сервис будет доступен по адресу:

```text
http://localhost:8000
```

## Документация API

Swagger UI:

```text
http://localhost:8000/docs
```

ReDoc:

```text
http://localhost:8000/redoc
```

## Эндпоинты

### Проверка сервера

```http
GET /ping
```

Пример ответа:

```json
{
  "status": "ok"
}
```

---

### Отправка запроса

```http
POST /query
```

Пример тела запроса:

```json
{
  "cadastral_number": "66:41:0101001:123",
  "latitude": 56.8389,
  "longitude": 60.6057
}
```

Пример ответа:

```json
{
  "id": 1,
  "cadastral_number": "66:41:0101001:123",
  "latitude": 56.8389,
  "longitude": 60.6057,
  "result": true,
  "created_at": "2026-06-14T12:00:00.000000Z"
}
```

---

### Получение всей истории запросов

```http
GET /history
```

Пример ответа:

```json
[
  {
    "id": 1,
    "cadastral_number": "66:41:0101001:123",
    "latitude": 56.8389,
    "longitude": 60.6057,
    "result": true,
    "created_at": "2026-06-14T12:00:00.000000Z"
  }
]
```

---

### Получение истории по кадастровому номеру

```http
GET /history?cadastral_number=66:41:0101001:123
```

---

### Эмуляция внешнего сервера

```http
GET /result
```

Пример ответа:

```json
{
  "result": true
}
```

или:

```json
{
  "result": false
}
```

По условию задания внешний сервер может обрабатывать запрос до 60 секунд.
Для удобства проверки в проекте используется случайная задержка от 1 до 5 секунд.

## Валидация

Для эндпоинта `/query` используется валидация:

* `cadastral_number` — формат `числа:числа:числа:числа`
* `latitude` — от `-90` до `90`
* `longitude` — от `-180` до `180`

Пример валидного кадастрового номера:

```text
66:41:0101001:123
```

## База данных

Используется таблица `requests_history`.

Поля:

* `id`
* `cadastral_number`
* `latitude`
* `longitude`
* `result`
* `created_at`

SQL-миграции находятся в папке:

```text
migrations/
```

Миграции применяются автоматически при старте приложения.

## Переменные окружения

Пример переменных окружения находится в файле:

```text
.env.example
```

Основные переменные:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/autosnab_db
EXTERNAL_SERVER_URL=http://127.0.0.1:8000/result
```

В Docker Compose для приложения используется подключение к базе данных по адресу:

```env
DATABASE_URL=postgresql://postgres:postgres@db:5432/autosnab_db
```

## Тесты

Для запуска тестов локально:

```bash
pytest
```

## Пример проверки через Swagger

1. Запустить проект:

```bash
docker compose up --build
```

2. Открыть документацию:

```text
http://localhost:8000/docs
```

3. Проверить `GET /ping`.

4. Выполнить `POST /query` с телом:

```json
{
  "cadastral_number": "66:41:0101001:123",
  "latitude": 56.8389,
  "longitude": 60.6057
}
```

5. Проверить сохранение данных через `GET /history`.

## Остановка проекта

```bash
docker compose down
```

Если нужно удалить также данные PostgreSQL:

```bash
docker compose down -v
```



