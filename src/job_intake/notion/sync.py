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
from job_intake.notion.mapper import build_notion_job_properties


@dataclass(slots=True)
class NotionSyncCandidate:
    job: CanonicalJob
    classification: JobClassification


@dataclass(slots=True)
class NotionSyncResult:
    created: int = 0
    updated: int = 0
    skipped: int = 0


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
            if not self._is_sync_candidate(candidate.classification):
                result.skipped += 1
                continue

            desired_properties = build_notion_job_properties(
                candidate.job,
                candidate.classification,
            )
            existing_page = self.client.find_page_by_canonical_job_key(
                database_id=self.database_id,
                canonical_job_key=candidate.job.canonical_job_key,
            )
            if existing_page is None:
                self.client.create_database_page(
                    database_id=self.database_id,
                    properties=desired_properties,
                )
                result.created += 1
                continue

            if self._managed_properties_match(existing_page.properties, desired_properties):
                result.skipped += 1
                continue

            self.client.update_database_page(
                page_id=existing_page.id,
                properties=desired_properties,
            )
            result.updated += 1

        return result

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
