from sqlmodel import SQLModel,Field,Relationship
from typing import Optional,List
from datetime import datetime
class SampleCreate(SQLModel):
    code:str
    lot:str

class Sample(SampleCreate,table=True):
    id:Optional[int]=Field(default=None,primary_key=True)
    status: str="pending"
    tasks: List["Task"]=Relationship(back_populates="sample",sa_relationship_kwargs={"cascade": "all, delete"})

class Task(SQLModel,table=True):
    id:Optional[int]=Field(default=None,primary_key=True)
    description:str
    is_done: bool=False
    created_at:datetime=Field(default_factory=datetime.utcnow)
    sample_id:int = Field(foreign_key="sample.id")
    sample: Optional[Sample] = Relationship(back_populates="tasks")
    
class PlasticBag(SQLModel,table=True):
    id:Optional[int]=Field(default=None,primary_key=True)
    code: str
    lot: str
    pallet:str
    layer:int
    status: str = "stored"
