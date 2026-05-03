from datetime import datetime
from typing import Optional, List, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.traveler import Traveler
    from models.sender import Sender
    from models.notification import Notification


class UserBase(SQLModel):
    username: str = Field(min_length=3, max_length=50, unique=True)
    email: str = Field(min_length=5, max_length=100, unique=True)
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    role: str = Field(
        default="user",
        description="user | admin",
    )
    is_active: bool = Field(default=True)


class User(UserBase, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    password_hash: str = Field(max_length=255)
    email_confirmed: bool = Field(default=False)
    confirmation_token: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    traveler_profile: Optional["Traveler"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin", "uselist": False},
    )
    sender_profile: Optional["Sender"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin", "uselist": False},
    )
    notifications: List["Notification"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
