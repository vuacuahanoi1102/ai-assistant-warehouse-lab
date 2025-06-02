from apscheduler.schedulers.background import BackgroundScheduler
from sqlmodel import Session, select
from sqlalchemy.orm import selectinload
from database import engine
from models import Sample, Task
import asyncio
from services.websocket_manager import connected_clients
from datetime import datetime, timedelta

scheduler = BackgroundScheduler()
event_loop = None  # <-- biến global để chứa loop chính

# Gửi tin nhắn tới tất cả WebSocket clients
async def broadcast_message(message: str):
    for ws in connected_clients:
        try:
            await ws.send_text(message)
        except Exception:
            pass

def remind_task_if_not_done(task_id: int):
    with Session(engine) as session:
        task = session.get(Task, task_id)
        if task and not task.is_done:
            sample = session.get(Sample, task.sample_id)
            message = f"⏰ Task '{task.description}' của sample {sample.code} lot {sample.lot} chưa xong sau 4 tiếng!"
            print("[BOT WARNING]", message)

            if event_loop:
                asyncio.run_coroutine_threadsafe(broadcast_message(message), event_loop)

def schedule_task_reminder(task_id: int):
    run_time = datetime.now() + timedelta(minutes=1)
    scheduler.add_job(
        remind_task_if_not_done,
        "date",
        run_date=run_time,
        args=[task_id],
        id=f"reminder_{task_id}",
        replace_existing=True,
    )

def start_scheduler(loop):
    global event_loop
    event_loop = loop
