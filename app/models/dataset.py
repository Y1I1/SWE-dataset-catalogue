import enum
import uuid
from datetime import datetime, timezone

from app.db import db


class RefreshFrequency(enum.Enum):
    daily = "daily"
    weekly = "weekly"
    monthly = "monthly"
    quarterly = "quarterly"
    ad_hoc = "ad_hoc"


class Dataset(db.Model):
    __tablename__ = "datasets"
    __table_args__ = (db.CheckConstraint("row_count >= 0", name="chk_row_count_nonneg"),)

    id = db.Column(db.Uuid, primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    source_system_id = db.Column(db.Integer, db.ForeignKey("source_systems.id"), nullable=False)
    classification_id = db.Column(db.Integer, db.ForeignKey("classifications.id"), nullable=False)
    owner_id = db.Column(db.Uuid, db.ForeignKey("users.id"), nullable=False)
    row_count = db.Column(db.BigInteger)
    refresh_frequency = db.Column(
        db.Enum(RefreshFrequency, name="refresh_frequency"),
        nullable=False,
        default=RefreshFrequency.daily,
    )
    last_refreshed = db.Column(db.Date)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    source_system = db.relationship("SourceSystem")
    classification = db.relationship("Classification")
    owner = db.relationship("User")
