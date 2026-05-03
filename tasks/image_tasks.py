"""Celery task for image compression and storage.

Workflow:
  1. Receive raw image bytes and package_id.
  2. Log original size.
  3. Compress with Pillow (resize if > 1920px wide, JPEG quality=70).
  4. Log compressed size + compression ratio.
  5. Store compressed binary in PostgreSQL (PackageImage table).
  6. Optionally upload to MinIO and save URL.
"""

import io
import logging
from datetime import datetime, timezone

from celery_app import celery

logger = logging.getLogger("packagego.image_tasks")


def _get_sync_session():
    """Create a synchronous SQLAlchemy session for use in Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    return Session(engine)


@celery.task(name="tasks.image_tasks.compress_and_store_image", bind=True, max_retries=3)
def compress_and_store_image(self, package_id: int, image_bytes_hex: str, filename: str):
    """Compress an image and store it in the database (and optionally MinIO).

    ``image_bytes_hex`` is the hex-encoded raw image bytes (JSON-safe).
    """
    from PIL import Image
    import base64

    raw_bytes = bytes.fromhex(image_bytes_hex)
    original_size = len(raw_bytes)

    logger.info("=" * 60)
    logger.info("🖼️  IMAGE COMPRESSION TASK")
    logger.info("-" * 60)
    logger.info(f"  Package ID:    {package_id}")
    logger.info(f"  Filename:      {filename}")
    logger.info(f"  Original size: {original_size:,} bytes ({original_size / 1024:.1f} KB)")

    # Open image
    img = Image.open(io.BytesIO(raw_bytes))
    original_format = img.format or "JPEG"

    # Resize if wider than 1920px
    max_width = 1920
    if img.width > max_width:
        ratio = max_width / img.width
        new_size = (max_width, int(img.height * ratio))
        img = img.resize(new_size, Image.LANCZOS)
        logger.info(f"  Resized:       {img.width}x{img.height}")

    # Convert to RGB if necessary (for JPEG)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # Compress to JPEG quality=70
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=70, optimize=True)
    compressed_bytes = output.getvalue()
    compressed_size = len(compressed_bytes)

    ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0.0

    logger.info(f"  Compressed:    {compressed_size:,} bytes ({compressed_size / 1024:.1f} KB)")
    logger.info(f"  Compression:   {ratio:.1f}% reduction")
    logger.info("=" * 60)

    print(
        f"\n[IMAGE TASK] Package {package_id}:"
        f" {original_size:,}B → {compressed_size:,}B"
        f" ({ratio:.1f}% reduction)\n"
    )

    # Store in PostgreSQL
    _store_in_db(package_id, compressed_bytes, original_size, compressed_size, filename)

    # Try MinIO upload (optional)
    image_url = _upload_to_minio(package_id, compressed_bytes, filename)
    if image_url:
        _update_image_url(package_id, image_url)

    return {
        "package_id": package_id,
        "original_size": original_size,
        "compressed_size": compressed_size,
        "reduction_pct": round(ratio, 1),
        "minio_url": image_url,
    }


def _store_in_db(package_id: int, compressed_bytes: bytes, original_size: int, compressed_size: int, filename: str):
    """Save compressed image binary to PostgreSQL PackageImage table."""
    from sqlalchemy import text

    session = _get_sync_session()
    try:
        session.execute(
            text(
                "INSERT INTO packageimage (package_id, image_data, original_size_bytes, "
                "compressed_size_bytes, filename, created_at) "
                "VALUES (:pid, :data, :orig, :comp, :fname, :ts)"
            ),
            {
                "pid": package_id,
                "data": compressed_bytes,
                "orig": original_size,
                "comp": compressed_size,
                "fname": filename,
                "ts": datetime.now(timezone.utc),
            },
        )
        session.commit()
        logger.info("  Stored in PostgreSQL ✓")
    except Exception as exc:
        session.rollback()
        logger.error("  DB store failed: %s", exc)
        raise
    finally:
        session.close()


def _upload_to_minio(package_id: int, compressed_bytes: bytes, filename: str) -> str | None:
    """Upload compressed image to MinIO and return the URL."""
    try:
        from minio import Minio
        from config import get_settings

        settings = get_settings()
        client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_use_ssl,
        )

        bucket = settings.minio_bucket
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)

        object_name = f"packages/{package_id}/{filename}"
        data_stream = io.BytesIO(compressed_bytes)
        client.put_object(
            bucket,
            object_name,
            data_stream,
            length=len(compressed_bytes),
            content_type="image/jpeg",
        )

        url = f"http://{settings.minio_endpoint}/{bucket}/{object_name}"
        logger.info("  Uploaded to MinIO: %s", url)
        return url
    except Exception as exc:
        logger.warning("  MinIO upload skipped: %s", exc)
        return None


def _update_image_url(package_id: int, image_url: str):
    """Update the image URL in the PackageImage table after MinIO upload."""
    from sqlalchemy import text

    session = _get_sync_session()
    try:
        session.execute(
            text(
                "UPDATE packageimage SET image_url = :url "
                "WHERE id = ("
                "  SELECT id FROM packageimage "
                "  WHERE package_id = :pid AND image_url IS NULL "
                "  ORDER BY id DESC LIMIT 1"
                ")"
            ),
            {"url": image_url, "pid": package_id},
        )
        session.commit()
    except Exception:
        # Non-critical – URL is optional
        session.rollback()
    finally:
        session.close()
