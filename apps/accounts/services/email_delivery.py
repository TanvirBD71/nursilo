"""Email delivery abstraction — no third-party requirement; never log tokens."""
from __future__ import annotations

import logging

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


class EmailDeliveryService:
    """Thin wrapper around Django email backends (console/locmem/SMTP)."""

    @staticmethod
    def send(*, subject: str, message: str, recipient: str) -> int:
        # Intentionally do not include tokens in logs.
        logger.info("Sending email subject=%s to_domain=%s", subject, _email_domain(recipient))
        return send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            fail_silently=False,
        )


def _email_domain(email: str) -> str:
    if "@" not in email:
        return "unknown"
    return email.split("@", 1)[1]
