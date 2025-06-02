from models import Sample, Task
from sqlmodel import Session, select
from database import engine
from models import SampleCreate
from ollama import Client
from pydantic import BaseModel
from services.sample_services import (
    get_pending_tasks, update_sample_to_done, mark_task_as_done,
    add_samples, add_task_to_samples, get_samples, get_sample_tasks,
    filter_samples, delete_samples, delete_tasks
)
import json
import re
from services.plastic_service import get_current_location,prepare_retrieval
INSTRUCTION_TEMPLATE = """
You are a lab assistant AI.

Provide one of these exact responses (no extra text):

1. Remaining tasks:
**Pending: {"code": "xxx", "lot": "yyy"}**
2. Add sample:
**Add sample: {"code": "xxx", "lot": "yyy"}**
3. Add task:
**Add task: {"code": "xxx", "lot": "yyy", "description": "task description"}**
4. Delete sample:
**Delete sample: {"code": "xxx", "lot": "yyy"}**
5. Show all remaining tasks:
**Filter all samples: {"status": "pending"}**
6. List samples by status:
**Get sample: {"status": "pending"}**  
or  
**Get sample: {"status": "done"}**
7. List tasks of a sample:
**Get sample task: {"code": "xxx", "lot": "yyy"}**
8. Mark sample done:
**Update sample to done: {"code": "xxx", "lot": "yyy"}**
9. Find sample location (e.g. "Where is code p640j lot 58"):
**Find location: {"code": "xxx", "lot": "yyy"}**
10. Guide for rearranging sample (e.g. "I wanna take sample p640j lot 58 out"):
**Rearrange sample: {"code": "xxx", "lot": "yyy"}**

**Always ensure the JSON is valid: use double quotes for all keys and string values, and do not forget closing braces.**
""".strip()


client = Client()

class TaskCreate(BaseModel):
    description: str

def get_sample_id_by_code_lot(code: str, lot: str, session: Session) -> int:
    sample = session.exec(select(Sample).where(Sample.code == code, Sample.lot == lot)).first()
    if not sample:
        raise Exception(f"Sample with code '{code}' and lot '{lot}' not found.")
    return sample.id

def get_task_id_by_code_lot_description(code: str, lot: str, description: str, session: Session) -> int:
    sample = session.exec(select(Sample).where(Sample.code == code, Sample.lot == lot)).first()
    if not sample:
        raise Exception(f"Sample with code '{code}' and lot '{lot}' not found.")
    task = next((t for t in sample.tasks if t.description.strip().lower() == description.strip().lower()), None)
    if not task:
        raise Exception(f"Task with description '{description}' not found in sample {code}-{lot}.")
    return task.id
def get_task_description_by_index(code: str, lot: str, index: int, session: Session) -> str:
    sample = session.exec(select(Sample).where(Sample.code == code, Sample.lot == lot)).first()
    if not sample:
        raise Exception(f"Sample with code '{code}' and lot '{lot}' not found.")
    if index < 1 or index > len(sample.tasks):
        raise Exception(f"Task #{index} not found for sample {code}-{lot}.")
    return sample.tasks[index - 1].description

def generate_prompt_from_sample(sample: Sample, user_question: str) -> str:
    task_list = "\n".join([f"{i+1}. {t.description}" for i, t in enumerate(sample.tasks)]) or "- No tasks yet"
    sample_info = f"""
SAMPLE INFO:
Code: {sample.code}
Lot: {sample.lot}
Status: {sample.status}
Tasks:
{task_list}
""".strip()
    return f"{INSTRUCTION_TEMPLATE}\n\n{sample_info}\n\nUSER QUESTION:\n{user_question}"

