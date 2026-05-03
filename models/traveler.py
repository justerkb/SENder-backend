from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.trip import Trip
    from models.package import Package
    from models.review import Review
    from models.user import User


class TravelerBase(SQLModel):
    name: str = Field(min_length=1, max_length=100)
    email: str = Field(min_length=1, max_length=100)
    phone: str = Field(min_length=1, max_length=50)
    bio: str


class Traveler(TravelerBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional["User"] = Relationship(
        back_populates="traveler_profile",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    trips: List["Trip"] = Relationship(
        back_populates="traveler",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    accepted_packages: List["Package"] = Relationship(
        back_populates="accepted_traveler",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    reviews: List["Review"] = Relationship(
        back_populates="traveler",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
