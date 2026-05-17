from aiogram.filters.callback_data import CallbackData
from aiogram.utils.keyboard import InlineKeyboardBuilder

# 1. Определяем структуру "прерывания" (CallbackData). 
# Это как C-struct, который Aiogram сам сериализует в строку для Telegram.
class TaskCallback(CallbackData, prefix="task"):
    action: str  # Например: "complete", "delete"
    task_id: str # UUID задачи из базы данных

# 2. Функция-генератор клавиатуры для конкретной задачи
def get_task_keyboard(task_id: str):
    builder = InlineKeyboardBuilder()
    
    # Добавляем кнопку "Выполнено"
    builder.button(
        text="✅ Завершить", 
        callback_data=TaskCallback(action="complete", task_id=task_id)
    )
    # Добавляем кнопку "Удалить"
    builder.button(
        text="🗑 Удалить", 
        callback_data=TaskCallback(action="delete", task_id=task_id)
    )
    
    # Выстраиваем кнопки в один ряд
    builder.adjust(2) 
    return builder.as_markup()