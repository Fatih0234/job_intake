"""DB-backed Notion sync orchestration for shortlisted jobs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from job_intake.logging import get_logger
from job_intake.models import PipelineRun
from job_intake.models.storage import ClassifiedJobRecord
from job_intake.notion.mapper import build_notion_job_page_blocks, build_notion_job_properties
from job_intake.notion.sync import NotionSyncCandidate, NotionSyncService
from job_intake.settings import Settings, get_settings


class NotionSyncRepository(Protocol):
    def insert_pipeline_run(self, pipeline_run: PipelineRun) -> UUID: ...
    def update_pipeline_run(
        self,
        *,
        pipeline_run_id: UUID,
        status: str,
        finished_at: datetime | None = None,
        counters: dict[str, int] | None = None,
        summary: dict[str, object] | None = None,
    ) -> None: ...
    def list_shortlisted_jobs_for_notion_sync(self, *, limit: int) -> list[ClassifiedJobRecord]: ...
    def upsert_notion_sync_state(
        self,
        *,
        job_id: UUID,
        notion_page_id: str | None,
        sync_status: str,
        last_error: str | None = None,
        payload_checksum: str | None = None,
    ) -> UUID: ...


@dataclass(slots=True)
class NotionSyncRuntimeSummary:
    jobs_attempted: int = 0
    synced_created: int = 0
    synced_updated: int = 0
    synced_skipped: int = 0
    sync_failed: int = 0
    errors: list[str] = field(default_factory=list)


def _checksum_payload(
    properties: dict[str, object | None],
    content_blocks: list[object],
) -> str:
    normalized = {
        key: value.isoformat() if isinstance(value, datetime) else value
        for key, value in properties.items()
        if key != "Synced At"
    }
    serialized = json.dumps(
        {
            "properties": normalized,
            "content_blocks": [
                {"type": block.type, "text": block.text}
                for block in content_blocks
            ],
        },
        sort_keys=True,
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


class NotionShortlistSyncRunner:
    def __init__(
        self,
        repository: NotionSyncRepository,
        *,
        sync_service: NotionSyncService,
    ) -> None:
        self.repository = repository
        self.sync_service = sync_service
        self.logger = get_logger(__name__)

    def run(
        self,
        *,
        settings: Settings | None = None,
        limit_jobs: int = 50,
    ) -> NotionSyncRuntimeSummary:
        _ = settings or get_settings()
        records = self.repository.list_shortlisted_jobs_for_notion_sync(limit=limit_jobs)
        summary = NotionSyncRuntimeSummary(jobs_attempted=len(records))
        pipeline_run_id = self.repository.insert_pipeline_run(
            PipelineRun(
                stage="notion_sync",
                status="running",
                counters={"jobs_attempted": summary.jobs_attempted},
            )
        )

        try:
            total_records = len(records)
            for index, record in enumerate(records, start=1):
                assert record.job.id is not None
                candidate = NotionSyncCandidate(
                    job=record.job,
                    classification=record.classification,
                )
                desired_properties = build_notion_job_properties(record.job, record.classification)
                desired_blocks = build_notion_job_page_blocks(record.job, record.classification)
                payload_checksum = _checksum_payload(desired_properties, desired_blocks)
                existing_state = record.notion_sync_state
                if (
                    existing_state is not None
                    and existing_state.sync_status == "synced"
                    and existing_state.payload_checksum == payload_checksum
                ):
                    summary.synced_skipped += 1
                    self.repository.upsert_notion_sync_state(
                        job_id=record.job.id,
                        notion_page_id=existing_state.notion_page_id,
                        sync_status="synced",
                        payload_checksum=payload_checksum,
                    )
                    continue

                self.logger.info(
                    "Syncing job %s/%s to Notion: %s",
                    index,
                    total_records,
                    record.job.canonical_job_key,
                )
                try:
                    page_result = self.sync_service.sync_candidate_with_page_hint(
                        candidate,
                        existing_page_id=(
                            existing_state.notion_page_id
                            if existing_state is not None
                            and existing_state.sync_status == "synced"
                            else None
                        ),
                    )
                    self.repository.upsert_notion_sync_state(
                        job_id=record.job.id,
                        notion_page_id=page_result.page_id or (
                            existing_state.notion_page_id if existing_state else None
                        ),
                        sync_status="synced",
                        payload_checksum=payload_checksum,
                    )
                except Exception as exc:
                    summary.sync_failed += 1
                    summary.errors.append(f"{record.job.canonical_job_key}: {exc}")
                    self.repository.upsert_notion_sync_state(
                        job_id=record.job.id,
                        notion_page_id=existing_state.notion_page_id if existing_state else None,
                        sync_status="failed",
                        last_error=str(exc),
                        payload_checksum=payload_checksum,
                    )
                    continue

                if page_result.action == "created":
                    summary.synced_created += 1
                elif page_result.action == "updated":
                    summary.synced_updated += 1
                else:
                    summary.synced_skipped += 1

            return summary
        finally:
            self.repository.update_pipeline_run(
                pipeline_run_id=pipeline_run_id,
                status="succeeded" if not summary.errors else "completed_with_errors",
                finished_at=datetime.now(UTC),
                counters={
                    "jobs_attempted": summary.jobs_attempted,
                    "synced_created": summary.synced_created,
                    "synced_updated": summary.synced_updated,
                    "synced_skipped": summary.synced_skipped,
                    "sync_failed": summary.sync_failed,
                    "errors": len(summary.errors),
                },
                summary={"errors": summary.errors},
            )
