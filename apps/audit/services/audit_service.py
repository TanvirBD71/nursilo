"""Append-only audit helper (docs/03 §10, docs/05 AuditService)."""
from __future__ import annotations

from typing import Any

from apps.audit.models import AuditEvent


class AuditService:
    @staticmethod
    def record(
        *,
        action: str,
        actor_user=None,
        target_type: str = "",
        target_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        safe_meta = dict(metadata or {})
        # Never persist secrets if a caller accidentally passes them
        for forbidden in (
            "password",
            "token",
            "raw_token",
            "session_key",
            "csrf",
            "store_passwd",
            "store_pass",
            "sslcommerz_store_passwd",
        ):
            safe_meta.pop(forbidden, None)
        return AuditEvent.objects.create(
            actor_user=actor_user,
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else "",
            metadata=safe_meta,
        )
