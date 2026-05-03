"""Image upload and retrieval routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, UploadFile, File, status
from fastapi.responses import Response
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from auth.deps import get_current_user
from models import PackageImage
from errors.exceptions import NotFoundException, BadRequestException

router = APIRouter(tags=["images"])


@router.post(
    "/packages/{package_id}/image",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload an image for a package (auth, triggers background compression)",
)
async def upload_image(
    package_id: Annotated[int, Path(gt=0)],
    file: UploadFile = File(...),
    current_user: Annotated[dict, Depends(get_current_user)] = None,
    session: AsyncSession = Depends(get_session),
):
    """Upload an image for a package.

    The image is sent to a Celery background task for compression.
    Original size and filename are logged; compressed result is stored in
    PostgreSQL and optionally uploaded to MinIO.
    """
    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "image/webp", "image/gif"}
    if file.content_type not in allowed_types:
        raise BadRequestException(
            detail=f"Invalid file type '{file.content_type}'. Allowed: {', '.join(allowed_types)}"
        )

    # Read file bytes
    contents = await file.read()
    if len(contents) > 10 * 1024 * 1024:  # 10 MB limit
        raise BadRequestException(detail="File too large. Maximum size is 10 MB.")

    # Dispatch Celery task
    from tasks.image_tasks import compress_and_store_image

    task = compress_and_store_image.delay(
        package_id=package_id,
        image_bytes_hex=contents.hex(),
        filename=file.filename or f"package_{package_id}.jpg",
    )

    return {
        "detail": "Image upload accepted and queued for compression",
        "task_id": task.id,
        "package_id": package_id,
        "original_size_bytes": len(contents),
        "filename": file.filename,
    }


@router.get(
    "/packages/{package_id}/image",
    summary="Get compressed image for a package",
)
async def get_image(
    package_id: Annotated[int, Path(gt=0)],
    session: AsyncSession = Depends(get_session),
):
    """Retrieve the most recent compressed image for a package."""
    from sqlmodel import select

    stmt = (
        select(PackageImage)
        .where(PackageImage.package_id == package_id)
        .order_by(PackageImage.id.desc())
    )
    result = await session.exec(stmt)
    image = result.first()

    if not image:
        raise NotFoundException(detail=f"No image found for package {package_id}")

    if image.image_data:
        return Response(
            content=image.image_data,
            media_type="image/jpeg",
            headers={
                "Content-Disposition": f'inline; filename="{image.filename}"',
                "X-Original-Size": str(image.original_size_bytes),
                "X-Compressed-Size": str(image.compressed_size_bytes),
            },
        )

    # If image_data is NULL but URL exists (MinIO only)
    if image.image_url:
        return {
            "image_url": image.image_url,
            "original_size_bytes": image.original_size_bytes,
            "compressed_size_bytes": image.compressed_size_bytes,
        }

    raise NotFoundException(detail="Image data not available")
