"""UserSession lifecycle — concurrent cap, timeouts, revocation (docs/07)."""
from __future__ import annotations

from django.contrib.sessions.models import Session
from django.db import transaction
from django.utils import timezone

from apps.accounts.exceptions import SessionLimitExceeded
from apps.accounts.models import UserAccount, UserSession, UserSessionStatus
from apps.accounts.policy import (
    FOURTH_LOGIN_BEHAVIOR,
    MAX_CONCURRENT_SESSIONS,
    SESSION_ABSOLUTE_TIMEOUT,
    SESSION_IDLE_TIMEOUT,
    SESSION_REMEMBER_IDLE_TIMEOUT,
    SESSION_TRACKING_KEY,
)
from apps.audit.services import AuditService


def parse_user_agent(user_agent: str) -> tuple[str, str, str]:
    """Best-effort browser/OS/device name — not invasive fingerprinting."""
    ua = user_agent or ""
    browser = "Browser"
    if "Edg/" in ua:
        browser = "Edge"
    elif "Chrome/" in ua and "Chromium" not in ua:
        browser = "Chrome"
    elif "Firefox/" in ua:
        browser = "Firefox"
    elif "Safari/" in ua and "Chrome/" not in ua:
        browser = "Safari"
    elif "OPR/" in ua or "Opera" in ua:
        browser = "Opera"

    os_name = "Unknown OS"
    if "Windows" in ua:
        os_name = "Windows"
    elif "Android" in ua:
        os_name = "Android"
    elif "iPhone" in ua or "iPad" in ua:
        os_name = "iOS"
    elif "Mac OS X" in ua or "Macintosh" in ua:
        os_name = "macOS"
    elif "Linux" in ua:
        os_name = "Linux"

    device_name = f"{browser} on {os_name}"
    return device_name, browser, os_name


def client_ip(request) -> str | None:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip() or None
    return request.META.get("REMOTE_ADDR") or None


class SessionService:
    @staticmethod
    def active_sessions_qs(user: UserAccount):
        return UserSession.objects.filter(user=user, status=UserSessionStatus.ACTIVE)

    @classmethod
    @transaction.atomic
    def enforce_concurrent_limit(cls, user: UserAccount) -> None:
        active = list(
            cls.active_sessions_qs(user).select_for_update().order_by("created_time")
        )
        if len(active) < MAX_CONCURRENT_SESSIONS:
            return
        if FOURTH_LOGIN_BEHAVIOR == "reject":
            raise SessionLimitExceeded()
        # Default: terminate oldest
        oldest = active[0]
        cls.revoke_session(oldest, reason="concurrent_limit", actor=user)

    @classmethod
    @transaction.atomic
    def create_for_request(cls, *, user: UserAccount, request, remember_me: bool = False) -> UserSession:
        cls.enforce_concurrent_limit(user)
        session_key = request.session.session_key
        if not session_key:
            request.session.save()
            session_key = request.session.session_key

        now = timezone.now()
        ua = request.META.get("HTTP_USER_AGENT", "")
        device_name, browser, os_name = parse_user_agent(ua)
        # Replace any stale row for this Django session key
        UserSession.objects.filter(session_key=session_key).delete()
        user_session = UserSession.objects.create(
            user=user,
            session_key=session_key,
            device_name=device_name,
            browser=browser,
            operating_system=os_name,
            ip_address=client_ip(request),
            user_agent=ua[:2000],
            created_time=now,
            last_activity=now,
            expires_at=now + SESSION_ABSOLUTE_TIMEOUT,
            remember_me=bool(remember_me),
            status=UserSessionStatus.ACTIVE,
        )
        request.session[SESSION_TRACKING_KEY] = str(user_session.id)
        cls.apply_cookie_expiry(request, remember_me=bool(remember_me))
        return user_session

    @staticmethod
    def apply_cookie_expiry(request, *, remember_me: bool) -> None:
        """Django session cookie lifetime — not a second auth token."""
        if remember_me:
            request.session.set_expiry(int(SESSION_ABSOLUTE_TIMEOUT.total_seconds()))
        # Unchecked: leave Django's existing session cookie policy unchanged.

    @classmethod
    def idle_timeout_for(cls, user_session: UserSession):
        if user_session.remember_me:
            return SESSION_REMEMBER_IDLE_TIMEOUT
        return SESSION_IDLE_TIMEOUT

    @classmethod
    def touch(cls, user_session: UserSession, *, now=None) -> UserSession | None:
        now = now or timezone.now()
        if user_session.status != UserSessionStatus.ACTIVE:
            return None
        if now >= user_session.expires_at:
            cls.mark_expired(user_session)
            return None
        idle_deadline = user_session.last_activity + cls.idle_timeout_for(user_session)
        if now >= idle_deadline:
            cls.mark_expired(user_session)
            return None
        user_session.last_activity = now
        user_session.save(update_fields=["last_activity", "updated_at"])
        return user_session

    @classmethod
    def get_current(cls, request) -> UserSession | None:
        sid = request.session.get(SESSION_TRACKING_KEY)
        if not sid:
            # Fallback: match Django session key
            key = request.session.session_key
            if not key:
                return None
            return (
                UserSession.objects.filter(
                    session_key=key, status=UserSessionStatus.ACTIVE
                )
                .select_related("user")
                .first()
            )
        return (
            UserSession.objects.filter(id=sid, status=UserSessionStatus.ACTIVE)
            .select_related("user")
            .first()
        )

    @classmethod
    def revoke_session(
        cls, user_session: UserSession, *, reason: str, actor=None
    ) -> None:
        if user_session.status != UserSessionStatus.ACTIVE:
            return
        user_session.status = UserSessionStatus.REVOKED
        user_session.save(update_fields=["status", "updated_at"])
        Session.objects.filter(session_key=user_session.session_key).delete()
        AuditService.record(
            action="session_revoked",
            actor_user=actor,
            target_type="user_session",
            target_id=str(user_session.id),
            metadata={"reason": reason, "user_id": str(user_session.user_id)},
        )

    @classmethod
    def mark_expired(cls, user_session: UserSession) -> None:
        if user_session.status != UserSessionStatus.ACTIVE:
            return
        user_session.status = UserSessionStatus.EXPIRED
        user_session.save(update_fields=["status", "updated_at"])
        Session.objects.filter(session_key=user_session.session_key).delete()

    @classmethod
    def revoke_all_for_user(
        cls,
        user: UserAccount,
        *,
        reason: str,
        actor=None,
        except_session: UserSession | None = None,
    ) -> int:
        qs = cls.active_sessions_qs(user)
        if except_session is not None:
            qs = qs.exclude(pk=except_session.pk)
        count = 0
        for sess in qs:
            cls.revoke_session(sess, reason=reason, actor=actor)
            count += 1
        return count

    @classmethod
    def rotate_current_session_key(cls, request, user_session: UserSession) -> UserSession:
        """After privilege/password changes — rotate Django session id (docs/07 §6.5)."""
        old_key = user_session.session_key
        request.session.cycle_key()
        new_key = request.session.session_key
        Session.objects.filter(session_key=old_key).delete()
        user_session.session_key = new_key
        user_session.last_activity = timezone.now()
        user_session.save(update_fields=["session_key", "last_activity", "updated_at"])
        request.session[SESSION_TRACKING_KEY] = str(user_session.id)
        return user_session
