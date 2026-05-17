# Используем легковесный образ Python (как и в бэкенде)
FROM python:3.11-alpine

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем только файл зависимостей (для кэширования слоев Docker)
COPY requirements.txt .

# Устанавливаем библиотеки
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь исходный код бота в контейнер
COPY . .

# Команда для запуска нашего бота
CMD ["python", "main.py"]