"""Mapping from canonical jobs and classifications to Notion properties."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime

from job_intake.models import CanonicalJob, DescriptionBlock, JobClassification
from job_intake.notion.schema import MANUAL_FIELDS_TO_PRESERVE, required_database_properties

DESCRIPTION_SNIPPET_LENGTH = 450
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
    return _description_page_blocks(
        job.description_blocks,
        fallback_description_text=job.description_text,
    )


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


def _description_page_blocks(
    description_blocks: list[DescriptionBlock],
    *,
    fallback_description_text: str | None,
) -> list[NotionPageBlock]:
    if description_blocks:
        return [
            NotionPageBlock(
                type=_map_description_block_type(block.type),
                text=block.text,
            )
            for block in description_blocks
        ]

    return [
        NotionPageBlock(type="paragraph", text=paragraph)
        for paragraph in _description_paragraphs(fallback_description_text)
    ]


def _map_description_block_type(block_type: str) -> str:
    if block_type == "heading":
        return "heading_3"
    if block_type in {"paragraph", "bulleted_list_item", "numbered_list_item"}:
        return block_type
    raise ValueError(f"Unsupported description block type {block_type!r}.")
