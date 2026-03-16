"""Core domain models shared across configuration, storage, and sync code."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field

RoleFamily = Literal[
    "data_engineering",
    "analytics_engineering",
    "analytics_bi",
    "ml_ai_engineering",
    "out_of_scope",
]

StudentFit = Literal["target_student_job", "possible_student_job", "not_student_job"]


def utc_now() -> datetime:
    return datetime.now(UTC)


class SearchDefinition(BaseModel):
    id: UUID | None = None
    name: str
    platform: str = "linkedin"
    city: str
    role_family: RoleFamily
    keywords: list[str] = Field(default_factory=list)
    enabled: bool = True
    query_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobDiscovery(BaseModel):
    id: UUID | None = None
    search_definition_id: UUID | None = None
    platform: str = "linkedin"
    external_job_id: str | None = None
    job_url: str
    rank_position: int | None = None
    discovered_at: datetime = Field(default_factory=utc_now)
    raw_payload: dict[str, Any] = Field(default_factory=dict)


class CanonicalJob(BaseModel):
    id: UUID | None = None
    canonical_job_key: str
    platform: str = "linkedin"
    external_job_id: str | None = None
    source_job_url: str
    normalized_job_url: str
    title: str
    company: str
    city: str
    country: str = "Germany"
    location_raw: str | None = None
    description_text: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    posted_text: str | None = None
    posted_at: datetime | None = None
    first_seen_at: datetime = Field(default_factory=utc_now)
    last_seen_at: datetime = Field(default_factory=utc_now)
    source_search_name: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class JobClassification(BaseModel):
    id: UUID | None = None
    job_id: UUID | None = None
    canonical_job_key: str | None = None
    student_fit: StudentFit
    role_family: RoleFamily
    shortlist_decision: bool
    shortlist_reason: str | None = None
    rule_version: str = "v1"
    signals: dict[str, Any] = Field(default_factory=dict)
