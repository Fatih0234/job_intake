"""Storage-facing models for pipeline run and sync state records."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from job_intake.models.core import utc_now


class PipelineRun(BaseModel):
    id: UUID | None = None
    stage: str
    status: str
    started_at: datetime = Field(default_factory=utc_now)
    finished_at: datetime | None = None
    counters: dict[str, int] = Field(default_factory=dict)
    summary: dict[str, Any] = Field(default_factory=dict)


class NotionSyncState(BaseModel):
    id: UUID | None = None
    job_id: UUID
    notion_page_id: str | None = None
    sync_status: str
    last_attempted_at: datetime | None = None
    last_synced_at: datetime | None = None
    last_error: str | None = None
    payload_checksum: str | None = None
