# Базовый образ с легковесным Python на Alpine Linux
FROM python:3.11-alpine

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Запрещаем Python писать файлы кэша .pyc на диск
ENV PYTHONDONTWRITEBYTECODE 1
# Отключаем буферизацию логов, чтобы сразу видеть их в консоли Докера
ENV PYTHONUNBUFFERED 1

# Копируем файл зависимостей в контейнер
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# ИЗМЕНЕНИЕ ЗДЕСЬ: копируем весь код именно в папку backend внутри контейнера
COPY . /app/backend

# Команда для запуска сервера Uvicorn при старте контейнера
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]