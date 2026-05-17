# Omni-Channel Task Management System

Production-ready система управления задачами с приемом тасок через Telegram (текст/голос) и отображением на интерактивном веб-дашборде в реальном времени.

## Архитектура проекта
- **Frontend**: React (Vite) + WebSockets
- **Backend API**: FastAPI (Asynchronous REST API)
- **Bot**: aiogram 3.x (Асинхронный Telegram Bot API)
- **Message Broker & Task Queue**: Redis + Celery
- **Database**: PostgreSQL + SQLAlchemy (Async DAO)
- **DevOps**: Docker & Docker Compose (6 изолированных контейнеров)

## Инструкция по запуску

1. Склонируйте репозиторий и перейдите в корень проекта.
2. Создайте файл `.env` в корневом каталоге и заполните переменные окружения:
   ```env
   TELEGRAM_BOT_TOKEN=ваш_токен_бота
   OPENAI_API_KEY=ваш_ключ_openai
   DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres_db:5432/omni_tasks
   REDIS_URL=redis://redis_broker:6373/0

Запустите всю систему одной командой:

docker compose up --build -d

После успешного запуска всех контейнеров:

Веб-дашборд доступен по адресу: http://localhost:5173

Документация FastAPI (Swagger): http://localhost:8000/docs