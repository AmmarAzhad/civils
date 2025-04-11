from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from .enums import StatusEnum
from .task import Task 

class WorkflowBase(BaseModel):
    name: str
    description: Optional[str] = None

class WorkflowCreate(WorkflowBase):
    pass

class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[StatusEnum] = None

class Workflow(WorkflowBase):
    id: int
    status: StatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None
    tasks: List[Task] = [] 

    model_config = ConfigDict(from_attributes=True) 