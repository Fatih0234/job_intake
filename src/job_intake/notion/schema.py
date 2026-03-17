"""Notion schema contracts for the downstream shortlist workspace."""

from __future__ import annotations

from pydantic import BaseModel

DEFAULT_ROOT_PAGE_NAME = "Student Job Intake"
DEFAULT_DATABASE_NAME = "Student Jobs - Shortlist"


class NotionPropertySpec(BaseModel):
    type: str
    optional: bool = False
    manual: bool = False


DATABASE_PROPERTY_SPECS = {
    "Job Title": NotionPropertySpec(type="title"),
    "Company": NotionPropertySpec(type="rich_text"),
    "City": NotionPropertySpec(type="rich_text"),
    "Location Raw": NotionPropertySpec(type="rich_text", optional=True),
    "Platform": NotionPropertySpec(type="select"),
    "Role Family": NotionPropertySpec(type="select"),
    "Student Fit": NotionPropertySpec(type="select"),
    "Posted Text": NotionPropertySpec(type="rich_text"),
    "Description Snippet": NotionPropertySpec(type="rich_text"),
    "Employment Type": NotionPropertySpec(type="rich_text", optional=True),
    "Seniority": NotionPropertySpec(type="rich_text", optional=True),
    "Posted At": NotionPropertySpec(type="date", optional=True),
    "Job URL": NotionPropertySpec(type="url"),
    "Shortlist Reason": NotionPropertySpec(type="rich_text"),
    "Priority": NotionPropertySpec(type="select", manual=True),
    "Review Status": NotionPropertySpec(type="status", manual=True),
    "Application Status": NotionPropertySpec(type="status", manual=True),
    "Notes": NotionPropertySpec(type="rich_text", manual=True),
    "Source Search Name": NotionPropertySpec(type="rich_text"),
    "Canonical Job Key": NotionPropertySpec(type="rich_text"),
    "Synced At": NotionPropertySpec(type="date"),
    "Last Seen At": NotionPropertySpec(type="date", optional=True),
}

MANUAL_FIELDS_TO_PRESERVE = tuple(
    name for name, spec in DATABASE_PROPERTY_SPECS.items() if spec.manual
)


def required_database_properties(*, include_optional: bool = False) -> dict[str, str]:
    return {
        name: spec.type
        for name, spec in DATABASE_PROPERTY_SPECS.items()
        if include_optional or not spec.optional
    }


def missing_required_database_properties(
    existing_properties: dict[str, str],
    *,
    include_optional: bool = False,
) -> list[str]:
    missing: list[str] = []
    for property_name, property_type in required_database_properties(
        include_optional=include_optional,
    ).items():
        if existing_properties.get(property_name) != property_type:
            missing.append(property_name)
    return missing
