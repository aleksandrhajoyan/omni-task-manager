import enum
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Enum, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from backend.app.database import Base

# Описываем статус задачи через стандартный Enum Python.
# На уровне СУБД это будет валидироваться как строгое ограничение (Constraint).
class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class Task(Base):
    """
    ORM-модель для таблицы 'tasks'.
    Каждому атрибуту класса будет соответствовать колонка в таблице PostgreSQL.
    """
    __tablename__ = "tasks"

    # UUID как первичный ключ (Primary Key). В отличие от Serial (int), 
    # его невозможно предугадать, и он генерируется децентрализованно.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, 
        default=uuid.uuid4
    )
    
    # Заголовок задачи (текст или результат транскрибации)
    title: Mapped[str] = mapped_column(
        String(500), 
        nullable=False
    )
    
    # Статус задачи с дефолтным значением 'pending'
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status_enum"), 
        default=TaskStatus.PENDING, 
        nullable=False
    )
    
    # Идентификатор пользователя в Telegram (BigInteger, т.к. лимиты Integer в Postgres можно превысить)
    telegram_user_id: Mapped[int] = mapped_column(
        BigInteger, 
        nullable=False
    )
    
    # Временная метка создания (Timestamp) с дефолтной фиксацией времени на сервере
    created_at: Mapped[datetime] = mapped_column(
        DateTime, 
        default=datetime.utcnow, 
        nullable=False
    )

    def __repr__(self) -> str:
        """Понятное строковое представление объекта в логах (как метод __str__)"""
        return f"<Task id={self.id} title={self.title[:20]} status={self.status}>"