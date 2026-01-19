# rdmc_mapping.py
from typing import Any, Dict, List, Tuple


def derive_fields_from_manifest(
    manifest: Dict[str, Any],
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Extracts two things from an RDMC manifest JSON:
      - rdmc table fields: a flat dict of summary/search fields that map
        directly to columns on the Rdmc database model.
      - contributor rows: a list of dicts representing individual
        contributors suitable for inserting into `rdmc_contributor`.

    This function is intentionally defensive: manifests may come from
    different producers and use slightly different key names (e.g.
    "RDMC Title" vs "title"). We therefore try a small set of
    fallbacks when reading values.

    Returns:
      (rdmc_fields, contributor_rows)
    where `rdmc_fields` is a mapping of canonical field names used by
    the service and `contributor_rows` is a list of per-contributor
    dicts with keys: position, first_name, last_name, email,
    affiliation, orcid, role.
    """

    # --- Top-level manifest fields ---
    # Try canonical RDMC keys first, then sensible fallbacks
    title = manifest.get("RDMC Title") or manifest.get("title")
    rdmc_version = manifest.get("RDMC Version")
    manifest_schema_version = manifest.get("Manifest-Schemaversion")
    manifest_file_path = manifest.get("Manifest File Path")

    # --- Nested metadata ---
    rdmc_metadata = manifest.get("RDMC Metadata", {}) or {}
    description = rdmc_metadata.get("Description")
    subject = rdmc_metadata.get("Subject")
    license_ = rdmc_metadata.get("License")
    keywords_raw = rdmc_metadata.get("Keywords")
    container_concept = rdmc_metadata.get("container-concept")

    # --- Contributors ---
    # We compute two artifacts from the contributors list:
    #  - `contributor_rows`: row dicts to insert into rdmc_contributor
    #  - `contributors_text`: a human-friendly summary for the rdmc
    #    table used in lists and search displays.
    contributors = rdmc_metadata.get("Contributors", []) or []
    contributors_count = len(contributors)

    contributor_rows: List[Dict[str, Any]] = []
    contrib_parts = []

    for pos, c in enumerate(contributors):
        # Normalize fields and ensure strings are stripped.
        first = (c.get("first_name") or "").strip()
        last = (c.get("last_name") or "").strip()
        email = c.get("email")
        affiliation = c.get("affiliation")
        orcid = c.get("orcid")
        role = c.get("role")

        # Build the contributor row used for DB insertion.
        contributor_rows.append(
            {
                "position": pos,
                "first_name": first,
                "last_name": last,
                "email": email,
                "affiliation": affiliation,
                "orcid": orcid,
                "role": role,
            }
        )

        # Build a compact, human-friendly contributor string piece by
        # piece. This is used to form `contributors_text` for display.
        piece = f"{first} {last}".strip()
        if role:
            piece += f" ({role})"
        if orcid:
            piece += f", ORCID: {orcid}"
        if affiliation:
            piece += f", {affiliation}"
        if piece:
            contrib_parts.append(piece)

    contributors_text = "; ".join(contrib_parts) if contrib_parts else None

    # --- Artifacts ---
    # We extract a few boolean flags that are useful for quick filtering
    # (e.g. does this RDMC have public artifacts? any software resources?)
    artifacts_raw = manifest.get("Artifacts")
    artifacts_details = manifest.get("Artifacts Details", []) or []
    artifact_count = len(artifacts_details)

    has_public = False
    has_restricted = False
    has_private = False
    has_data = False
    has_software = False
    has_links = False

    for art in artifacts_details:
        access_level = (art.get("access_level") or "").lower()
        if access_level == "public":
            has_public = True
        elif access_level == "restricted":
            has_restricted = True
        elif access_level == "private":
            has_private = True

        # Files and folders may declare a resource type that indicates
        # whether the item is data or software.
        for file_ in art.get("files", []) or []:
            rtype = (file_.get("resource type") or "").lower()
            if rtype == "data":
                has_data = True
            elif rtype == "software":
                has_software = True

        for folder in art.get("folders", []) or []:
            rtype = (folder.get("resource type") or "").lower()
            if rtype == "data":
                has_data = True
            elif rtype == "software":
                has_software = True

        # Links are represented under `links` in the artifact schema
        if art.get("links"):
            if len(art["links"]) > 0:
                has_links = True

    # --- Canonical rdmc_fields mapping ---
    rdmc_fields = {
        "title": title or "(no title)",
        "rdmc_version": rdmc_version,
        "manifest_schema_version": manifest_schema_version,
        "manifest_file_path": manifest_file_path,
        "description": description,
        "subject": subject,
        "license": license_,
        "keywords_raw": keywords_raw,
        "container_concept": container_concept,
        "contributors_count": contributors_count,
        "contributors_text": contributors_text,
        "artifacts_raw": artifacts_raw,
        "artifact_count": artifact_count,
        "has_public_artifacts": has_public,
        "has_restricted_artifacts": has_restricted,
        "has_private_artifacts": has_private,
        "has_data_resources": has_data,
        "has_software_resources": has_software,
        "has_links": has_links,
    }

    return rdmc_fields, contributor_rows
