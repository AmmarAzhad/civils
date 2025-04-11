# app/models/workflow_execution.py
import uuid
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID 
from .base import Base, TimestampMixin
from .enums import StatusEnum 

class WorkflowExecution(Base, TimestampMixin):
    __tablename__ = "workflow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4) 
    workflow_definition_id = Column(Integer, ForeignKey("workflows.id"), nullable=False) 
    status = Column(SQLAlchemyEnum(StatusEnum), default=StatusEnum.PENDING, nullable=False)
    last_message = Column(String, nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    #workflow_definition = relationship("Workflow")