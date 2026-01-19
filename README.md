# RDMC Registry Service

A FastAPI-based microservice for ingesting, indexing, and retrieving RDMC
(Research Data Management Container) manifests.

The service is **fully deployed on Render**, including both the **API** and the
**PostgreSQL database**.


##  Deployment (Render)

### Live API
https://rdmc-registry-service.onrender.com

###  API Documentation
- **Swagger UI:** https://rdmc-registry-service.onrender.com/docs
- **ReDoc:** https://rdmc-registry-service.onrender.com/redoc
- **OpenAPI JSON:** https://rdmc-registry-service.onrender.com/openapi.json

###  Database
The PostgreSQL database is hosted on **Render** and accessed via environment
variables.



##  Repository Structure

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


## License and contributing

- This project is licensed under the MIT License — see the included `LICENSE` file for details.


- Contributions are welcome! Please open issues or pull requests on GitHub.