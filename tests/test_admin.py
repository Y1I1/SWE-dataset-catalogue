import uuid

from app.models import Classification, SourceSystem, User
from tests.conftest import extract_csrf, get_csrf, login


def test_admin_creates_dataset(client, admin_user, app):
    login(client, admin_user.email)
    with app.app_context():
        classification = Classification.query.filter_by(label="Public").one()
        source = SourceSystem.query.filter_by(name="SAP").one()
        owner = User.query.filter_by(email="admin@catalogue.test").one()

    client.get("/admin/datasets/new")
    response = client.post(
        "/admin/datasets/new",
        data={
            "csrf_token": get_csrf(client, "/admin/datasets/new"),
            "name": f"Dataset {uuid.uuid4().hex[:6]}",
            "description": "Test dataset",
            "classification_id": classification.id,
            "source_system_id": source.id,
            "owner_id": str(owner.id),
            "row_count": 42,
            "refresh_frequency": "weekly",
            "is_active": "y",
        },
        follow_redirects=True,
    )
    assert b"Dataset created" in response.data


def test_admin_cannot_delete_classification_in_use(client, admin_user, app):
    login(client, admin_user.email)
    with app.app_context():
        classification = Classification.query.filter_by(label="Public").one()
    page = client.get(f"/admin/classifications/{classification.id}/delete")
    response = client.post(
        f"/admin/classifications/{classification.id}/delete",
        data={"csrf_token": extract_csrf(page.data.decode())},
        follow_redirects=True,
    )
    assert b"Cannot delete" in response.data


def test_admin_classification_crud(client, admin_user, app):
    login(client, admin_user.email)
    client.get("/admin/classifications/new")
    create = client.post(
        "/admin/classifications/new",
        data={
            "csrf_token": get_csrf(client, "/admin/classifications/new"),
            "label": "Archive",
            "rank": 5,
            "description": "",
        },
        follow_redirects=True,
    )
    assert b"Classification created" in create.data

    with app.app_context():
        item_id = Classification.query.filter_by(label="Archive").one().id

    page = client.get(f"/admin/classifications/{item_id}/edit")
    client.post(
        f"/admin/classifications/{item_id}/edit",
        data={
            "csrf_token": extract_csrf(page.data.decode()),
            "label": "Archive",
            "rank": 5,
            "description": "Updated",
        },
        follow_redirects=True,
    )

    delete_page = client.get(f"/admin/classifications/{item_id}/delete")
    delete = client.post(
        f"/admin/classifications/{item_id}/delete",
        data={"csrf_token": extract_csrf(delete_page.data.decode())},
        follow_redirects=True,
    )
    assert b"Classification deleted" in delete.data


def test_admin_edits_user(client, admin_user, app):
    login(client, admin_user.email)
    with app.app_context():
        user_id = User.query.filter_by(email="steward@catalogue.test").one().id

    page = client.get(f"/admin/users/{user_id}/edit")
    response = client.post(
        f"/admin/users/{user_id}/edit",
        data={
            "csrf_token": extract_csrf(page.data.decode()),
            "full_name": "Updated Steward",
            "role": "viewer",
            "is_active": "y",
        },
        follow_redirects=True,
    )
    assert b"User updated" in response.data
