"""Mapping from canonical jobs and classifications to Notion properties."""

from __future__ import annotations

from datetime import UTC, datetime

from job_intake.models import CanonicalJob, JobClassification
from job_intake.notion.schema import MANUAL_FIELDS_TO_PRESERVE, required_database_properties


def build_notion_job_properties(
    job: CanonicalJob,
    classification: JobClassification,
    *,
    synced_at: datetime | None = None,
) -> dict[str, object | None]:
    active_synced_at = synced_at or datetime.now(UTC)
    properties: dict[str, object | None] = {
        "Job Title": job.title,
        "Company": job.company,
        "City": job.city,
        "Platform": job.platform.value,
        "Role Family": classification.role_family.value,
        "Student Fit": classification.student_fit.value,
        "Posted Text": job.posted_text,
        "Job URL": job.normalized_job_url,
        "Shortlist Reason": classification.shortlist_reason,
        "Source Search Name": job.source_search_name,
        "Canonical Job Key": job.canonical_job_key,
        "Synced At": active_synced_at,
        "Last Seen At": job.last_seen_at,
    }
    managed_properties = {
        name: value
        for name, value in properties.items()
        if name in required_database_properties(include_optional=True)
        and name not in MANUAL_FIELDS_TO_PRESERVE
    }
    return managed_properties
