from __future__ import annotations

from app.db import db
from app.models import Classification, Dataset, SourceSystem


def search_datasets(
    *,
    q: str | None = None,
    classification: str | None = None,
    source_system: str | None = None,
    sort: str = "name",
    active_only: bool = True,
) -> list[Dataset]:
    query = Dataset.query
    if active_only:
        query = query.filter_by(is_active=True)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(db.or_(Dataset.name.ilike(like), Dataset.description.ilike(like)))

    if classification:
        query = query.join(Classification).filter(
            Classification.label.ilike(classification.strip())
        )

    if source_system:
        query = query.join(SourceSystem).filter(SourceSystem.name.ilike(source_system.strip()))

    if sort == "last_refreshed":
        query = query.order_by(Dataset.last_refreshed.desc().nullslast(), Dataset.name)
    else:
        query = query.order_by(Dataset.name)

    return query.all()


def get_active_dataset(dataset_id) -> Dataset | None:
    dataset = db.session.get(Dataset, dataset_id)
    if dataset is None or not dataset.is_active:
        return None
    return dataset
