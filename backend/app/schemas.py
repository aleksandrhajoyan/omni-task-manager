import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from backend.app.models import TaskStatus

# Схема для данных, которые приходят к нам ПРИ СОЗДАНИИ задачи
class TaskCreate(BaseModel):
    title: str
    telegram_user_id: int

# Схема для данных, которые мы ОТДАЕМ клиенту при ответе
class TaskResponse(BaseModel):
    id: uuid.UUID
    title: str
    status: TaskStatus
    telegram_user_id: int
    created_at: datetime

    # Конфигурация для автоматического чтения данных из ORM-моделей SQLAlchemy
    model_config = ConfigDict(from_attributes=True)

class AudioTaskCreate(BaseModel):
    file_id: str
    telegram_user_id: int