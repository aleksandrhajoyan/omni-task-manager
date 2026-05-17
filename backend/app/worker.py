import os
import tempfile
import httpx
from celery import Celery
import logging
from openai import OpenAI
import urllib.request
import json


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.database import Base
from backend.app.models import Task

logger = logging.getLogger(__name__)



REDIS_URL = os.getenv("REDIS_URL", "redis://redis_broker:6379/0")
# ... дальше весь твой остальной код без изменений
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Строим синхронный URL базы данных
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@postgres_db:5432/{os.getenv('POSTGRES_DB')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

celery_app = Celery("worker", broker=REDIS_URL, backend=REDIS_URL)
client = OpenAI(api_key=OPENAI_API_KEY)

@celery_app.task(bind=True, max_retries=3)
def process_audio_task(self, file_id: str, telegram_user_id: int):
    logger.info(f"Начало обработки аудио {file_id} от пользователя {telegram_user_id}")
    
    file_info_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}"
    
    try:
        with httpx.Client() as http_client:
            response = http_client.get(file_info_url)
            response.raise_for_status()
            file_path = response.json()["result"]["file_path"]
            
            download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            
            with tempfile.NamedTemporaryFile(suffix=".ogg", delete=True) as temp_audio:
                audio_response = http_client.get(download_url)
                audio_response.raise_for_status()
                temp_audio.write(audio_response.content)
                temp_audio.flush()
                
                logger.info("Файл успешно скачан. Отправляем в Whisper...")
                
                with open(temp_audio.name, "rb") as audio_file:
                    transcription = client.audio.transcriptions.create(
                        model="whisper-1", 
                        file=audio_file
                    )
                
                transcribed_text = transcription.text
                logger.info(f"Расшифровка получена: {transcribed_text}")
                
                # Сохраняем в базу данных через контекстный менеджер сессии
                # Сохраняем в базу данных через контекстный менеджер сессии
                with SessionLocal() as db:
                    new_task = Task(
                        title=f"🎤 {transcribed_text}",
                        telegram_user_id=telegram_user_id,
                        status="pending"  # Явно передаем дефолтный статус в виде строки
                    )
                    db.add(new_task)
                    db.commit() 
                    db.refresh(new_task) # ВАЖНО: запрашиваем обновленные данные из БД, чтобы получить сгенерированный ID
                    
                    logger.info("Задача успешно сохранена в PostgreSQL!")
                    
                    # --- НОВЫЙ БЛОК: ОТПРАВКА УВЕДОМЛЕНИЯ В FASTAPI ---
                    try:
                        # Формируем JSON-payload для нашего внутреннего эндпоинта
                        broadcast_data = json.dumps({
                            "id": str(new_task.id), 
                            "title": new_task.title,
                            "status": "pending",
                            "telegram_user_id": new_task.telegram_user_id
                        }).encode('utf-8')
                        
                        # Делаем POST-запрос в контейнер бэкенда (имя сервиса backend_api)
                        req = urllib.request.Request(
                            "http://backend_api:8000/internal/broadcast", 
                            data=broadcast_data, 
                            headers={'Content-Type': 'application/json'}
                        )
                        urllib.request.urlopen(req)
                        logger.info("✅ Уведомление об аудио-задаче успешно отправлено в FastAPI")
                    except Exception as e:
                        logger.error(f"❌ Ошибка отправки уведомления в FastAPI: {e}")
                    # ---------------------------------------------------
                    
                return {"status": "success", "text": transcribed_text}

    except Exception as exc:
        logger.error(f"Ошибка при обработке аудио: {exc}")
        raise self.retry(exc=exc, countdown=60)