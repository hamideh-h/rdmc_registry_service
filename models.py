"""ORM model definitions for the RDMC registry service.

This module defines SQLAlchemy models (currently a single `Rdmc` model)
that map to the `rdmc` table in PostgreSQL. Fields include identifiers,
PID lifecycle state, metadata (title, description, subjects, etc.),
artifact flags, the full manifest (as JSONB), and timestamp columns.

Comments on individual fields explain their purpose and typical values.
"""

# Standard and SQLAlchemy imports used to declare table columns and
# types. We import PostgreSQL-specific types JSONB and TSVECTOR for
# storing the manifest and search index respectively.
from sqlalchemy import (
    Column,
    BigInteger,
    Text,
    Integer,
    Boolean,
    TIMESTAMP,
    ForeignKey
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base


class Rdmc(Base):
    """Represents a single RDMC record.

    Each instance corresponds to one row in the `rdmc` table. The table
    stores both machine-readable data (manifest JSON) and extracted
    searchable/summary fields used for listing and filtering.

    Notes:
    - Many fields are nullable because manifests can be incomplete.
    - Some fields (like `manifest`) are stored in Postgres JSONB for
      efficient JSON querying.
    """

    __tablename__ = "rdmc"

    # Primary key: numeric, auto-incrementing. Use BigInteger to allow a
    # large number of records.
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # External identifier(s): these come from the source system that
    # deposited the RDMC record. `external_id` is indexed for lookup.
    external_id = Column(Text, nullable=False, index=True)
    external_id_scheme = Column(Text)

    # PID fields: persistent identifier assigned by a PID service.
    # `pid` is unique. `pid_status` tracks lifecycle (e.g. 'pending',
    # 'minted', 'failed'). `pid_minted_at` records when it was minted.
    pid = Column(Text, unique=True)
    pid_scheme = Column(Text)
    pid_status = Column(Text, nullable=False, default="pending")
    pid_minted_at = Column(TIMESTAMP(timezone=True))

    # Versioning / manifest metadata
    rdmc_version = Column(Text)
    manifest_schema_version = Column(Text)
    manifest_file_path = Column(Text)  # path or key to raw manifest file

    # Human-readable metadata used for display and search
    title = Column(Text, nullable=False)
    description = Column(Text)
    subject = Column(Text, index=True)  # simple subject/category text
    license = Column(Text, index=True)
    keywords_raw = Column(Text)  # raw keywords (comma/JSON text)
    container_concept = Column(Text, index=True)

    # Contributor summary fields (extracted from manifest)
    contributors_count = Column(Integer)
    contributors_text = Column(Text)  # human-friendly contributors string

    # Artifact and resource summaries
    artifacts_raw = Column(Text)  # raw artifact list as text/JSON
    artifact_count = Column(Integer)
    has_public_artifacts = Column(Boolean, default=False)
    has_restricted_artifacts = Column(Boolean, default=False)
    has_private_artifacts = Column(Boolean, default=False)
    has_data_resources = Column(Boolean, default=False)
    has_software_resources = Column(Boolean, default=False)
    has_links = Column(Boolean, default=False)

    # The full manifest stored as JSONB for efficient JSON queries in
    # PostgreSQL. This is the authoritative manifest for the RDMC record.
    manifest = Column(JSONB, nullable=False)

    # Full text search vector (TSVECTOR) used by Postgres FTS indexes and
    # queries. It's populated by a trigger or application code.
    search_vector = Column(TSVECTOR)

    # Hash of the manifest content to detect duplicates/changes.
    manifest_hash = Column(Text)

    # Whether this row is the latest version for a given external_id
    # (useful if you store historical records). Default True for new
    # inserts; application logic should flip this when new versions are
    # added.
    is_latest = Column(Boolean, default=True)

    # Timestamps: created_at defaults to now(), updated_at updates on
    # every row modification using `onupdate=func.now()`.
    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationship to the contributor table. This enables ORM-style
    # access like `rdmc.contributors` which returns a list of
    # `RdmcContributor` objects linked to this RDMC row.
    #
    # Note: the contributor class below also declares a relationship
    # back to `Rdmc`. SQLAlchemy supports either `backref` (one-side)
    # or `back_populates` (explicit on both sides). Here we use
    # `back_populates` on this side; the other side currently uses a
    # `backref` (both patterns are valid, but you can unify them if you
    # prefer explicit two-way relationships).
    contributors = relationship("RdmcContributor", back_populates="rdmc")


class RdmcContributor(Base):
    """Represents a single contributor to an RDMC record.

    Each row stores contributor-identifying fields (name, email, ORCID,
    affiliation) as well as their ordinal `position` in the manifest.
    The `rdmc_id` column is a foreign key linking back to `rdmc.id`.
    """
    __tablename__ = "rdmc_contributor"

    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # Foreign key to the RDMC row. `ondelete='CASCADE'` means contributors
    # will be removed automatically if their parent RDMC row is deleted.
    rdmc_id = Column(
        BigInteger,
        ForeignKey("rdmc.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Position is used to preserve the author order coming from the
    # manifest. It should start at 0 (the code that inserts contributors
    # in the service assigns `pos` from enumerate()).
    position = Column(Integer, nullable=False)

    # Contributor identity fields. `first_name` and `last_name` are
    # required here, but `email`, `affiliation` and `orcid` are optional
    # because manifests vary in what they provide.
    first_name = Column(Text, nullable=False)
    last_name = Column(Text, nullable=False)
    email = Column(Text)
    affiliation = Column(Text)
    orcid = Column(Text, index=True)
    role = Column(Text)

    created_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationship back to Rdmc. The `backref` creates a complementary
    # attribute `rdmc.contributors` on the parent side; see the note
    # above about `backref` vs `back_populates`.
    rdmc = relationship("Rdmc", backref="contributors")
