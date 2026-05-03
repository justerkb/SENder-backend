from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SenderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=50)
    city: str = Field(min_length=1, max_length=100)


class SenderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, min_length=1, max_length=50)
    city: Optional[str] = Field(default=None, min_length=1, max_length=100)


class SenderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    email: str
    phone: str
    city: str
    created_at: datetime
    updated_at: datetime

