from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TravelerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=50)
    bio: str = Field(min_length=1)


class TravelerUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    email: Optional[str] = Field(default=None, min_length=1, max_length=100)
    phone: Optional[str] = Field(default=None, min_length=1, max_length=50)
    bio: Optional[str] = Field(default=None, min_length=1)


class TravelerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    email: str
    phone: str
    bio: str
    created_at: datetime
    updated_at: datetime

