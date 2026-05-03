"""Celery tasks for email confirmation and password reset.

These tasks simulate sending emails by logging to the console.
In production you would swap the ``print`` calls for real SMTP via
``smtplib`` or an email service SDK.
"""

import logging
from datetime import datetime, timezone

from celery_app import celery

logger = logging.getLogger("packagego.email_tasks")


@celery.task(name="tasks.email_tasks.send_confirmation_email", bind=True, max_retries=3)
def send_confirmation_email(self, user_email: str, username: str, token: str):
    """Send an email-confirmation link to a newly registered user."""
    confirmation_url = f"http://localhost:8000/auth/confirm-email/{token}"

    logger.info("=" * 60)
    logger.info("📧  CONFIRMATION EMAIL")
    logger.info("-" * 60)
    logger.info(f"  To:      {user_email}")
    logger.info(f"  User:    {username}")
    logger.info(f"  Link:    {confirmation_url}")
    logger.info(f"  Sent at: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    # Simulate sending – in production replace with:
    #   import smtplib
    #   msg = MIMEText(f"Click to confirm: {confirmation_url}")
    #   ...
    print(
        f"\n[EMAIL TASK] Confirmation email sent to {user_email}\n"
        f"  Confirm URL: {confirmation_url}\n"
    )
    return {"status": "sent", "email": user_email}


@celery.task(name="tasks.email_tasks.send_password_reset_email", bind=True, max_retries=3)
def send_password_reset_email(self, user_email: str, username: str, token: str):
    """Send a password-reset link."""
    reset_url = f"http://localhost:8000/auth/reset-password/{token}"

    logger.info("=" * 60)
    logger.info("🔑  PASSWORD RESET EMAIL")
    logger.info("-" * 60)
    logger.info(f"  To:      {user_email}")
    logger.info(f"  User:    {username}")
    logger.info(f"  Link:    {reset_url}")
    logger.info(f"  Sent at: {datetime.now(timezone.utc).isoformat()}")
    logger.info("=" * 60)

    print(
        f"\n[EMAIL TASK] Password-reset email sent to {user_email}\n"
        f"  Reset URL: {reset_url}\n"
    )
    return {"status": "sent", "email": user_email}
