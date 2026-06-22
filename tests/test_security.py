from app import create_app
from tests.conftest import login


def test_missing_csrf_rejected(client, viewer_user):
    login(client, viewer_user.email)
    response = client.post("/auth/logout", data={}, follow_redirects=False)
    assert response.status_code == 400


def test_sqli_search_is_neutralised(client, viewer_user):
    login(client, viewer_user.email)
    baseline = client.get("/catalogue/")
    baseline_rows = baseline.data.count(b"/catalogue/datasets/")
    response = client.get("/catalogue/?q=%27+OR+1%3D1+--")
    assert response.data.count(b"/catalogue/datasets/") < baseline_rows


def test_xss_payload_is_escaped(client, viewer_user):
    login(client, viewer_user.email)
    response = client.get("/catalogue/?q=%3Cscript%3Ealert(1)%3C/script%3E")
    assert b"<script>" not in response.data


def test_prod_config_debug_off(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "prod-test-secret")
    app = create_app("prod")
    assert app.config["DEBUG"] is False


def test_security_headers_in_prod(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "prod-test-secret")
    app = create_app("prod")
    client = app.test_client()
    response = client.get("/auth/login", follow_redirects=True)
    assert response.headers.get("X-Frame-Options") == "SAMEORIGIN"
