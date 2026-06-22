import enum
import uuid
from datetime import datetime, timezone

from app.db import db


class RequestStatus(enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class AccessRequest(db.Model):
    __tablename__ = "access_requests"
    __table_args__ = (
        db.CheckConstraint(
            "(status = 'pending' AND decided_by IS NULL AND decided_at IS NULL) OR "
            "(status != 'pending' AND decided_by IS NOT NULL AND decided_at IS NOT NULL)",
            name="chk_decided",
        ),
        db.Index(
            "uq_pending_request",
            "dataset_id",
            "requested_by",
            unique=True,
            postgresql_where=db.text("status = 'pending'"),
            sqlite_where=db.text("status = 'pending'"),
        ),
    )

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    dataset_id = db.Column(
        db.Uuid, db.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False
    )
    requested_by = db.Column(db.Uuid, db.ForeignKey("users.id"), nullable=False)
    reason = db.Column(db.Text, nullable=False)
    status = db.Column(
        db.Enum(RequestStatus, name="request_status"), nullable=False, default=RequestStatus.pending
    )
    decided_by = db.Column(db.Uuid, db.ForeignKey("users.id"))
    decided_at = db.Column(db.DateTime(timezone=True))
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    dataset = db.relationship("Dataset", foreign_keys=[dataset_id])
    requester = db.relationship("User", foreign_keys=[requested_by])
