import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

# Считываем переменные окружения, которые мы задали в .env
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres_admin")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secure_db_pass_2026")
POSTGRES_DB = os.getenv("POSTGRES_DB", "omni_tasks")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")

# Формируем URL для асинхронного подключения к Postgres через asyncpg
# Обрати внимание: внутри Docker-сети контейнер бэкенда будет обращаться к БД по имени сервиса 'postgres_db'
DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@postgres_db:{POSTGRES_PORT}/{POSTGRES_DB}"

# Создаем асинхронный движок
engine = create_async_engine(
    DATABASE_URL,
    echo=True,  # Логировать все SQL-запросы в консоль (удобно для разработки)
    future=True
)

# Создаем фабрику асинхронных сессий
async_session_maker = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Базовый класс для всех будущих ORM-моделей (таблиц)
class Base(DeclarativeBase):
    pass

# Асинг-генератор для получения сессии БД в эндпоинтах FastAPI
async def get_async_session():
    async with async_session_maker() as session:
        yield session