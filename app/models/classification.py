from app.db import db


class Classification(db.Model):
    __tablename__ = "classifications"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(100), unique=True, nullable=False)
    rank = db.Column(db.Integer, unique=True, nullable=False)
    description = db.Column(db.Text)
