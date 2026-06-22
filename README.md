# Dataset Catalogue

Flask app for browsing datasets and managing access requests.

## Setup

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
flask --app run.py init-db
flask --app run.py seed
flask --app run.py run
```

## Test logins

Password: `CatalogueDemo2024!`

- admin@catalogue.test (admin)
- viewer@catalogue.test (viewer)

## Tests

```
set FLASK_CONFIG=test
pytest
```
