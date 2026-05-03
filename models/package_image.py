"""PackageImage model – stores compressed images for packages."""

from datetime import datetime
from typing import Optional

from sqlmodel import SQLModel, Field, Column
from sqlalchemy import LargeBinary


class PackageImageBase(SQLModel):
    package_id: int = Field(foreign_key="package.id")
    filename: str = Field(max_length=255)
    original_size_bytes: int
    compressed_size_bytes: int
    image_url: Optional[str] = Field(default=None, max_length=500)


class PackageImage(PackageImageBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    image_data: Optional[bytes] = Field(
        default=None,
        sa_column=Column(LargeBinary, nullable=True),
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
