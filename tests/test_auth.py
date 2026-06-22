import uuid

from tests.conftest import get_csrf, login


def test_register_and_login(client):
    email = f"user-{uuid.uuid4().hex[:8]}@catalogue.test"
    client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": get_csrf(client, "/auth/register"),
            "full_name": "New User",
            "email": email,
            "password": "ValidPass123!",
            "confirm_password": "ValidPass123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Catalogue" in response.data

    client.post(
        "/auth/logout",
        data={"csrf_token": get_csrf(client, "/catalogue/")},
        follow_redirects=True,
    )
    login(client, email, "ValidPass123!")


def test_login_invalid_credentials(client):
    client.get("/auth/login")
    response = client.post(
        "/auth/login",
        data={
            "csrf_token": get_csrf(client),
            "email": "viewer@catalogue.test",
            "password": "wrong-password",
        },
        follow_redirects=True,
    )
    assert b"Invalid email or password" in response.data


def test_catalogue_requires_login(client):
    response = client.get("/catalogue/", follow_redirects=False)
    assert response.status_code == 302


def test_register_rejects_short_password(client):
    client.get("/auth/register")
    response = client.post(
        "/auth/register",
        data={
            "csrf_token": get_csrf(client, "/auth/register"),
            "full_name": "Bad Password",
            "email": "bad@catalogue.test",
            "password": "short",
            "confirm_password": "short",
        },
        follow_redirects=True,
    )
    assert b"12 characters" in response.data


def test_health_db(app):
    with app.test_client() as client:
        response = client.get("/health/db")
        assert response.status_code == 200
        assert response.get_json()["database"] == "connected"
