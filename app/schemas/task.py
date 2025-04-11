from pydantic import BaseModel, ConfigDict, Json
from typing import Optional, Any
from datetime import datetime
from .enums import StatusEnum, ExecutionTypeEnum

class TaskBase(BaseModel):
    name: str
    execution_type: ExecutionTypeEnum
    description: Optional[str] = None
    sequence: int = 0
    config: Optional[dict[str, Any]] = None 

class TaskCreate(TaskBase):
    workflow_id: int 
    pass 

class TaskCreateNested(TaskBase):
     pass 

class TaskUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sequence: Optional[int] = None
    status: Optional[StatusEnum] = None
    config: Optional[dict[str, Any]] = None

class Task(TaskBase):
    id: int
    workflow_id: int
    status: StatusEnum
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
