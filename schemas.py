"""Pydantic request/response schemas for the RDMC registry service.

This module defines the JSON shapes the API accepts and returns:
- `RdmcIn` is used for incoming create/update payloads.
- `RdmcSummary` is a compact view for list endpoints.
- `RdmcDetail` extends the summary with additional fields for
  detailed views.

Comments on each field explain where the data comes from and how the
field maps to the database `Rdmc` model.
"""

# Typing helpers and Pydantic model base class. Field is used to attach
# metadata (like descriptions) which shows up in OpenAPI docs.
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class RdmcIn(BaseModel):
    """Payload when we ingest a new RDMC or update an existing one.

    This model represents the canonical input the API expects when a
    client submits an RDMC manifest. The `manifest` field should be the
    full JSON manifest (the service will extract summary fields from it
    and store the raw manifest in the DB).
    """

    # Identifier assigned by the source system (required).
    external_id: str

    # Optional scheme or namespace for the external_id (e.g. a provider
    # name or system URI).
    external_id_scheme: Optional[str] = None

    # Optional PID info: if present the service may attempt to mint or
    # validate a PID for this record; it's fine to omit these fields on
    # create and let the registry handle PID assignment.
    pid: Optional[str] = None
    pid_scheme: Optional[str] = None

    # The full RDMC manifest (already converted to JSON). Use a plain
    # Dict[str, Any] because the manifest structure can be nested and
    # heterogeneous. The Field description improves generated docs.
    manifest: Dict[str, Any] = Field(
        ...,
        description="Full RDMC manifest as JSON (converted from YAML if needed)",
    )


class RdmcSummary(BaseModel):
    """What we return in list endpoints.

    This is a compact representation intended for index/list API
    responses. The fields are a subset of what lives in the full
    `Rdmc` database model.
    """

    external_id: str
    title: str

    # Optional summary fields extracted from the manifest. They may be
    # absent if the manifest didn't include matching metadata.
    subject: Optional[str] = None
    license: Optional[str] = None
    container_concept: Optional[str] = None

    class Config:
        # Use attribute-based population so you can return SQLAlchemy ORM
        # objects directly from path operations and have Pydantic
        # convert them to the schema. For Pydantic v1 use `orm_mode = True`.
        from_attributes = True  # Pydantic v2 (if v1, use orm_mode = True)


class RdmcDetail(RdmcSummary):
    """Detailed view of an RDMC record returned by detail endpoints.

    Extends `RdmcSummary` with additional diagnostic and descriptive
    fields that are useful when inspecting a single record.
    """

    # Extended descriptive fields
    description: Optional[str] = None
    keywords_raw: Optional[str] = None

    # Contributor counts and human-friendly summary extracted from the
    # manifest; useful for display without fetching the full manifest.
    contributors_count: Optional[int] = None
    contributors_text: Optional[str] = None

    # Artifact summaries (may be derived from manifest 'artifacts' or
    # calculated by mapping code). These are helpful to know at a glance
    # whether a record has downloadable data/software or links.
    artifacts_raw: Optional[str] = None
    artifact_count: Optional[int] = None
    has_public_artifacts: Optional[bool] = None
    has_restricted_artifacts: Optional[bool] = None
    has_private_artifacts: Optional[bool] = None
    has_data_resources: Optional[bool] = None
    has_software_resources: Optional[bool] = None
    has_links: Optional[bool] = None

    # The authoritative manifest is included in the detailed view so
    # clients can inspect the full JSON when they need to.
    manifest: dict
