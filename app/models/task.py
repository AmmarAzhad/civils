from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLAlchemyEnum, JSON, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, TimestampMixin
from .enums import StatusEnum, ExecutionTypeEnum
class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True) 
    execution_type = Column(SQLAlchemyEnum(ExecutionTypeEnum), nullable=False)
    sequence = Column(Integer, default=0, nullable=False) 
    status = Column(SQLAlchemyEnum(StatusEnum), default=StatusEnum.PENDING, nullable=False)
    config = Column(JSON, nullable=True) 

    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)

    workflow = relationship("Workflow", back_populates="tasks")