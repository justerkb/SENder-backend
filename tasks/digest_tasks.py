"""Periodic Celery Beat task: delivery notifications digest.

Runs every hour (configured in celery_app.py beat_schedule).
Queries packages that changed status in the last hour and creates
summary notifications for affected users.
"""

import logging
from datetime import datetime, timedelta, timezone

from celery_app import celery

logger = logging.getLogger("packagego.digest_tasks")


def _get_sync_session():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from config import get_settings

    settings = get_settings()
    engine = create_engine(settings.database_url_sync)
    return Session(engine)


@celery.task(name="tasks.digest_tasks.delivery_digest")
def delivery_digest():
    """Aggregate package status changes from the last hour and notify users.

    For each affected user (sender or accepted traveler) a summary
    notification is inserted into the ``notification`` table.
    """
    from sqlalchemy import text

    session = _get_sync_session()
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

    try:
        # Find packages updated in the last hour
        rows = session.execute(
            text(
                "SELECT p.id, p.description, p.status, p.sender_id, "
                "       p.accepted_traveler_id, s.user_id AS sender_user_id, "
                "       t.user_id AS traveler_user_id "
                "FROM package p "
                "JOIN sender s ON s.id = p.sender_id "
                "LEFT JOIN traveler t ON t.id = p.accepted_traveler_id "
                "WHERE p.updated_at >= :since"
            ),
            {"since": one_hour_ago},
        ).fetchall()

        if not rows:
            logger.info("[DIGEST] No package updates in the last hour.")
            print("[DIGEST] No package updates in the last hour.")
            return {"notifications_created": 0}

        # Group updates by user
        user_updates: dict[int, list[str]] = {}
        for row in rows:
            msg = f"Package #{row.id} ({row.description[:30]}) → {row.status}"
            # Notify the sender
            if row.sender_user_id:
                user_updates.setdefault(row.sender_user_id, []).append(msg)
            # Notify the traveler (if assigned)
            if row.traveler_user_id:
                user_updates.setdefault(row.traveler_user_id, []).append(msg)

        # Insert notifications
        created = 0
        now = datetime.now(timezone.utc)
        for user_id, messages in user_updates.items():
            summary = "Hourly Delivery Digest:\n" + "\n".join(f"  • {m}" for m in messages)
            session.execute(
                text(
                    "INSERT INTO notification (user_id, title, message, notification_type, is_read, created_at) "
                    "VALUES (:uid, :title, :msg, :ntype, false, :ts)"
                ),
                {
                    "uid": user_id,
                    "title": "📦 Delivery Digest",
                    "msg": summary,
                    "ntype": "system",
                    "ts": now,
                },
            )
            created += 1

        session.commit()

        logger.info("[DIGEST] Created %d digest notifications for %d packages.", created, len(rows))
        print(f"[DIGEST] Created {created} digest notifications for {len(rows)} package updates.")
        return {"notifications_created": created, "packages_updated": len(rows)}

    except Exception as exc:
        session.rollback()
        logger.error("[DIGEST] Failed: %s", exc)
        raise
    finally:
        session.close()
