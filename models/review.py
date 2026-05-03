from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Relationship

from models.sender import Sender  # noqa: F401 – needed for FK resolution
from models.traveler import Traveler  # noqa: F401 – needed for FK resolution
from models.package import Package  # noqa: F401 – needed for FK resolution


class ReviewBase(SQLModel):
    rating: int = Field(ge=1, le=5)
    comment: str


class Review(ReviewBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sender_id: int = Field(foreign_key="sender.id")
    traveler_id: int = Field(foreign_key="traveler.id")
    package_id: int = Field(foreign_key="package.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    sender: "Sender" = Relationship(
        back_populates="reviews",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    traveler: "Traveler" = Relationship(
        back_populates="reviews",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    package: "Package" = Relationship(
        back_populates="reviews",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
