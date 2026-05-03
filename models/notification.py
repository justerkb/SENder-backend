from datetime import datetime
from typing import Optional, TYPE_CHECKING

from sqlmodel import SQLModel, Field, Relationship

if TYPE_CHECKING:
    from models.user import User


class NotificationBase(SQLModel):
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)
    notification_type: str = Field(
        default="info",
        description="info | package_accepted | package_delivered | review | system",
    )
    is_read: bool = Field(default=False)


class Notification(NotificationBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: "User" = Relationship(
        back_populates="notifications",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
