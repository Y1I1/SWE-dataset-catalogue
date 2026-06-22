from app.models import AccessRequest, Dataset, RequestStatus
from tests.conftest import get_csrf, login


def test_catalogue_lists_datasets(client, viewer_user):
    login(client, viewer_user.email)
    response = client.get("/catalogue/")
    assert response.status_code == 200
    assert b"Customer Master" in response.data


def test_viewer_can_view_public_dataset(client, viewer_user, app):
    login(client, viewer_user.email)
    with app.app_context():
        dataset = Dataset.query.filter_by(name="Customer Master").one()
    response = client.get(f"/catalogue/datasets/{dataset.id}")
    assert response.status_code == 200
    assert b"Customer Master" in response.data


def test_viewer_blocked_from_restricted_dataset(client, viewer_user, app):
    login(client, viewer_user.email)
    with app.app_context():
        dataset = Dataset.query.filter_by(name="Customer PII").one()
    response = client.get(f"/catalogue/datasets/{dataset.id}")
    assert b"Request access" in response.data


def test_viewer_submits_access_request(client, viewer_user, app):
    login(client, viewer_user.email)
    with app.app_context():
        dataset = Dataset.query.filter_by(name="Fraud Alerts").one()
    response = client.post(
        f"/catalogue/datasets/{dataset.id}/request-access",
        data={
            "csrf_token": get_csrf(client, f"/catalogue/datasets/{dataset.id}"),
            "reason": "Need Fraud Alerts for compliance dashboard work.",
        },
        follow_redirects=True,
    )
    assert b"Access request submitted" in response.data


def test_viewer_cannot_access_admin(client, viewer_user):
    login(client, viewer_user.email)
    response = client.get("/admin/", follow_redirects=False)
    assert response.status_code == 403


def test_admin_approves_request(client, admin_user, viewer_user, app):
    login(client, viewer_user.email)
    with app.app_context():
        dataset = Dataset.query.filter_by(name="Sales Pipeline").one()
    client.post(
        f"/catalogue/datasets/{dataset.id}/request-access",
        data={
            "csrf_token": get_csrf(client, f"/catalogue/datasets/{dataset.id}"),
            "reason": "Need Sales Pipeline for quarterly reporting review.",
        },
        follow_redirects=True,
    )

    login(client, admin_user.email)
    with app.app_context():
        pending = AccessRequest.query.filter_by(status=RequestStatus.pending).first()
        request_id = pending.id

    response = client.post(
        f"/admin/access-requests/{request_id}/approve",
        data={"csrf_token": get_csrf(client, "/admin/access-requests")},
        follow_redirects=True,
    )
    assert b"approved" in response.data

    login(client, viewer_user.email)
    detail = client.get(f"/catalogue/datasets/{dataset.id}")
    assert b"Request access" not in detail.data
