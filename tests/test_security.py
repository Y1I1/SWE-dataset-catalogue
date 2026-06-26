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


def test_csp_header_present_in_prod(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "prod-test-secret")
    app = create_app("prod")
    client = app.test_client()
    response = client.get("/auth/login", follow_redirects=True)
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src" in csp
    assert "'self'" in csp


def test_session_cookie_samesite_in_prod(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("SECRET_KEY", "prod-test-secret")
    app = create_app("prod")
    assert app.config.get("SESSION_COOKIE_SAMESITE") == "Lax"
    assert app.config.get("SESSION_COOKIE_HTTPONLY") is True
    assert app.config.get("SESSION_COOKIE_SECURE") is True


def test_password_hash_uses_scrypt(app):
    from app.models import User

    with app.app_context():
        user = User.query.filter_by(email="viewer@catalogue.test").one()
        assert user.password_hash.startswith("scrypt:")


def test_viewer_list_masks_gated_metadata(client, viewer_user):
    login(client, viewer_user.email)
    response = client.get("/catalogue/")
    assert response.status_code == 200
    body = response.data.decode()
    # Public dataset name is visible
    assert "Customer Master" in body
    # OneLake is used only by Revenue Forecast (Confidential) — must not appear in a table cell
    assert "<td>OneLake</td>" not in body


def test_stored_xss_escaped_in_list(client, admin_user, app):
    from app.db import db
    from app.models import Classification, Dataset, SourceSystem

    login(client, admin_user.email)
    with app.app_context():
        cls = Classification.query.filter_by(label="Public").one()
        sys = SourceSystem.query.filter_by(name="Salesforce").one()
        xss_dataset = Dataset(
            name='<script>alert("xss")</script>',
            description="XSS test dataset",
            classification_id=cls.id,
            source_system_id=sys.id,
            owner_id=admin_user.id,
            row_count=0,
            refresh_frequency="daily",
        )
        db.session.add(xss_dataset)
        db.session.commit()

    response = client.get("/catalogue/")
    assert b"<script>alert" not in response.data
    assert b"&lt;script&gt;" in response.data
