from datetime import date, timedelta

import pytest

from app.models import Classification, Dataset, RequestStatus
from app.services import access_requests as ar_service
from app.services.admin import (
    AdminValidationError,
    classification_in_use,
    parse_optional_date,
    validate_dataset_name,
    validate_unique_label,
)
from app.services.catalogue import get_active_dataset, search_datasets
from app.services.permissions import can_view_dataset


def test_can_view_dataset(viewer_user, app):
    with app.app_context():
        public = Dataset.query.filter_by(name="Customer Master").one()
        restricted = Dataset.query.filter_by(name="Customer PII").one()
        assert can_view_dataset(viewer_user, public) is True
        assert can_view_dataset(viewer_user, restricted) is False


def test_admin_validation(app):
    with app.app_context():
        assert validate_dataset_name("Unique Name") == "Unique Name"
        assert classification_in_use(
            Dataset.query.filter_by(name="Customer Master").one().classification_id
        )
        with pytest.raises(AdminValidationError):
            validate_unique_label(Classification, "Public")
        with pytest.raises(AdminValidationError):
            validate_dataset_name("   ")
        with pytest.raises(AdminValidationError):
            parse_optional_date("bad", "Last refreshed")
        future = (date.today() + timedelta(days=1)).isoformat()
        with pytest.raises(AdminValidationError):
            parse_optional_date(future, "Last refreshed")


def test_access_request_workflow(viewer_user, admin_user, app):
    with app.app_context():
        dataset = Dataset.query.filter_by(name="Revenue Forecast").one()
        req = ar_service.create_request(viewer_user, dataset, "Need for reporting.")
        assert req.status == RequestStatus.pending
        with pytest.raises(ar_service.AccessRequestError):
            ar_service.create_request(viewer_user, dataset, "Duplicate request.")
        ar_service.decide_request(req, admin_user, RequestStatus.approved)
        with pytest.raises(ar_service.AccessRequestError):
            ar_service.decide_request(req, admin_user, RequestStatus.rejected)
        assert can_view_dataset(viewer_user, dataset) is True


def test_search_and_active_dataset(app):
    with app.app_context():
        assert search_datasets(classification="Public")
        dataset = Dataset.query.filter_by(name="Customer Master").one()
        dataset.is_active = False
        from app.db import db

        db.session.commit()
        assert get_active_dataset(dataset.id) is None
