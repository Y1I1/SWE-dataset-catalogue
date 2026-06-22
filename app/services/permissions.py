from app.models import AccessRequest, RequestStatus, User, UserRole

CONFIDENTIAL_RANK = 3


def can_view_dataset(user: User, dataset) -> bool:
    if user.role == UserRole.admin:
        return True
    if dataset.classification.rank < CONFIDENTIAL_RANK:
        return True
    return (
        AccessRequest.query.filter_by(
            dataset_id=dataset.id,
            requested_by=user.id,
            status=RequestStatus.approved,
        ).first()
        is not None
    )
