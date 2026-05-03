from datetime import datetime, date
from typing import Optional, List, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.review import Review

from models.sender import Sender  # noqa: F401 – needed for FK resolution
from models.traveler import Traveler  # noqa: F401 – needed for FK resolution


class PackageBase(SQLModel):
    description: str
    pickup_city: str = Field(min_length=1, max_length=100)
    delivery_city: str = Field(min_length=1, max_length=100)
    weight_kg: float = Field(gt=0, le=30)
    size: str = Field(description="small | medium | large")
    reward: float = Field(ge=0)
    deadline: date
    status: str = Field(
        default="pending",
        description="pending | accepted | in_transit | delivered | cancelled",
    )


class Package(PackageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    sender_id: int = Field(foreign_key="sender.id")
    accepted_traveler_id: Optional[int] = Field(
        default=None, foreign_key="traveler.id"
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    sender: "Sender" = Relationship(
        back_populates="packages",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    accepted_traveler: Optional["Traveler"] = Relationship(
        back_populates="accepted_packages",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    reviews: List["Review"] = Relationship(
        back_populates="package",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
