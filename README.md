# RDMC Registry Service

A small FastAPI-based service to ingest and index RDMC (Research Data Management Container) manifests.

This repository contains:
- `api.py` - FastAPI router with endpoints for ingesting and querying RDMCs.
- `main.py` - application entrypoint (wires the router into a FastAPI app).
- `db.py` - SQLAlchemy engine/session and base declarative setup.
- `models.py` - SQLAlchemy ORM models (`Rdmc`, `RdmcContributor`).
- `schemas.py` - Pydantic request/response schemas used by the API.
- `rdmc_mapping.py` - Logic that maps RDMC manifest JSON into DB fields and contributor rows.
- `requirements.txt` - Python dependencies.

This README explains how to set up, run, and interact with the service locally.


## Prerequisites
- Python 3.10+ (project uses modern typing and Pydantic/SQLAlchemy features).
- PostgreSQL database available and reachable from this service.
- Recommended: create and use a virtual environment (venv).


## Install

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```


## Configuration / Environment

The service reads database configuration from the `DATABASE_URL` environment variable. Create a `.env` file in the project root or export the variable in your shell. Example:

```
# .env
# DATABASE_URL=postgresql+psycopg2://user:password@host:port/dbname
```


## Run locally (development)

Start the FastAPI app using Uvicorn (from the project root):

```powershell
# Run on localhost:8000
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Open http://127.0.0.1:8000/docs to view the interactive OpenAPI (Swagger) UI.


## API Endpoints (high level)

- `GET /`
  - Health check. Returns `{ "status": "ok" }`.

- `POST /rdmcs`
  - Ingest or update an RDMC manifest.
  - Request body: `RdmcIn` (see `schemas.py`). The `manifest` field should contain the full RDMC JSON.
  - Response: full `RdmcDetail` object when successful.

- `GET /rdmcs`
  - List RDMCs (returns `RdmcSummary` objects).
  - Optional query params: `subject`, `license_` (alias for `license`), `container_concept`.

- `GET /rdmcs/{external_id}`
  - Get full RDMC detail by `external_id` (includes stored `manifest`).

- `GET /rdmcs/by-contributor?orcid=...&email=...`
  - Find RDMCs by contributor ORCID or email.

Refer to the interactive docs at `/docs` for exact request/response shapes.


## Database notes

- Schema is defined by the SQLAlchemy models in `models.py`.
- The `rdmc` table stores the full manifest JSON in a `JSONB` column plus a set of derived fields for indexing and filtering.
- Contributors are stored in `rdmc_contributor` with a foreign key `rdmc_id`.

This project does not include automatic migrations. For production use, add Alembic (recommended) and create migration scripts. For a quick local setup you can create tables using SQLAlchemy's metadata (only for dev/testing):

```python
# quick dev-only example (run once)
from db import engine
from models import Base
Base.metadata.create_all(bind=engine)
```


## Example requests

Health check (PowerShell / curl):

```powershell
curl http://127.0.0.1:8000/
```

Ingest example (replace `manifest.json` with your RDMC JSON file):

```powershell
curl -X POST http://127.0.0.1:8000/rdmcs -H "Content-Type: application/json" -d @manifest.json
```

List RDMCs:

```powershell
curl http://127.0.0.1:8000/rdmcs
```

Find by contributor ORCID:

```powershell
curl "http://127.0.0.1:8000/rdmcs/by-contributor?orcid=0000-0000-0000-0000"
```


## Tests

There are no test files included in this repository yet. Recommended next steps:
- Add unit tests for `rdmc_mapping.py` (happy path + malformed manifests).
- Add integration tests for `api.py` using FastAPI's TestClient and a temporary test database.


## Next steps / improvements

- Add Alembic migrations for robust schema management.
- Harden input validation and manifest schema checks (the `rdmc_mapping` module uses permissive lookups).
- Add unit and integration tests.
- Add CI workflow that runs linting and tests.


## License and contributing

- This project is licensed under the MIT License — see the included `LICENSE` file for details.

- If you plan to publish or share this project, consider adding a `CONTRIBUTING.md` file that explains how to contribute, coding standards, and how to run tests. If you'd like, I can add a starter `CONTRIBUTING.md` for you.


## Contact / support

