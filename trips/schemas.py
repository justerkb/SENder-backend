from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TripCreate(BaseModel):
    traveler_id: int = Field(gt=0, description="ID of the traveler making this trip")
    from_city: str = Field(min_length=1, max_length=100)
    to_city: str = Field(min_length=1, max_length=100)
    departure_date: date
    arrival_date: date
    available_weight_kg: float = Field(gt=0, le=30)
    notes: Optional[str] = None
    status: str = Field(
        default="open",
        description="open | full | completed | cancelled",
    )


class TripUpdate(BaseModel):
    traveler_id: Optional[int] = Field(default=None, gt=0)
    from_city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    to_city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    departure_date: Optional[date] = None
    arrival_date: Optional[date] = None
    available_weight_kg: Optional[float] = Field(default=None, gt=0, le=30)
    notes: Optional[str] = None
    status: Optional[str] = None


class TripRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    traveler_id: int
    from_city: str
    to_city: str
    departure_date: date
    arrival_date: date
    available_weight_kg: float
    notes: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
