"""FastAPI app entrypoint for the RDMC Registry Service.

This file only creates the FastAPI `app` and includes the routes
from `api.py`.
"""

from fastapi import FastAPI

from api import router as api_router

app = FastAPI(title="RDMC Registry Service")

# Include the application routes defined in `api.py` under the root path.
app.include_router(api_router)
