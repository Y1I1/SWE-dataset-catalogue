import os
from datetime import date, datetime, timedelta, timezone

from app.db import db
from app.models import (
    AccessRequest,
    Classification,
    Dataset,
    RefreshFrequency,
    RequestStatus,
    SourceSystem,
    User,
    UserRole,
)

SEED_PASSWORD = "CatalogueDemo2026!"


def run_seed() -> None:
    reset_pw = os.getenv("RESET_ALL_PASSWORDS")

    if User.query.first():
        if reset_pw:
            users = User.query.all()
            for u in users:
                u.set_password(reset_pw)
            db.session.commit()
            print(f"Passwords reset for {len(users)} user(s).")
        else:
            print("Already seeded — skipping.")
        return

    classifications = _seed_classifications()
    systems = _seed_source_systems()
    users = _seed_users()
    datasets = _seed_datasets(classifications, systems, users)
    _seed_access_requests(datasets, users, classifications)
    db.session.commit()
    print("Seed complete.")


def _seed_classifications():
    items = {}
    for label, rank, desc in [
        ("Public", 1, "Open to all staff"),
        ("Internal", 2, "Internal use only"),
        ("Confidential", 3, "Requires approval"),
        ("Restricted", 4, "Highly restricted"),
    ]:
        c = Classification(label=label, rank=rank, description=desc)
        db.session.add(c)
        items[label] = c
    db.session.flush()
    return items


def _seed_source_systems():
    items = {}
    for name, desc, host in [
        ("Salesforce", "CRM data", "crm.example.com"),
        ("OneLake", "Data lake", "onelake.example.com"),
        ("SAP", "ERP", "sap.example.com"),
        ("Snowflake", "Warehouse", "snowflake.example.com"),
        ("Stripe", "Payments", "stripe.example.com"),
    ]:
        s = SourceSystem(name=name, description=desc, hostname=host)
        db.session.add(s)
        items[name] = s
    db.session.flush()
    return items


def _seed_users():
    items = {}
    for email, name, role in [
        ("admin@catalogue.test", "Catalogue Admin", UserRole.admin),
        ("viewer@catalogue.test", "Catalogue Viewer", UserRole.viewer),
        ("steward@catalogue.test", "Data Steward", UserRole.viewer),
        ("analyst@catalogue.test", "Business Analyst", UserRole.viewer),
    ]:
        u = User(email=email, full_name=name, role=role)
        u.set_password(SEED_PASSWORD)
        db.session.add(u)
        items[email] = u
    db.session.flush()
    return items


def _seed_datasets(classifications, systems, users):
    admin = users["admin@catalogue.test"]
    steward = users["steward@catalogue.test"]
    today = date.today()
    specs = [
        ("Customer Master", "Public", "Salesforce", admin, 125000, "daily", 1),
        ("Product Catalogue", "Public", "SAP", steward, 8400, "weekly", 3),
        ("Internal KPIs", "Internal", "Snowflake", admin, 520000, "daily", 0),
        ("Sales Pipeline", "Confidential", "Salesforce", steward, 98000, "daily", 1),
        ("Revenue Forecast", "Confidential", "OneLake", admin, 450000, "weekly", 2),
        ("Customer PII", "Restricted", "Salesforce", admin, 125000, "monthly", 10),
        ("Fraud Alerts", "Restricted", "Stripe", admin, 12000, "daily", 0),
        ("Web Analytics", "Public", "Snowflake", steward, 8900000, "daily", 0),
    ]
    datasets = []
    for name, cls, sys, owner, rows, freq, days_ago in specs:
        ds = Dataset(
            name=name,
            description=f"{name} dataset",
            source_system_id=systems[sys].id,
            classification_id=classifications[cls].id,
            owner_id=owner.id,
            row_count=rows,
            refresh_frequency=RefreshFrequency(freq),
            last_refreshed=today - timedelta(days=days_ago),
        )
        db.session.add(ds)
        datasets.append(ds)
    db.session.flush()
    return datasets


def _seed_access_requests(datasets, users, classifications):
    admin = users["admin@catalogue.test"]
    viewer = users["viewer@catalogue.test"]
    now = datetime.now(timezone.utc)
    sensitive_ids = {
        classifications["Confidential"].id,
        classifications["Restricted"].id,
    }
    confidential = [d for d in datasets if d.classification_id in sensitive_ids]

    db.session.add(
        AccessRequest(
            dataset_id=confidential[0].id,
            requested_by=viewer.id,
            reason="Need access for quarterly compliance reporting.",
            status=RequestStatus.pending,
        )
    )
    db.session.add(
        AccessRequest(
            dataset_id=confidential[1].id,
            requested_by=users["analyst@catalogue.test"].id,
            reason="Building executive dashboard for finance.",
            status=RequestStatus.approved,
            decided_by=admin.id,
            decided_at=now - timedelta(days=2),
        )
    )
