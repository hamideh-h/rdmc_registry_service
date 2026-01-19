"""API routes for the RDMC Registry Service.

This module holds the FastAPI router and all endpoint implementations.
It was split out from `main.py` so the application entrypoint can stay
small and focused (e.g., for ASGI servers or tests).
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy import literal

from db import get_db
from models import Rdmc, RdmcContributor
from schemas import RdmcIn, RdmcSummary, RdmcDetail
from rdmc_mapping import derive_fields_from_manifest

# Create a router that can be included into the main FastAPI app.
router = APIRouter()


@router.get("/", tags=["health"])
def health_check():
    """Simple health endpoint used by load balancers or tests.

    Returns a minimal JSON object indicating the service is running.
    """
    return {"status": "ok"}


@router.post("/rdmcs", response_model=RdmcDetail, tags=["rdmc"])
def ingest_rdmc(payload: RdmcIn, db: Session = Depends(get_db)):
    """
    Create or update an RDMC entry based on external_id.
    Also synchronizes contributors in rdmc_contributor.
    """
    # Check if it exists already
    stmt = select(Rdmc).where(Rdmc.external_id == literal(payload.external_id))
    existing = db.scalars(stmt).first()

    rdmc_fields, contributor_rows = derive_fields_from_manifest(payload.manifest)

    if existing:
        rdmc = existing
    else:
        rdmc = Rdmc(external_id=payload.external_id)
        db.add(rdmc)

    # Basic identity
    rdmc.external_id_scheme = payload.external_id_scheme
    rdmc.pid = payload.pid or rdmc.pid
    rdmc.pid_scheme = payload.pid_scheme or rdmc.pid_scheme
    if payload.pid:
        rdmc.pid_status = "minted"

    # Mapped fields → rdmc table
    rdmc.rdmc_version = rdmc_fields["rdmc_version"]
    rdmc.manifest_schema_version = rdmc_fields["manifest_schema_version"]
    rdmc.manifest_file_path = rdmc_fields["manifest_file_path"]

    rdmc.title = rdmc_fields["title"]
    rdmc.description = rdmc_fields["description"]
    rdmc.subject = rdmc_fields["subject"]
    rdmc.license = rdmc_fields["license"]
    rdmc.keywords_raw = rdmc_fields["keywords_raw"]
    rdmc.container_concept = rdmc_fields["container_concept"]

    rdmc.contributors_count = rdmc_fields["contributors_count"]
    rdmc.contributors_text = rdmc_fields["contributors_text"]

    rdmc.artifacts_raw = rdmc_fields["artifacts_raw"]
    rdmc.artifact_count = rdmc_fields["artifact_count"]
    rdmc.has_public_artifacts = rdmc_fields["has_public_artifacts"]
    rdmc.has_restricted_artifacts = rdmc_fields["has_restricted_artifacts"]
    rdmc.has_private_artifacts = rdmc_fields["has_private_artifacts"]
    rdmc.has_data_resources = rdmc_fields["has_data_resources"]
    rdmc.has_software_resources = rdmc_fields["has_software_resources"]
    rdmc.has_links = rdmc_fields["has_links"]

    rdmc.manifest = payload.manifest

    # Flush so rdmc.id is available for contributor foreign keys
    db.flush()

    # --- sync contributors table ---
    # Remove existing contributors for this rdmc (delete by rdmc_id)
    db.query(RdmcContributor).filter(
        RdmcContributor.rdmc_id == literal(rdmc.id)
    ).delete(synchronize_session=False)

    # Insert current contributors
    for c in contributor_rows:
        contrib = RdmcContributor(
            rdmc_id=rdmc.id,
            position=c["position"],
            first_name=c["first_name"],
            last_name=c["last_name"],
            email=c["email"],
            affiliation=c["affiliation"],
            orcid=c["orcid"],
            role=c["role"],
        )
        db.add(contrib)

    db.commit()
    db.refresh(rdmc)

    return rdmc


@router.get("/rdmcs", response_model=List[RdmcSummary], tags=["rdmc"])
def list_rdmcs(
    subject: Optional[str] = Query(None),
    license: Optional[str] = Query(None, alias="license_"),
    container_concept: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List RDMCs with simple equality filters.

    Query parameters:
    - `subject`: match Rdmc.subject exactly
    - `license_`: alias for `license` (avoid shadowing Python keyword)
    - `container_concept`: match Rdmc.container_concept exactly
    """
    stmt = select(Rdmc)

    if subject:
        stmt = stmt.where(Rdmc.subject == subject)  # type: ignore
    if license:
        stmt = stmt.where(Rdmc.license == license)  # type: ignore
    if container_concept:
        stmt = stmt.where(Rdmc.container_concept == container_concept)  # type: ignore

    stmt = stmt.order_by(Rdmc.created_at.desc())

    rows = db.scalars(stmt).all()
    return rows


@router.get("/rdmcs/{external_id}", response_model=RdmcDetail, tags=["rdmc"])
def get_rdmc(external_id: str, db: Session = Depends(get_db)):
    """Get full details (including manifest) for one RDMC.

    Selects by `external_id` and returns 404 if not found. The returned
    object includes the full `manifest` JSON for client inspection.
    """
    stmt = select(Rdmc).where(Rdmc.external_id == external_id)  # type: ignore
    rdmc = db.scalars(stmt).first()
    if not rdmc:
        raise HTTPException(status_code=404, detail="RDMC not found")
    return rdmc


@router.get(
    "/rdmcs/by-contributor",
    response_model=List[RdmcSummary],
    tags=["rdmc"],
)
def rdmcs_by_contributor(
    orcid: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Find RDMCs where a contributor matches given ORCID or email.
    """
    if not orcid and not email:
        raise HTTPException(
            status_code=400,
            detail="Provide at least one of: orcid, email",
        )

    # Join to contributors and filter by provided identity fields
    stmt = select(Rdmc).join(RdmcContributor)

    if orcid:
        stmt = stmt.where(RdmcContributor.orcid == literal(orcid))
    if email:
        stmt = stmt.where(RdmcContributor.email == literal(email))

    stmt = stmt.distinct().order_by(Rdmc.created_at.desc())

    rdmcs = db.scalars(stmt).all()
    return rdmcs
