# Сервис сокращения URL-адресов

Сервис на базе FastAPI для создания, управления и отслеживания сокращенных URL-адресов.

## Возможности

- Создание сокращенных URL с пользовательскими алиасами
- Отслеживание посещений и статистики для каждого URL
- Установка срока действия для URL
- Поиск URL по исходному адресу
- Автоматическая очистка истекших и неиспользуемых URL
- Аутентификация пользователей и контроль доступа
- Кэширование Redis для повышения производительности

## Документация API

Документация API доступна в двух форматах:

- **Swagger UI**: Интерактивная документация по адресу `http://localhost:8000/docs`
- **ReDoc**: Альтернативная документация по адресу `http://localhost:8000/redoc`

Документация включает полную информацию об эндпоинтах, схемах запросов/ответов.

## Конечные точки API

### Endpoints аутентификации

- **POST /api/v1/users/register** - Регистрация нового пользователя
- **POST /api/v1/users/login** - Вход и получение токена доступа
- **POST /api/v1/users/logout** - Выход (аннулирование токена)
- **GET /api/v1/users/me** - Получение информации о текущем пользователе

### Endpoints для работы с URL

- **POST /api/v1/links/shorten** - Создание сокращенного URL (поддерживает пользовательский алиас и срок действия)
- **GET /{short_code}** - Перенаправление на исходный URL
- **GET /api/v1/links/{short_code}/stats** - Получение статистики по URL
- **PUT /api/v1/links/{short_code}** - Обновление URL
- **DELETE /api/v1/links/{short_code}** - Удаление URL
- **GET /api/v1/links/search** - Поиск URL по исходному адресу
- **GET /api/v1/links/expired-history** - Получение истории истекших URL
- **POST /api/v1/links/cleanup-unused** - Удаление URL, которые не использовались в течение указанного периода

## Примеры

### Регистрация пользователя

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/register' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "email": "user@example.com",
  "username": "testuser",
  "password": "securepassword123"
}'
```

### Вход в систему

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/users/login' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -d 'username=testuser&password=securepassword123'
```

### Создание сокращенного URL

```bash
curl -X 'POST' \
  'http://localhost:8000/api/v1/links/shorten' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN' \
  -H 'Content-Type: application/json' \
  -d '{
  "original_url": "https://example.com/very/long/url/that/needs/shortening",
  "custom_alias": "example",
  "expires_at": "2023-12-31T00:00:00Z"
}'
```

### Перенаправление на исходный URL

```bash
curl -L -X 'GET' 'http://localhost:8000/example'
```

### Получение статистики по URL

```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/links/example/stats' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

### Поиск URL

```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/links/search?original_url=example.com' \
  -H 'accept: application/json'
```

### Просмотр истории истекших URL

```bash
curl -X 'GET' \
  'http://localhost:8000/api/v1/links/expired-history?limit=10&offset=0' \
  -H 'accept: application/json' \
  -H 'Authorization: Bearer YOUR_ACCESS_TOKEN'
```

## Автоматическая очистка

Сервис включает автоматическую очистку для:

1. **Истекших URL**: URL, срок действия которых истек, автоматически удаляются
2. **Неиспользуемых URL**: URL, которые не использовались в течение настроенного периода (по умолчанию: 90 дней)

Задачи очистки выполняются по расписанию с использованием выделенного сервиса очистки в конфигурации Docker Compose.

## Инструкции по установке

### Использование Docker

1. Клонируйте репозиторий
2. Скопируйте файл `.env.example` в `.env` и настройте переменные окружения:
   ```bash
   cp .env.example .env
   ```
3. Отредактируйте файл `.env`, установив безопасные значения для секретов
4. Запустите с помощью docker-compose:
   ```bash
   docker-compose -f deployment/docker-compose.yml --env-file .env up -d
   ```

### Ручками

1. Клонируйте репозиторий
2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```
3. Скопируйте файл `.env.example` в `.env` и настройте переменные окружения
4. Настройте PostgreSQL и Redis
5. Запустите приложение:
   ```bash
   uvicorn src.app.main:app --reload
   ```

### Переменные окружения

Для настройки приложения используется файл `.env`. Вот основные переменные:

```
# Настройки PostgreSQL
POSTGRES_USER=urlshortener
POSTGRES_PASSWORD=securepassword
POSTGRES_DB=urlshortener
POSTGRES_PORT=5433

# Настройки Redis
REDIS_PORT=6379

# Настройки API
API_PORT=8000

# Настройки приложения
SECRET_KEY=your-very-secure-and-random-secret-key
UNUSED_LINKS_THRESHOLD_DAYS=90
```

## Описание базы данных

Приложение использует PostgreSQL в качестве основной базы данных и Redis для кэширования.

### Схема базы данных

#### Таблица Users
- id: Первичный ключ
- email: Уникальный адрес электронной почты
- username: Уникальное имя пользователя
- hashed_password: Безопасно хешированный пароль
- is_active: Флаг активного статуса
- created_at: Временная метка создания
- updated_at: Временная метка последнего обновления

#### Таблица URLs
- id: Первичный ключ
- original_url: Исходный длинный URL
- short_code: Уникальный короткий код для URL
- expires_at: Опциональная дата истечения срока действия
- visits: Количество посещений короткого URL
- last_visited_at: Временная метка последнего посещения
- user_id: Внешний ключ к пользователю, создавшему URL
- created_at: Временная метка создания
- updated_at: Временная метка последнего обновления

### Кэширование Redis

Приложение использует Redis для кэширования:
- Данных URL по короткому коду
- Данных пользователя по email и имени пользователя
- Активных токенов

Кэшированные элементы имеют соответствующие TTL и инвалидируются при обновлениях/удалениях.

### Логи

- Логи сервиса можно просмотреть с помощью Docker:
  ```bash
  docker-compose -f deployment/docker-compose.yml logs -f urlshortener
  ```

- Для операций с базой данных:
  ```bash
  docker-compose -f deployment/docker-compose.yml logs -f postgres
  ```
