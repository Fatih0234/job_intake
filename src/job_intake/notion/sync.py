"""Notion sync interfaces for shortlisted jobs.

Supabase remains canonical. Notion is downstream and operational only.
Only shortlisted jobs should sync into the Notion review database, and manual workflow
fields must be preserved across updates.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

from job_intake.models import CanonicalJob, JobClassification, StudentFit
from job_intake.notion.client import NotionSyncClient
from job_intake.notion.mapper import build_notion_job_page_blocks, build_notion_job_properties


@dataclass(slots=True)
class NotionSyncCandidate:
    job: CanonicalJob
    classification: JobClassification


@dataclass(slots=True)
class NotionSyncResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0


@dataclass(slots=True)
class NotionSyncPageResult:
    action: str
    page_id: str | None = None


class NotionSyncService:
    """Idempotent downstream sync for shortlisted jobs.

    - Sync only shortlisted jobs, never the full raw corpus.
    - Preserve `Priority`, `Review Status`, `Application Status`, and `Notes`.
    - Use `Canonical Job Key` as the stable identity anchor.
    - Stay idempotent across reruns.
    """

    def __init__(self, client: NotionSyncClient, *, database_id: str) -> None:
        self.client = client
        self.database_id = database_id

    def sync_shortlisted_jobs(
        self,
        jobs: Iterable[NotionSyncCandidate],
    ) -> NotionSyncResult:
        result = NotionSyncResult()

        for candidate in jobs:
            page_result = self.sync_candidate(candidate)
            if page_result.action == "created":
                result.created += 1
            elif page_result.action == "updated":
                result.updated += 1
            else:
                result.skipped += 1

        return result

    def sync_candidate(self, candidate: NotionSyncCandidate) -> NotionSyncPageResult:
        return self.sync_candidate_with_page_hint(candidate)

    def sync_candidate_with_page_hint(
        self,
        candidate: NotionSyncCandidate,
        *,
        existing_page_id: str | None = None,
    ) -> NotionSyncPageResult:
        if not self._is_sync_candidate(candidate.classification):
            return NotionSyncPageResult(action="skipped")

        desired_properties = build_notion_job_properties(
            candidate.job,
            candidate.classification,
        )
        desired_blocks = build_notion_job_page_blocks(
            candidate.job,
            candidate.classification,
        )
        if existing_page_id:
            updated_page = self.client.update_database_page(
                page_id=existing_page_id,
                properties=desired_properties,
                content_blocks=desired_blocks,
            )
            return NotionSyncPageResult(action="updated", page_id=updated_page.id)

        existing_page = self.client.find_page_by_canonical_job_key(
            database_id=self.database_id,
            canonical_job_key=candidate.job.canonical_job_key,
        )
        if existing_page is None:
            created_page = self.client.create_database_page(
                database_id=self.database_id,
                properties=desired_properties,
                content_blocks=desired_blocks,
            )
            return NotionSyncPageResult(action="created", page_id=created_page.id)

        if self._managed_properties_match(
            existing_page.properties,
            desired_properties,
        ) and self._managed_blocks_match(existing_page.managed_blocks, desired_blocks):
            return NotionSyncPageResult(action="skipped", page_id=existing_page.id)

        updated_page = self.client.update_database_page(
            page_id=existing_page.id,
            properties=desired_properties,
            content_blocks=desired_blocks,
        )
        return NotionSyncPageResult(action="updated", page_id=updated_page.id)

    def _is_sync_candidate(self, classification: JobClassification) -> bool:
        return (
            classification.shortlist_decision
            and classification.student_fit is StudentFit.TARGET_STUDENT_JOB
        )

    def _managed_properties_match(
        self,
        existing_properties: dict[str, object | None],
        desired_properties: dict[str, object | None],
    ) -> bool:
        for property_name, desired_value in desired_properties.items():
            if property_name == "Synced At":
                continue
            existing_value = existing_properties.get(property_name)
            if isinstance(desired_value, datetime):
                desired_value = desired_value.isoformat()
            if isinstance(existing_value, datetime):
                existing_value = existing_value.isoformat()
            if existing_value != desired_value:
                return False
        return True

    def _managed_blocks_match(
        self,
        existing_blocks: tuple[object, ...],
        desired_blocks: list[object],
    ) -> bool:
        return list(existing_blocks) == desired_blocks
