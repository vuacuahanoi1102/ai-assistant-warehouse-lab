from sqlmodel import Session,select
from models import Sample, Task,SampleCreate
from fastapi import HTTPException
from task_template import TASK_TEMPLATES
from pydantic import BaseModel
from services.reminder_services import schedule_task_reminder

    
class TaskCreate (BaseModel):
    description: str
def delete_tasks(task_id:int, session: Session):
    task=session.get(Task,task_id)
    if not task:
        return f"task not found"
    sample=task.sample
    session.delete(task)
    session.commit()
    return f"Task {task.description} of code {sample.code} lot {sample.lot} deleted"

def delete_samples(sample_id:int,session:Session):
    sample=session.get(Sample,sample_id)
    if not sample:
        return f"Sample not found"
    session.delete(sample)
    session.commit()
    return f"Sample with code {sample.code} lot {sample.lot} deleted"

def filter_samples(session: Session):
    samples = session.exec(select(Sample)).all()
    lines = []
    for sample in samples:
        pending_tasks = [t.description for t in sample.tasks if not t.is_done]
        if pending_tasks:
            task_list = ", ".join(pending_tasks)
            lines.append(f"code {sample.code} lot {sample.lot} task remain {task_list}")
    if not lines:
        return "No pending task found."
    return "\n".join(lines)

def get_sample_tasks(sample_id: int, session: Session):
    sample = session.get(Sample, sample_id)
    if not sample:
        return f"Sample not found"
    if not sample.tasks:
        return f"code {sample.code} lot {sample.lot} has no tasks."
    lines = [f"code {sample.code} lot {sample.lot} have task:"]
    lines += [f"- {task.description}" for task in sample.tasks]
    return "\n".join(lines)

def get_samples(status:str,session:Session):
    query=select(Sample)
    if status:
        query=query.where(Sample.status == status)
    samples=session.exec(query).all()
    if not samples:
        return f"No samples found with status '{status}'."
    lines = [f"Sample {sample.status}: code {sample.code}, lot {sample.lot},id {sample.id}" for sample in samples]
    return "\n".join(lines)

def add_task_to_samples(sample_id:int,task_data:TaskCreate,session:Session):
    sample=session.get(Sample,sample_id)
    if not sample:
        return f"sample not found"
    task=Task(description=task_data.description,sample_id=sample_id)
    session.add(task)
    session.commit()
    session.refresh(task)
    
    return f"Add task {task.description} to code {sample.code}, lot {sample.lot}"
def add_samples(sample_create:SampleCreate,session:Session):
    sample=Sample.from_orm(sample_create)
    session.add(sample)
    session.commit()
    session.refresh(sample)
    task_list=TASK_TEMPLATES.get(sample.code.lower(),TASK_TEMPLATES["default"])
    task_created=[]
    for desc in task_list:
        task = Task(description=desc,sample_id=sample.id)
        session.add(task)
        task_created.append(desc)
    session.commit()
    schedule_task_reminder(task.id)
    task_display="\n".join(f"- {desc}" for desc in task_created)
    return f"""Sample added — Code: {sample.code}, Lot: {sample.lot}
    Tasks:
    {task_display}
    """

def get_pending_tasks(sample_id:int,session:Session):
    sample=session.get(Sample,sample_id)
    if not sample:
        return f"sample not found"
    pending_tasks=[t for t in sample.tasks if not t.is_done]
    if not pending_tasks:
        return f"Code {sample.code} lot {sample.lot} have no pending task"
    lines=[f"code {sample.code} lot {sample.lot} pending task:"]
    lines+=[f"-{task.description}" for task in pending_tasks]
    return "\n".join(lines)

def update_sample_to_done(sample_id:int,session:Session):
    sample=session.get(Sample,sample_id)
    if not sample:
        return f"sample not found"
    sample.status = "done"
    for task in sample.tasks:
        task.is_done=True
        session.add(task)
    session.add(sample)
    session.commit()
    session.refresh(sample)
    return f"Sample code {sample.code} lot {sample.lot} marked as done. All tasks completed."

def mark_task_as_done(task_id:int,session:Session):
    task=session.get(Task,task_id)
    if not task:
        return f"Task not found"
    task.is_done=True
    session.add(task)
    session.commit()
    session.refresh(task)
    sample=task.sample
    if all(t.is_done for t in sample.tasks):
        sample.status = "done"
        session.add(sample)
        session.commit()
    return f"Task {task.description} of code {sample.code} lot {sample.lot} completed"