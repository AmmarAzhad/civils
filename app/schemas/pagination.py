from pydantic import BaseModel, Field
from typing import List, Generic, TypeVar, Optional

DataType = TypeVar('DataType')

class Page(BaseModel, Generic[DataType]):
    """
    Generic pagination schema.
    """
    items: List[DataType]
    page: Optional[int] = Field(None, ge=1, description="Current page number (if applicable)")
    size: Optional[int] = Field(None, ge=1, description="Number of items per page (if applicable)")
    total: int = Field(..., ge=0, description="Total number of items available")
    pages: Optional[int] = Field(None, ge=0, description="Total number of pages (if applicable)")