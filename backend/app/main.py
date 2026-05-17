import uuid
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from contextlib import asynccontextmanager
from pydantic import BaseModel

from backend.app.ws_manager import manager  # Импортируем наш менеджер
from backend.app.database import engine, Base, get_async_session
from backend.app.models import Task
from backend.app.schemas import TaskCreate, TaskResponse, AudioTaskCreate
from backend.app.worker import process_audio_task

class BroadcastTaskSchema(BaseModel):
    id: str
    title: str
    status: str
    telegram_user_id: int

class TaskUpdateSchema(BaseModel):
    status: str

# Настраиваем жизненный цикл приложения (Lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        # Автоматически создаем все таблицы, описанные в моделях (если их еще нет в БД)
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Omni Task Manager API",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Разрешаем фронтенду подключаться
    allow_credentials=True,
    allow_methods=["*"],  # Разрешаем GET, POST, OPTIONS, PUT, DELETE
    allow_headers=["*"],
)

# Эндпоинт проверки здоровья сервиса (Healthcheck)
@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "backend"}

# Эндпоинт для получения ВСЕХ задач (для главного дашборда)
@app.get("/tasks", response_model=list[TaskResponse])
async def get_all_tasks(db: AsyncSession = Depends(get_async_session)):
    query = select(Task).order_by(Task.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks

# Эндпоинт для создания новой задачи (текст)
@app.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(task_data: TaskCreate, db: AsyncSession = Depends(get_async_session)):
    new_task = Task(
        title=task_data.title,
        telegram_user_id=task_data.telegram_user_id
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    
    await manager.broadcast({
        "event": "task_created",
        "task": {
            "id": str(new_task.id),
            "title": new_task.title,
            "status": new_task.status.value if hasattr(new_task.status, 'value') else new_task.status,
            "telegram_user_id": new_task.telegram_user_id
        }
    })
    return new_task

# Эндпоинт для обновления статуса задачи (вызывается сайтом или ботом)
@app.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, task_data: TaskUpdateSchema, db: AsyncSession = Depends(get_async_session)):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат UUID")
        
    query = select(Task).where(Task.id == task_uuid)
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
        
    task.status = task_data.status
    await db.commit()
    await db.refresh(task)
    
    # Оповещаем все открытые вкладки браузера об изменении статуса
    await manager.broadcast({
        "event": "task_updated",
        "task": {
            "id": str(task.id),
            "title": task.title,
            "status": task.status.value if hasattr(task.status, 'value') else task.status,
            "telegram_user_id": task.telegram_user_id
        }
    })
    return task

# Эндпоинт для удаления задачи (вызывается сайтом или ботом)
@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str, db: AsyncSession = Depends(get_async_session)):
    try:
        task_uuid = uuid.UUID(task_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат UUID")
        
    query = select(Task).where(Task.id == task_uuid)
    result = await db.execute(query)
    task = result.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")
        
    await db.delete(task)
    await db.commit()
    
    # Оповещаем фронтенд, что карточку пора удалить с экрана
    await manager.broadcast({
        "event": "task_deleted",
        "task_id": task_id
    })
    return {"success": True}

# Эндпоинт для получения всех задач конкретного пользователя Telegram
@app.get("/tasks/user/{telegram_user_id}", response_model=list[TaskResponse])
async def get_user_tasks(telegram_user_id: int, db: AsyncSession = Depends(get_async_session)):
    query = select(Task).where(Task.telegram_user_id == telegram_user_id).order_by(Task.created_at.desc())
    result = await db.execute(query)
    tasks = result.scalars().all()
    return tasks

# Эндпоинт для добавления аудио в Celery
@app.post("/tasks/audio", status_code=202)
async def process_audio_endpoint(audio_data: AudioTaskCreate):
    process_audio_task.delay(audio_data.file_id, audio_data.telegram_user_id)
    return {
        "message": "Задача на расшифровку аудио добавлена в очередь", 
        "file_id": audio_data.file_id
    }

# Внутренний эндпоинт для воркера
@app.post("/internal/broadcast")
async def internal_broadcast(task: BroadcastTaskSchema):
    await manager.broadcast({
        "event": "task_created",
        "task": task.model_dump()
    })
    return {"success": True}

# WEBSOCKET ЭНДПОИНТ
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)