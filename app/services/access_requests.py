from __future__ import annotations

from datetime import datetime, timezone

from app.db import db
from app.models import AccessRequest, Dataset, RequestStatus, User
from app.models.audit_event import AuditAction
from app.services.audit import write_audit
from app.services.permissions import can_view_dataset


class AccessRequestError(Exception):
    pass


def list_user_requests(user: User) -> list[AccessRequest]:
    return (
        AccessRequest.query.filter_by(requested_by=user.id)
        .order_by(AccessRequest.created_at.desc())
        .all()
    )


def list_all_requests(status: RequestStatus | None = None) -> list[AccessRequest]:
    query = AccessRequest.query.order_by(AccessRequest.created_at.desc())
    if status is not None:
        query = query.filter_by(status=status)
    return query.all()


def create_request(user: User, dataset: Dataset, reason: str) -> AccessRequest:
    if can_view_dataset(user, dataset):
        raise AccessRequestError("You already have access to this dataset.")

    existing = AccessRequest.query.filter_by(
        dataset_id=dataset.id,
        requested_by=user.id,
        status=RequestStatus.pending,
    ).first()
    if existing:
        raise AccessRequestError("You already have a pending request for this dataset.")

    access_request = AccessRequest(
        dataset_id=dataset.id,
        requested_by=user.id,
        reason=reason.strip(),
    )
    db.session.add(access_request)
    write_audit(
        AuditAction.access_request_created,
        target_type="access_request",
        target_id=dataset.id,
        actor_id=user.id,
        meta={"dataset_name": dataset.name},
    )
    db.session.commit()
    return access_request


def get_request_for_user(request_id, user: User) -> AccessRequest | None:
    return AccessRequest.query.filter_by(id=request_id, requested_by=user.id).first()


def decide_request(
    access_request: AccessRequest,
    admin: User,
    decision: RequestStatus,
) -> AccessRequest:
    if access_request.status != RequestStatus.pending:
        raise AccessRequestError("Only pending requests can be approved or rejected.")
    if decision not in (RequestStatus.approved, RequestStatus.rejected):
        raise AccessRequestError("Invalid decision.")

    access_request.status = decision
    access_request.decided_by = admin.id
    access_request.decided_at = datetime.now(timezone.utc)

    action = (
        AuditAction.access_request_approved
        if decision == RequestStatus.approved
        else AuditAction.access_request_rejected
    )
    write_audit(
        action,
        target_type="access_request",
        target_id=access_request.id,
        actor_id=admin.id,
        meta={"dataset_id": str(access_request.dataset_id)},
    )
    db.session.commit()
    return access_request
