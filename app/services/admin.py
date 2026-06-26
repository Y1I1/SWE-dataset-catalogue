from __future__ import annotations

from datetime import date

from app.db import db
from app.models import Dataset, RefreshFrequency


class AdminValidationError(Exception):
    pass


def classification_in_use(classification_id: int) -> bool:
    count = db.session.scalar(
        db.select(db.func.count())
        .select_from(Dataset)
        .where(Dataset.is_active.is_(True), Dataset.classification_id == classification_id)
    )
    return (count or 0) > 0


def source_system_in_use(source_system_id: int) -> bool:
    count = db.session.scalar(
        db.select(db.func.count())
        .select_from(Dataset)
        .where(Dataset.is_active.is_(True), Dataset.source_system_id == source_system_id)
    )
    return (count or 0) > 0


def parse_optional_date(value, field: str) -> date | None:
    if value in (None, ""):
        return None
    if isinstance(value, date):
        parsed = value
    else:
        try:
            parsed = date.fromisoformat(str(value))
        except ValueError as exc:
            raise AdminValidationError(f"{field} must be a valid ISO date (YYYY-MM-DD).") from exc
    if parsed > date.today():
        raise AdminValidationError(f"{field} cannot be in the future.")
    return parsed


def validate_dataset_name(name: str, existing: Dataset | None = None) -> str:
    name = name.strip()
    if not name:
        raise AdminValidationError("Name is required.")
    duplicate = Dataset.query.filter(Dataset.name.ilike(name))
    if existing:
        duplicate = duplicate.filter(Dataset.id != existing.id)
    if duplicate.first():
        raise AdminValidationError("A dataset with that name already exists.")
    return name


def validate_unique_name(model, name: str, existing_id: int | None = None) -> str:
    name = name.strip()
    if not name:
        raise AdminValidationError("Name is required.")
    query = model.query.filter(model.name.ilike(name))
    if existing_id is not None:
        query = query.filter(model.id != existing_id)
    if query.first():
        raise AdminValidationError("That name is already in use.")
    return name


def validate_unique_label(model, label: str, existing_id: int | None = None) -> str:
    label = label.strip()
    if not label:
        raise AdminValidationError("Label is required.")
    query = model.query.filter(model.label.ilike(label))
    if existing_id is not None:
        query = query.filter(model.id != existing_id)
    if query.first():
        raise AdminValidationError("That label is already in use.")
    return label


def validate_unique_rank(rank: int, existing_id: int | None = None) -> int:
    from app.models import Classification

    query = Classification.query.filter(Classification.rank == rank)
    if existing_id is not None:
        query = query.filter(Classification.id != existing_id)
    if query.first():
        raise AdminValidationError(f"Rank {rank} is already assigned to another classification.")
    return rank


def parse_refresh_frequency(value: str) -> RefreshFrequency:
    try:
        return RefreshFrequency(value)
    except ValueError as exc:
        raise AdminValidationError("Refresh frequency is invalid.") from exc
