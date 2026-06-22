from datetime import datetime, timezone

from app.db import db


class SourceSystem(db.Model):
    __tablename__ = "source_systems"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text)
    hostname = db.Column(db.String(255))
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
