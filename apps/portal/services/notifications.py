"""Notification list/read presentation — no notification engine (docs/05 §12)."""
from __future__ import annotations

from apps.notifications.models import Notification


class NotificationPresentationService:
    @staticmethod
    def list_for_user(user, *, limit: int = 50):
        return list(
            Notification.objects.filter(user=user).order_by("-created_at")[:limit]
        )

    @staticmethod
    def unread_count(user) -> int:
        return Notification.objects.filter(user=user, is_read=False).count()

    @staticmethod
    def recent_for_dashboard(user, *, limit: int = 5):
        return list(
            Notification.objects.filter(user=user).order_by("-created_at")[:limit]
        )

    @staticmethod
    def get_own(user, notification_id) -> Notification | None:
        try:
            return Notification.objects.get(id=notification_id, user=user)
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def mark_read(*, user, notification: Notification) -> Notification:
        if notification.user_id != user.id:
            raise PermissionError("Permission denied.")
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return notification