def dispatch_action(response: str, session: Session):
    # Task done
    # if m := re.search(r"\*\*Task is: (\{.*?\})\*\*", response):
    #     data = json.loads(m.group(1))
    #     task_id = get_task_id_by_code_lot_description(data["code"], data["lot"], data["description"], session)
    #     return mark_task_as_done(task_id, session=session)
    # Pending tasks
    if m := re.search(r"Pending: (\{.*?\})", response):
        data = json.loads(m.group(1))
        sample_id = get_sample_id_by_code_lot(data["code"], data["lot"], session)
        return get_pending_tasks(sample_id, session=session)
    # Add sample
    if m := re.search(r"Add sample: (\{.*?\})", response):
        data = json.loads(m.group(1))
        return add_samples(SampleCreate(code=data["code"], lot=data["lot"]), session=session)
    # Add task
    if m := re.search(r"Add task: (\{.*?\})", response):
        data = json.loads(m.group(1))
        sample_id = get_sample_id_by_code_lot(data["code"], data["lot"], session)
        return add_task_to_samples(sample_id, TaskCreate(description=data["description"]), session=session)
    # Delete sample
    if m := re.search(r"Delete sample: (\{.*?\})", response):
        data = json.loads(m.group(1))
        sample_id = get_sample_id_by_code_lot(data["code"], data["lot"], session)
        return delete_samples(sample_id, session=session)
    # Delete task
    # if m := re.search(r"Delete task: (\{.*?\})", response):
    #     data = json.loads(m.group(1))
    #     task_id = get_task_id_by_code_lot_description(data["code"], data["lot"], data["description"], session)
    #     return delete_tasks(task_id, session=session)
    # Filter samples
    if m := re.search(r"Filter all samples: (\{.*?\})", response):
        data = json.loads(m.group(1))
        return filter_samples(session=session)
    # List samples
    if m := re.search(r"Get sample: (\{.*?\})", response):
        data = json.loads(m.group(1))
        return get_samples(data["status"], session=session)
    # Get sample task
    if m := re.search(r"Get sample task: (\{.*?\})", response):
        data = json.loads(m.group(1))
        sample_id = get_sample_id_by_code_lot(data["code"], data["lot"], session)
        return get_sample_tasks(sample_id, session=session)
    # Update sample done
    if m := re.search(r"Update sample to done: (\{.*?\})", response):
        data = json.loads(m.group(1))
        sample_id = get_sample_id_by_code_lot(data["code"], data["lot"], session)
        return update_sample_to_done(sample_id, session=session)
    # Find sample Location
    if m := re.search(r"Find location: (\{.*?\})", response):
        data = json.loads(m.group(1))
        code,lot,pallet,target_layer=get_current_location(data["code"],data["lot"],session=session)
        return f"Retain with code {code} lot {lot} located at pallet {pallet} layer {target_layer}"
    # Rearrange
    if m := re.search(r"Rearrange sample: (\{.*?\})", response):
        data=json.loads(m.group(1))
        code,lot,pallet,target_layer=get_current_location(data["code"],data["lot"],session=session)
        return prepare_retrieval(code,lot,target_layer,session=session)
    # Unclear
    if "The question is unclear." in response:
        return response
    return response

def ask_llm_about_sample(code: str, lot: str, user_question: str) -> dict:
    """
    Pre-handle 'task X done' and 'delete task X' directly in backend before calling LLM.
    """
    with Session(engine) as session:
        # extract numeric task index
        if m := re.search(r"task\s+(\d+)\s+done", user_question, re.IGNORECASE):
            idx = int(m.group(1))
            desc = get_task_description_by_index(code, lot, idx, session)
            # mark done directly
            task_id = get_task_id_by_code_lot_description(code, lot, desc, session)
            result = mark_task_as_done(task_id, session=session)
            return {"llm_response": None, "action_result": result}
        if m := re.search(r"delete\s+task\s+(\d+)", user_question, re.IGNORECASE):
            idx = int(m.group(1))
            desc = get_task_description_by_index(code, lot, idx, session)
            task_id = get_task_id_by_code_lot_description(code, lot, desc, session)
            result = delete_tasks(task_id, session=session)
            return {"llm_response": None, "action_result": result}

        # fallback to LLM for other intents
        sample = session.exec(
            select(Sample).where(Sample.code == code, Sample.lot == lot)
        ).first()
        if not sample:
            sample = Sample(code=code, lot=lot, status="unknown", tasks=[])
        prompt = generate_prompt_from_sample(sample, user_question)
        response = client.chat(
            model='llama3',
            messages=[{"role": "user", "content": prompt}]
        )["message"]["content"]
        result = dispatch_action(response, session)
        return {"llm_response": response, "action_result": result}
