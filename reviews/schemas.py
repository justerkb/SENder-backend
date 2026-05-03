from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewCreate(BaseModel):
    sender_id: int = Field(gt=0)
    traveler_id: int = Field(gt=0)
    package_id: int = Field(gt=0)
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1)


class ReviewUpdate(BaseModel):
    """Full update — both fields required."""

    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1)


class ReviewPartialUpdate(BaseModel):
    """Partial update — all fields optional."""

    rating: Optional[int] = Field(default=None, ge=1, le=5)
    comment: Optional[str] = Field(default=None, min_length=1)


class ReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    traveler_id: int
    package_id: int
    rating: int
    comment: str
    created_at: datetime
    updated_at: datetime

