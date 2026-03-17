"""Mapping from canonical jobs and classifications to Notion properties."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import re

from job_intake.models import CanonicalJob, JobClassification
from job_intake.notion.schema import MANUAL_FIELDS_TO_PRESERVE, required_database_properties

DESCRIPTION_SNIPPET_LENGTH = 450
SYNCED_OVERVIEW_HEADING = "Synced Overview"
DESCRIPTION_HEADING = "Description"
SYNC_METADATA_HEADING = "Sync Metadata"
REVIEWER_NOTES_HEADING = "Reviewer Notes"
WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class NotionPageBlock:
    type: str
    text: str


def build_description_snippet(
    description_text: str | None,
    *,
    limit: int = DESCRIPTION_SNIPPET_LENGTH,
) -> str | None:
    normalized = _normalize_inline_text(description_text)
    if not normalized:
        return None
    if len(normalized) <= limit:
        return normalized

    truncated = normalized[:limit].rstrip()
    if " " in truncated:
        truncated = truncated.rsplit(" ", 1)[0]
    return f"{truncated}..."


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
        "Location Raw": job.location_raw,
        "Platform": job.platform.value,
        "Role Family": classification.role_family.value,
        "Student Fit": classification.student_fit.value,
        "Posted Text": job.posted_text,
        "Description Snippet": build_description_snippet(job.description_text),
        "Employment Type": job.employment_type,
        "Seniority": job.seniority,
        "Posted At": job.posted_at,
        "Job URL": job.source_job_url,
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


def build_notion_job_page_blocks(
    job: CanonicalJob,
    classification: JobClassification,
    *,
    synced_at: datetime | None = None,
) -> list[NotionPageBlock]:
    _ = synced_at or datetime.now(UTC)
    description_paragraphs = _description_paragraphs(job.description_text)

    blocks = [
        NotionPageBlock(type="heading_2", text=SYNCED_OVERVIEW_HEADING),
        NotionPageBlock(type="bulleted_list_item", text=f"Company: {job.company}"),
        NotionPageBlock(type="bulleted_list_item", text=f"City: {job.city}"),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Location Raw: {_display_value(job.location_raw)}",
        ),
        NotionPageBlock(type="bulleted_list_item", text=f"Platform: {job.platform.value}"),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Role Family: {classification.role_family.value}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Student Fit: {classification.student_fit.value}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Employment Type: {_display_value(job.employment_type)}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Seniority: {_display_value(job.seniority)}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Posted Text: {_display_value(job.posted_text)}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Posted At: {_display_datetime(job.posted_at)}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Last Seen At: {_display_datetime(job.last_seen_at)}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Source Search Name: {_display_value(job.source_search_name)}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=f"Source Job URL: {job.source_job_url}",
        ),
        NotionPageBlock(
            type="bulleted_list_item",
            text=(
                "Shortlist Reason: "
                f"{_display_value(classification.shortlist_reason)}"
            ),
        ),
        NotionPageBlock(type="heading_2", text=DESCRIPTION_HEADING),
    ]
    blocks.extend(
        NotionPageBlock(type="paragraph", text=paragraph)
        for paragraph in description_paragraphs
    )
    blocks.extend(
        [
            NotionPageBlock(type="heading_2", text=SYNC_METADATA_HEADING),
            NotionPageBlock(
                type="bulleted_list_item",
                text=f"Canonical Job Key: {job.canonical_job_key}",
            ),
            NotionPageBlock(
                type="bulleted_list_item",
                text=f"Normalized Job URL: {job.normalized_job_url}",
            ),
            NotionPageBlock(type="heading_2", text=REVIEWER_NOTES_HEADING),
        ]
    )
    return blocks


def _normalize_inline_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = WHITESPACE_RE.sub(" ", value).strip()
    return normalized or None


def _description_paragraphs(description_text: str | None) -> list[str]:
    if not description_text or not description_text.strip():
        return ["No description captured."]

    normalized = description_text.replace("\r\n", "\n").replace("\r", "\n").strip()
    paragraphs = [paragraph.strip() for paragraph in normalized.split("\n\n") if paragraph.strip()]
    if paragraphs:
        return paragraphs
    return [normalized]


def _display_datetime(value: datetime | None) -> str:
    if value is None:
        return "n/a"
    return value.isoformat()


def _display_value(value: str | None) -> str:
    return value.strip() if value and value.strip() else "n/a"
