"""Append-only audit event writer. Never exposes edit or delete operations."""

import json

from app.db import db
from app.models.audit_event import AuditAction, AuditEvent


def write_audit(
    action: AuditAction,
    target_type: str,
    target_id: str | None = None,
    actor_id=None,
    meta: dict | None = None,
) -> None:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        meta=json.dumps(meta, default=str) if meta else None,
    )
    db.session.add(event)
