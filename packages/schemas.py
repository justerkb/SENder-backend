from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class PackageCreate(BaseModel):
    sender_id: int = Field(gt=0, description="ID of the sender")
    accepted_traveler_id: Optional[int] = Field(
        default=None, gt=0, description="ID of traveler who accepted"
    )
    description: str = Field(min_length=1)
    pickup_city: str = Field(min_length=1, max_length=100)
    delivery_city: str = Field(min_length=1, max_length=100)
    weight_kg: float = Field(gt=0, le=30, description="Weight in kg, max 30")
    size: str = Field(min_length=1, description="small | medium | large")
    reward: float = Field(ge=0, description="Reward in USD for the traveler")
    deadline: date
    status: str = Field(
        default="pending",
        description="pending | accepted | in_transit | delivered | cancelled",
    )


class PackageUpdate(BaseModel):
    sender_id: Optional[int] = Field(default=None, gt=0)
    accepted_traveler_id: Optional[int] = Field(default=None, gt=0)
    description: Optional[str] = Field(default=None, min_length=1)
    pickup_city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    delivery_city: Optional[str] = Field(default=None, min_length=1, max_length=100)
    weight_kg: Optional[float] = Field(default=None, gt=0, le=30)
    size: Optional[str] = None
    reward: Optional[float] = Field(default=None, ge=0)
    deadline: Optional[date] = None
    status: Optional[str] = None


class PackageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender_id: int
    accepted_traveler_id: Optional[int]
    description: str
    pickup_city: str
    delivery_city: str
    weight_kg: float
    size: str
    reward: float
    deadline: date
    status: str
    created_at: datetime
    updated_at: datetime


class PackageStatusUpdate(BaseModel):
    status: str = Field(
        description="pending | accepted | in_transit | delivered | cancelled"
    )


class PackageAccept(BaseModel):
    traveler_id: int = Field(gt=0, description="ID of the traveler accepting the package")
