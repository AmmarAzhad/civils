from sqlalchemy import Column, Integer, String, DateTime, Enum as SQLAlchemyEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base, TimestampMixin
from .enums import StatusEnum 

class Workflow(Base, TimestampMixin):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    status = Column(SQLAlchemyEnum(StatusEnum), default=StatusEnum.PENDING, nullable=False)

    tasks = relationship(
        "Task",
        back_populates="workflow",
        cascade="all, delete-orphan", 
        order_by="Task.sequence",
        lazy="selectin"
    )
