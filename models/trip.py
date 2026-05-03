from datetime import datetime, date
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship

from models.traveler import Traveler  # noqa: F401 – needed for FK resolution


class TripBase(SQLModel):
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


class Trip(TripBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    traveler_id: int = Field(foreign_key="traveler.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    traveler: "Traveler" = Relationship(
        back_populates="trips",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
