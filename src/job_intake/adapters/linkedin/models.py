"""LinkedIn-specific discovery and detail payload models."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from job_intake.canonical import (
    build_canonical_job_key,
    extract_linkedin_external_job_id,
    normalize_linkedin_job_url,
)
from job_intake.models import CanonicalJob, JobDiscovery
from job_intake.models.common import Platform


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


class LinkedInDiscoveryRecord(BaseModel):
    platform: Platform = Platform.LINKEDIN
    external_job_id: str | None = None
    title: str
    company: str
    location_raw: str | None = None
    job_url: str
    posted_text: str | None = None
    posted_at: datetime | None = None
    rank_position: int
    source_search_name: str
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    def to_job_discovery(self, *, search_definition_id: UUID | None = None) -> JobDiscovery:
        return JobDiscovery(
            search_definition_id=search_definition_id,
            platform=self.platform,
            external_job_id=self.external_job_id,
            discovery_url=self.job_url,
            rank_position=self.rank_position,
            raw_payload={
                "title": self.title,
                "company": self.company,
                "location_raw": self.location_raw,
                "posted_text": self.posted_text,
                "posted_at": self.posted_at.isoformat() if self.posted_at else None,
                "source_search_name": self.source_search_name,
                **self.raw_payload,
            },
        )


def derive_city(location_raw: str | None) -> str:
    if not location_raw:
        return "Unknown"
    city = location_raw.split(",", maxsplit=1)[0].strip()
    return city or "Unknown"


class LinkedInJobDetail(BaseModel):
    platform: Platform = Platform.LINKEDIN
    external_job_id: str | None = None
    job_url: str
    title: str
    company: str
    location_raw: str | None = None
    description_text: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    job_function: str | None = None
    industries: list[str] = Field(default_factory=list)
    posted_text: str | None = None
    posted_at: datetime | None = None
    source_search_name: str | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)

    def to_canonical_job(self) -> CanonicalJob:
        external_job_id = self.external_job_id or extract_linkedin_external_job_id(self.job_url)
        normalized_job_url = normalize_linkedin_job_url(self.job_url)
        return CanonicalJob(
            canonical_job_key=build_canonical_job_key(
                external_job_id=external_job_id,
                job_url=normalized_job_url,
            ),
            platform=self.platform,
            external_job_id=external_job_id,
            source_job_url=self.job_url,
            normalized_job_url=normalized_job_url,
            title=self.title,
            company=self.company,
            city=derive_city(self.location_raw),
            location_raw=self.location_raw,
            description_text=self.description_text,
            employment_type=self.employment_type,
            seniority=self.seniority,
            posted_text=self.posted_text,
            posted_at=self.posted_at,
            source_search_name=self.source_search_name,
            metadata={
                "job_function": self.job_function,
                "industries": self.industries,
                **self.raw_payload,
            },
        )
