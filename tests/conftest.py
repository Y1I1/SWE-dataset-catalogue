import re

import pytest

from app import create_app
from app.db import db
from app.models import User
from scripts.seed import SEED_PASSWORD, run_seed

CSRF_RE = re.compile(r'name="csrf_token"[^>]*value="([^"]+)"|value="([^"]+)"[^>]*name="csrf_token"')


@pytest.fixture
def app():
    application = create_app("test")
    with application.app_context():
        db.create_all()
        if not User.query.first():
            run_seed()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    return User.query.filter_by(email="admin@catalogue.test").one()


@pytest.fixture
def viewer_user(app):
    return User.query.filter_by(email="viewer@catalogue.test").one()


def extract_csrf(html: str) -> str:
    match = CSRF_RE.search(html)
    assert match, "CSRF token not found in page"
    return match.group(1) or match.group(2)


def get_csrf(client, url: str = "/auth/login") -> str:
    response = client.get(url, follow_redirects=True)
    return extract_csrf(response.data.decode())


def login(client, email: str, password: str = SEED_PASSWORD):
    catalogue = client.get("/catalogue/", follow_redirects=False)
    if catalogue.status_code == 200:
        client.post(
            "/auth/logout",
            data={"csrf_token": extract_csrf(catalogue.data.decode())},
            follow_redirects=True,
        )

    response = client.get("/auth/login")
    return client.post(
        "/auth/login",
        data={
            "csrf_token": extract_csrf(response.data.decode()),
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )
