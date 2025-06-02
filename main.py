from fastapi import FastAPI,Depends,HTTPException,Body,Query,WebSocket

from sqlmodel import Session,select
from models import Sample,SampleCreate,Task
from database import create_db_and_tables,get_session
from contextlib import asynccontextmanager
from pydantic import BaseModel
from sqlalchemy.orm import selectinload
from services.chat_services import extract_code_and_lot
from services.sample_services import (
    get_pending_tasks, update_sample_to_done, mark_task_as_done,add_samples,add_task_to_samples,get_samples,get_sample_tasks,filter_samples,delete_samples,delete_tasks
)
from services.reminder_services import start_scheduler
from services.llm_service import ask_llm_about_sample
from services.websocket_manager import connected_clients, add_client, remove_client, send_message_to_clients
import asyncio
from services.reminder_services import start_scheduler
from services.plastic_service import add_new_lot,prepare_retrieval,get_current_location
# Trước khi chạy app
loop = asyncio.get_event_loop()
start_scheduler(loop)

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await add_client(websocket)  # Thêm client vào danh sách
    try:
        while True:
            await websocket.receive_text()  # Giữ kết nối sống
    except Exception:
        await remove_client(websocket)
    
class TaskCreate (BaseModel):
    description: str
class QuestionRequest(BaseModel):
    question: str
from fastapi.middleware.cors import CORSMiddleware


# Cho phép mọi origin gọi API (cho dev/test)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # hoặc ['http://localhost:3000'] nếu bạn dùng React/Vite
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/sample/")
def add_sample(sample_create:SampleCreate,session:Session=Depends(get_session)):
    return add_samples(sample_create,session)

@app.post("/sample/{sample_id}/task")
def add_task_to_sample(sample_id:int,task_data:TaskCreate,session:Session=Depends(get_session)):
    return add_task_to_samples(sample_id,task_data,session)

@app.get("/sample/")
def get_sample(status:str = None,session:Session =Depends(get_session)):
    return get_samples(status,session)

@app.get("/sample/{sample_id}/tasks")
def get_sample_task(sample_id:int,session:Session = Depends(get_session)):
    return get_sample_tasks(sample_id,session)

@app.get("/sample/filter")
def filter_sample(session:Session = Depends(get_session)):
    return filter_samples(session)

@app.get("/sample/{sample_id}/todo")
def get_pending_task(sample_id:int,session:Session=Depends(get_session)):
    return get_pending_tasks(sample_id,session)

@app.put("/sample/{sample_id}")
def update_sample_status(sample_id:int,session:Session=Depends(get_session)):
    return update_sample_to_done(sample_id,session)

@app.put("/task/{task_id}")
def mark_task_done(task_id:int,session:Session=Depends(get_session)):
    return mark_task_as_done(task_id,session)

@app.delete("/sample/{sample_id}")
def delete_sample(sample_id:int,session:Session=Depends(get_session)):
    return delete_samples(sample_id,session)

@app.delete("/task/{task_id}")
def delete_task(task_id:int, session: Session=Depends(get_session)):
    return delete_tasks(task_id,session)

@app.post("/plastic/add")
def add_plastic_bag(code:str,lot:str,session: Session=Depends(get_session)):
    return add_new_lot(code,lot,session)

@app.get("/plastic/location")
def get_location(code:str,lot:str,session:Session=Depends(get_session)):
    return get_current_location(code,lot,session)

@app.post("/plastic/retrieval")
def plastic_retrieval(code:str,lot:str,target_layer:int,session:Session=Depends(get_session)):
    return prepare_retrieval(code,lot,target_layer,session)

@app.post("/ask_llm")
def ask_llm(request: QuestionRequest):
    code, lot = extract_code_and_lot(request.question)
    response = ask_llm_about_sample(code, lot, request.question)
    print("LLM Response:", response)
    return {"response": response}

