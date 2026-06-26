import enum
from datetime import datetime, timezone

from app.db import db


class AuditAction(enum.Enum):
    access_request_created = "access_request_created"
    access_request_approved = "access_request_approved"
    access_request_rejected = "access_request_rejected"
    dataset_created = "dataset_created"
    dataset_updated = "dataset_updated"
    dataset_deactivated = "dataset_deactivated"
    classification_created = "classification_created"
    classification_updated = "classification_updated"
    classification_deleted = "classification_deleted"
    source_system_created = "source_system_created"
    source_system_updated = "source_system_updated"
    source_system_deleted = "source_system_deleted"
    user_role_changed = "user_role_changed"
    user_activated = "user_activated"
    user_deactivated = "user_deactivated"


class AuditEvent(db.Model):
    """Append-only audit log. No UPDATE or DELETE routes exist for this table."""

    __tablename__ = "audit_events"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Uuid, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = db.Column(db.Enum(AuditAction, name="audit_action"), nullable=False, index=True)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.String(100), nullable=True)
    meta = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
