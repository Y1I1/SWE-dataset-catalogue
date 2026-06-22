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

## Deploy (Render)

1. Push this repo to GitHub.
2. In [Render](https://render.com), create a **Web Service** from the repo (or use **New > Blueprint** if `render.yaml` is detected).
3. Set environment variable `DATABASE_URL` to your Supabase pooler URI (`postgresql+pg8000://...` on port 6543).
4. Deploy. The release step runs `init-db` and `seed` automatically.
5. Open the Render URL and log in with the test accounts above.
