import aiohttp
from aiogram import F
import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from keyboards import TaskCallback, get_task_keyboard

# Настройка логирования, чтобы мы видели, что происходит в консоли Docker
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Получаем токен из переменных окружения (Docker прокинет его из .env)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN не найден в переменных окружения!")

# Bot — это класс, который делает HTTP-запросы к API самого Telegram
bot = Bot(token=TELEGRAM_BOT_TOKEN)

# Dispatcher — это маршрутизатор (роутер). 
# Он берет входящие обновления от Telegram и решает, в какую функцию их передать.
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    Хэндлер на команду /start.
    Срабатывает, когда пользователь впервые открывает бота.
    """
    user_name = message.from_user.first_name
    telegram_id = message.from_user.id
    
    await message.answer(
        f"Привет, {user_name}! Я Omni Task Manager 🚀\n\n"
        f"Твой Telegram ID: {telegram_id}\n"
        f"Скоро я научусь сохранять твои задачи в базу данных!"
    )

@dp.message(Command("tasks"))
async def cmd_get_tasks(message: types.Message):
    """
    Получает список задач пользователя с бэкенда.
    """
    user_id = message.from_user.id
    api_url = f"http://backend_api:8000/tasks/user/{user_id}"

    status_msg = await message.answer("⏳ Загружаю задачи...")

    try:
        async with aiohttp.ClientSession() as session:
            # Здесь используем GET, так как мы получаем данные
            async with session.get(api_url) as response:
                if response.status == 200:
                    tasks = await response.json()
                    
                    # ДЕБАГ: выводим в логи Docker сырые данные от сервера
                    logger.info(f"Сырые данные от API: {tasks}")
                    
                    if not tasks:
                        await status_msg.edit_text("📭 У тебя пока нет задач. Напиши мне что-нибудь, чтобы добавить новую!")
                        return
                    
                    text = "📋 **Твои задачи:**\n\n"
                    for i, task in enumerate(tasks, start=1):
                        # Безопасное извлечение: если ключа нет, подставим дефолтное значение
                        status = task.get("status", "pending")
                        title = task.get("title", "Без названия (ошибка данных)")
                        
                        icon = "✅" if status == "completed" else "⏳"
                        text += f"{i}. {icon} {title}\n"
                    
                    await status_msg.edit_text(text, parse_mode="Markdown")
                else:
                    logger.error(f"Ошибка получения задач: {response.status}")
                    await status_msg.edit_text("❌ Ошибка при загрузке задач с сервера.")
    except Exception as e:
        logger.error(f"Ошибка соединения с API (GET tasks): {e}")
        await status_msg.edit_text("❌ Бэкенд временно недоступен.")

@dp.message(F.text)
async def handle_text_task(message: types.Message):
    """
    Ловит любой текст (кроме команд) и отправляет его в FastAPI бэкенд.
    """
    task_title = message.text
    user_id = message.from_user.id

    # Даем пользователю мгновенный фидбек (UI/UX)
    status_msg = await message.answer("⏳ Сохраняю задачу...")

    # URL нашего бэкенда внутри сети Docker Compose.
    api_url = "http://backend_api:8000/tasks"
    
    payload = {
        "title": task_title,
        "telegram_user_id": user_id
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Здесь используем POST, так как мы отправляем данные
            async with session.post(api_url, json=payload) as response:
                if response.status == 201:
                    created_task = await response.json()
                    task_id = created_task.get("id")

                    await status_msg.edit_text(
                        f"✅ Задача успешно сохранена:\n\n_{task_title}_", 
                        parse_mode="Markdown",
                        reply_markup=get_task_keyboard(task_id) # Прикрепляем кнопки
                    )
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка API (статус {response.status}): {error_text}")
                    await status_msg.edit_text("❌ Ошибка при сохранении задачи на сервере.")
    except Exception as e:
        logger.error(f"Ошибка соединения с API: {e}")
        await status_msg.edit_text("❌ Бэкенд временно недоступен (ошибка сети).")

@dp.message(F.voice)
async def handle_voice_task(message: types.Message):
    """
    Ловит голосовые сообщения, берет file_id и кидает в FastAPI для асинхронной обработки.
    """
    # Telegram сам хранит файлы на своих серверах. Нам нужен только уникальный ID файла.
    voice_file_id = message.voice.file_id
    user_id = message.from_user.id

    # Даем пользователю мгновенный фидбек (UI/UX)
    status_msg = await message.answer("🎤 Голосовое сообщение принято! Отправил на расшифровку ⏳")

    api_url = "http://backend_api:8000/tasks/audio"
    
    # Формируем Payload в точности под нашу схему AudioTaskCreate
    payload = {
        "file_id": voice_file_id,
        "telegram_user_id": user_id
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(api_url, json=payload) as response:
                if response.status == 202:
                    # Задача успешно улетела в очередь (Redis). 
                    # Бот свою работу выполнил, он не ждет расшифровки!
                    logger.info(f"Аудио {voice_file_id} отправлено в очередь.")
                else:
                    error_text = await response.text()
                    logger.error(f"Ошибка API (статус {response.status}): {error_text}")
                    await status_msg.edit_text("❌ Ошибка при отправке аудио на сервер.")
    except Exception as e:
        logger.error(f"Ошибка соединения с API (аудио): {e}")
        await status_msg.edit_text("❌ Бэкенд временно недоступен (ошибка сети).")

@dp.callback_query(TaskCallback.filter())
async def process_task_action(callback: types.CallbackQuery, callback_data: TaskCallback):
    """
    Обработчик нажатий на inline-кнопки задач.
    """
    task_id = callback_data.task_id
    action = callback_data.action
    
    # API эндпоинт для конкретной задачи
    api_url = f"http://backend_api:8000/tasks/{task_id}"
    
    async with aiohttp.ClientSession() as session:
        if action == "complete":
            payload = {"status": "completed"}
            async with session.put(api_url, json=payload) as response:
                if response.status == 200:
                    await callback.message.edit_text(
                        f"{callback.message.text}\n\n*Статус:* ✅ Выполнено",
                        parse_mode="Markdown",
                        reply_markup=None
                    )
                    await callback.answer("Задача завершена!")
                else:
                    await callback.answer("Ошибка при обновлении!", show_alert=True)
                    
        elif action == "delete":
            async with session.delete(api_url) as response:
                if response.status == 200: 
                    await callback.message.edit_text("🗑 Задача удалена.")
                    await callback.answer("Удалено!")
                else:
                    await callback.answer("Ошибка при удалении!", show_alert=True)

async def main():
    """
    Главная корутина. Точка входа в приложение бота.
    """
    logger.info("Запуск Telegram-бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")