# Data Cataloguer

[![CI](https://github.com/Y1I1/SWE-dataset-catalogue/actions/workflows/ci.yml/badge.svg)](https://github.com/Y1I1/SWE-dataset-catalogue/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)

A secure, centralised Flask web application for discovering datasets across an organisation and requesting access to sensitive ones through a formal approval workflow. Built as the secure-application component for the **Software Engineering and DevOps** module (Level 6 Digital & Technology Solutions degree apprenticeship).

---

## Contents

- [The problem it solves](#the-problem-it-solves)
- [Features](#features)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Project structure](#project-structure)
- [Data model](#data-model)
- [Security](#security)
- [Getting started](#getting-started)
- [Configuration](#configuration)
- [Test accounts](#test-accounts)
- [Running the tests](#running-the-tests)
- [Code quality](#code-quality)
- [Continuous integration](#continuous-integration)
- [Deployment](#deployment)
- [Health check](#health-check)
- [Known limitations & future work](#known-limitations--future-work)
- [Academic note](#academic-note)

---

## The problem it solves

In many large organisations data is heavily **siloed** — customer data in a CRM, financials in an ERP, analytics in a warehouse and a data lake, payments in a separate system. Different teams own different systems, there is **no single place to discover what data exists**, who owns it, how sensitive it is, or how fresh it is, and access is often granted ad hoc through email threads and spreadsheets with no audit trail.

**Data Cataloguer** attacks that problem directly. It provides one searchable catalogue of datasets spanning every source system, surfaces each dataset's owner, classification, row count and refresh cadence, and gates access to sensitive datasets behind an explicit admin approval workflow.

Sensitivity is modelled as ranked **classifications** (Public → Internal → Confidential → Restricted). Public and Internal datasets are visible to all signed-in staff; Confidential and Restricted datasets are gated until an administrator approves an access request.

## Features

**Viewers** can:
- Browse and search the full dataset catalogue (free-text, by classification, by source system, sortable).
- View full metadata for any dataset they are entitled to see.
- Request access to gated (Confidential/Restricted) datasets with a written justification.
- Track the status of their own access requests.

**Administrators** can do all of the above, plus:
- Manage datasets, classifications and source systems (create, edit, deactivate/delete).
- Manage users (edit role and active status).
- Approve or reject pending access requests.

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 |
| Web framework | Flask 3.1 |
| ORM | Flask-SQLAlchemy 3.1 / SQLAlchemy 2.0 |
| Forms & CSRF | Flask-WTF + WTForms |
| Authentication | Flask-Login |
| Security headers / CSP | Flask-Talisman |
| Rate limiting | Flask-Limiter |
| Database (production) | PostgreSQL on Supabase (via the `pg8000` driver) |
| Database (tests) | SQLite (in-memory) |
| WSGI server | Gunicorn |
| Hosting | Render |
| CI | GitHub Actions |
| Tooling | black, isort, ruff, pytest, pytest-cov |

## Architecture

The application uses a layered architecture. HTTP requests pass through a security middleware layer, are routed by feature **blueprints**, delegate business logic to a **services** layer, and reach the database only through **SQLAlchemy models** — keeping route handlers thin and logic testable in isolation.

```mermaid
flowchart TB
    U["Viewer / Admin (browser)"] -->|HTTPS| MW
    subgraph Host["Render — Gunicorn + Flask"]
      MW["Security layer<br/>Talisman headers/CSP · CSRF · Rate limiter · Flask-Login"]
      subgraph BP["Blueprints"]
        A["auth"]
        C["catalogue"]
        AD["admin"]
      end
      SVC["Services<br/>permissions · catalogue · access_requests · admin"]
      ORM["SQLAlchemy models<br/>User · Dataset · Classification · SourceSystem · AccessRequest"]
      MW --> BP --> SVC --> ORM
    end
    ORM -->|pg8000| DB[("Supabase PostgreSQL")]
```

## Project structure

```
.
├── app/
│   ├── __init__.py            # App factory, extension init, CLI commands, routes
│   ├── config.py              # Dev / Test / Prod configuration classes
│   ├── db.py                  # SQLAlchemy instance re-export
│   ├── errors.py              # 403/404/500/429 handlers
│   ├── extensions.py          # db, login_manager, csrf, limiter, talisman
│   ├── auth/                  # Registration, login, logout
│   ├── catalogue/             # Browse, search, dataset detail, access requests
│   ├── admin/                 # Dataset/classification/source-system/user management
│   ├── models/                # User, Dataset, Classification, SourceSystem, AccessRequest
│   ├── security/              # role_required decorator
│   ├── services/              # permissions, catalogue, access_requests, admin (business logic)
│   ├── static/                # CSS and assets
│   └── templates/             # Jinja2 templates (auto-escaped)
├── scripts/
│   └── seed.py                # Idempotent demo-data seeding
├── supabase/
│   └── schema.sql             # Reference PostgreSQL schema (DDL)
├── tests/                     # pytest suite incl. dedicated security tests
├── .github/workflows/ci.yml   # Lint + test pipeline
├── render.yaml                # Render deployment blueprint
├── requirements.txt           # Pinned dependencies
├── pyproject.toml             # black / isort / ruff / pytest config
└── run.py                     # Entry point (gunicorn run:app)
```

## Data model

Five tables with UUID primary keys for core entities and serial integers for lookups, a range of data types (UUID, TEXT, INT, BIGINT, BOOLEAN, DATE, TIMESTAMPTZ, ENUM), foreign-key relationships, and database-level integrity constraints:

- **`chk_decided`** — a decided access request must have both a decider and a decision timestamp; a pending one must have neither.
- **`uq_pending_request`** — a partial unique index preventing duplicate *pending* requests for the same dataset/user.
- **`chk_row_count_nonneg`** — dataset row counts cannot be negative.

```mermaid
erDiagram
    USERS ||--o{ DATASETS : owns
    USERS ||--o{ ACCESS_REQUESTS : requests
    USERS ||--o{ ACCESS_REQUESTS : decides
    SOURCE_SYSTEMS ||--o{ DATASETS : "is source of"
    CLASSIFICATIONS ||--o{ DATASETS : classifies
    DATASETS ||--o{ ACCESS_REQUESTS : "is target of"

    USERS {
        uuid id PK
        text email UK
        text full_name
        text password_hash
        enum role
        bool is_active
    }
    SOURCE_SYSTEMS {
        int id PK
        text name UK
        text hostname
    }
    CLASSIFICATIONS {
        int id PK
        text label UK
        int rank UK
    }
    DATASETS {
        uuid id PK
        text name UK
        int source_system_id FK
        int classification_id FK
        uuid owner_id FK
        bigint row_count
        enum refresh_frequency
        date last_refreshed
        bool is_active
    }
    ACCESS_REQUESTS {
        uuid id PK
        uuid dataset_id FK
        uuid requested_by FK
        text reason
        enum status
        uuid decided_by FK
        timestamptz decided_at
    }
```

## Security

Security is the focus of the application, with controls mapped to the **OWASP Top 10 (2021)** and verified by automated tests.

| OWASP category | Control in this app | Where | Verified by |
|---|---|---|---|
| **A01 – Broken Access Control** | Server-side role enforcement (`role_required`, 403 on failure) and a per-object permission check (classification-rank gate + approved-request lookup) | `security/decorators.py`, `services/permissions.py` | `test_viewer_cannot_access_admin`, `test_viewer_blocked_from_restricted_dataset` |
| **A02 – Cryptographic Failures** | Salted password hashing; HTTPS forced in production; `HttpOnly` / `SameSite=Lax` / `Secure` session cookies | `models/user.py`, `config.py` | `test_security_headers_in_prod` |
| **A03 – Injection (SQLi & XSS)** | Parameterised queries via SQLAlchemy `ilike` (no string concatenation); Jinja2 auto-escaping | `services/catalogue.py`, templates | `test_sqli_search_is_neutralised`, `test_xss_payload_is_escaped` |
| **A05 – Security Misconfiguration** | Talisman security headers + CSP; `DEBUG=False` in production | `extensions.py`, `config.py` | `test_prod_config_debug_off`, `test_security_headers_in_prod` |
| **A07 – Identification & Auth Failures** | Password policy (≥12 chars, letter + number); login rate limiting; generic "Invalid email or password" message to prevent user enumeration | `auth/forms.py`, `auth/routes.py` | `test_register_rejects_short_password`, `test_login_invalid_credentials` |
| **CSRF** (A01-adjacent) | Flask-WTF CSRF tokens on all state-changing forms | `extensions.py`, templates | `test_missing_csrf_rejected` |

## Getting started

### Prerequisites

- Python 3.12
- A database. For a zero-config local run you can use SQLite; for a shared/production-like setup use PostgreSQL (e.g. Supabase).

### 1. Clone and create a virtual environment

```bash
git clone https://github.com/Y1I1/SWE-dataset-catalogue.git
cd SWE-dataset-catalogue
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
# macOS / Linux
cp .env.example .env

# Windows
copy .env.example .env
```

For the quickest local start, set a local SQLite database in `.env`:

```
DATABASE_URL=sqlite:///catalogue.db
SECRET_KEY=change-me-to-something-random
FLASK_CONFIG=dev
```

For a shared/production-like setup, point `DATABASE_URL` at your Supabase pooler URI instead (see [Configuration](#configuration)).

### 4. Initialise and seed the database

```bash
flask --app run.py init-db
flask --app run.py seed
```

Seeding is idempotent — it skips if users already exist.

### 5. Run the app

```bash
flask --app run.py run
```

Then open <http://127.0.0.1:5000> and sign in with one of the [test accounts](#test-accounts).

## Configuration

Configuration is environment-driven and selected by `FLASK_CONFIG` (`dev`, `test`, or `prod`).

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes (dev/prod) | SQLAlchemy database URI. SQLite for local (`sqlite:///catalogue.db`); for Postgres on Supabase use `postgresql+pg8000://...` on the pooler port `6543`. Not needed for the test config (uses in-memory SQLite). |
| `SECRET_KEY` | Yes | Flask session signing key. Use a long random value in production. |
| `FLASK_CONFIG` | No | `dev` (default), `test`, or `prod`. |

The `prod` configuration enables HTTPS enforcement, a strict Content-Security-Policy, secure cookies, `DEBUG=False`, and a `ProxyFix` middleware for running behind Render's proxy.

## Test accounts

Created by the seed script. Default password for all accounts: `CatalogueDemo2024!`

| Email | Role |
|---|---|
| admin@catalogue.test | Admin |
| viewer@catalogue.test | Viewer |
| steward@catalogue.test | Viewer |
| analyst@catalogue.test | Viewer |

## Running the tests

The suite covers authentication, catalogue, admin, the services layer, and a dedicated security module (CSRF, SQL injection, XSS, security headers, production hardening).

```bash
# macOS / Linux
FLASK_CONFIG=test pytest

# Windows (PowerShell)
$env:FLASK_CONFIG = "test"; pytest
```

A **coverage gate of 80%** is enforced via `pyproject.toml` (`--cov-fail-under=80`); the run fails if coverage drops below that threshold.

## Code quality

Formatting and linting are enforced both locally and in CI.

```bash
black app tests scripts
isort app tests scripts
ruff check app tests scripts
```

## Continuous integration

Every push and pull request to `main` triggers the GitHub Actions pipeline (`.github/workflows/ci.yml`), which on Python 3.12:

1. Checks formatting with **black** and **isort**.
2. Lints with **ruff**.
3. Runs the **pytest** suite with the 80% coverage gate.

A pull request must pass all checks before it can be merged.

## Deployment

The app is deployed to **Render** as a web service, defined declaratively in `render.yaml`.

1. Push the repository to GitHub.
2. In [Render](https://render.com), create a **Web Service** from the repo (or use **New → Blueprint** so `render.yaml` is detected).
3. Set `DATABASE_URL` to your Supabase pooler URI (`postgresql+pg8000://...`, port `6543`). `SECRET_KEY` is generated automatically and `FLASK_CONFIG` is set to `prod` by the blueprint.
4. Deploy. On startup the service runs `init-db` and `seed`, then starts Gunicorn:
   ```
   flask --app run.py init-db && flask --app run.py seed && gunicorn run:app --bind 0.0.0.0:$PORT
   ```
5. Open the Render URL and sign in with the test accounts.

## Health check

A lightweight endpoint at `/health/db` confirms database connectivity and is suitable for an uptime probe:

```json
{ "database": "connected" }
```

## Known limitations & future work

Documented honestly to support critical evaluation. None of these block the core use case; they are the natural next iterations:

- **No structured logging or audit trail.** The app reports errors to the user but does not log them, and access decisions are not recorded beyond the `decided_by`/`decided_at` fields on a request. A dedicated audit log of access decisions and admin actions would reinforce the governance goal and is the single highest-value improvement.
- **Rate limiting is in-memory.** `Flask-Limiter` uses an in-memory store, so login throttling is per-process and resets on restart. A shared backend (e.g. Redis) would make it effective across multiple Gunicorn workers.
- **Open self-registration.** Anyone can register a viewer account. For an internal tool this would be better restricted to a verified email domain or gated behind admin approval.
- **No MFA or account lockout.** Authentication relies on password strength and rate limiting; multi-factor authentication and progressive lockout would harden it further.
- **Catalogue queries are unpaginated** and use lazy relationship loading. Eager loading and pagination would improve performance at scale.
- **The sensitivity boundary is rank-based** (`rank >= 3`). A dedicated `is_sensitive` flag on classifications would make the security boundary explicit and resistant to rank reordering.

## Academic note

This repository was produced as coursework for the University of Roehampton **Software Engineering and DevOps** module (QAC020X328). It is shared for assessment and demonstration purposes.