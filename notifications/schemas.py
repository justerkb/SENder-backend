from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NotificationCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1)
    notification_type: str = Field(
        default="info",
        description="info | package_accepted | package_delivered | review | system",
    )


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    message: str
    notification_type: str
    is_read: bool
    created_at: datetime


class NotificationUpdate(BaseModel):
    is_read: Optional[bool] = None
