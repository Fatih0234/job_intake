"""Core domain models shared across configuration, storage, and sync code."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from job_intake.canonical import normalize_linkedin_job_url, sanitize_url_text
from job_intake.models.common import Platform, RoleFamily, StudentFit


def utc_now() -> datetime:
    return datetime.now(UTC)


class SearchDefinition(BaseModel):
    id: UUID | None = None
    name: str
    platform: Platform = Platform.LINKEDIN
    city: str
    role_family: RoleFamily
    keywords: list[str] = Field(default_factory=list)
    filters: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True
    query_text: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_fields(self) -> SearchDefinition:
        self.name = self.name.strip()
        self.city = self.city.strip()
        self.keywords = [keyword.strip() for keyword in self.keywords if keyword.strip()]
        self.filters = {
            key.strip(): value.strip()
            for key, value in self.filters.items()
            if key.strip() and value.strip()
        }
        return self


class JobDiscovery(BaseModel):
    id: UUID | None = None
    search_definition_id: UUID | None = None
    platform: Platform = Platform.LINKEDIN
    external_job_id: str | None = None
    discovery_url: str
    rank_position: int | None = None
    discovered_at: datetime = Field(default_factory=utc_now)
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def normalize_fields(self) -> JobDiscovery:
        self.discovery_url = sanitize_url_text(self.discovery_url)
        return self


class CanonicalJob(BaseModel):
    id: UUID | None = None
    canonical_job_key: str
    platform: Platform = Platform.LINKEDIN
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

    @model_validator(mode="after")
    def normalize_fields(self) -> CanonicalJob:
        self.source_job_url = sanitize_url_text(self.source_job_url)
        self.normalized_job_url = normalize_linkedin_job_url(
            self.normalized_job_url or self.source_job_url
        )
        return self


class JobClassification(BaseModel):
    id: UUID | None = None
    job_id: UUID | None = None
    student_fit: StudentFit
    role_family: RoleFamily
    shortlist_decision: bool
    shortlist_reason: str | None = None
    rule_version: str = "v1"
    signals: dict[str, Any] = Field(default_factory=dict)
