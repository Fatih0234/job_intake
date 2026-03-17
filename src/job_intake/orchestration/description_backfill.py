"""One-off backfill for structured job descriptions from stored LinkedIn detail HTML."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from job_intake.adapters.linkedin import extract_job_description_content
from job_intake.logging import get_logger
from job_intake.models import DescriptionBackfillCandidate, PipelineRun


class DescriptionBackfillRepository(Protocol):
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
    def list_jobs_for_description_backfill(
        self,
        *,
        limit: int,
        include_already_structured: bool = False,
    ) -> list[DescriptionBackfillCandidate]: ...
    def update_job_description_content(
        self,
        *,
        job_id: UUID,
        description_text: str | None,
        description_blocks: list[dict[str, object]],
    ) -> None: ...


@dataclass(slots=True)
class DescriptionBackfillSummary:
    jobs_scanned: int = 0
    jobs_updated: int = 0
    jobs_skipped: int = 0
    jobs_failed: int = 0
    errors: list[str] = field(default_factory=list)


class DescriptionBackfillRunner:
    def __init__(self, repository: DescriptionBackfillRepository) -> None:
        self.repository = repository
        self.logger = get_logger(__name__)

    def preview_candidates(
        self,
        *,
        limit_jobs: int,
        include_already_structured: bool = False,
    ) -> list[DescriptionBackfillCandidate]:
        return self.repository.list_jobs_for_description_backfill(
            limit=limit_jobs,
            include_already_structured=include_already_structured,
        )

    def run(
        self,
        *,
        limit_jobs: int,
        include_already_structured: bool = False,
    ) -> DescriptionBackfillSummary:
        candidates = self.preview_candidates(
            limit_jobs=limit_jobs,
            include_already_structured=include_already_structured,
        )
        summary = DescriptionBackfillSummary(jobs_scanned=len(candidates))
        pipeline_run_id = self.repository.insert_pipeline_run(
            PipelineRun(
                stage="description_backfill",
                status="running",
                counters={"jobs_scanned": summary.jobs_scanned},
            )
        )

        try:
            for candidate in candidates:
                self._run_one_candidate(candidate, summary)
            return summary
        finally:
            self.repository.update_pipeline_run(
                pipeline_run_id=pipeline_run_id,
                status="succeeded" if not summary.errors else "completed_with_errors",
                finished_at=datetime.now(UTC),
                counters={
                    "jobs_scanned": summary.jobs_scanned,
                    "jobs_updated": summary.jobs_updated,
                    "jobs_skipped": summary.jobs_skipped,
                    "jobs_failed": summary.jobs_failed,
                    "errors": len(summary.errors),
                },
                summary={"errors": summary.errors},
            )

    def _run_one_candidate(
        self,
        candidate: DescriptionBackfillCandidate,
        summary: DescriptionBackfillSummary,
    ) -> None:
        self.logger.info("Backfilling description blocks for %s", candidate.canonical_job_key)
        try:
            description_text, description_blocks = extract_job_description_content(
                candidate.detail_html
            )
        except Exception as exc:
            summary.jobs_failed += 1
            summary.errors.append(f"{candidate.canonical_job_key}: {exc}")
            return

        serialized_blocks = [block.model_dump(mode="json") for block in description_blocks]
        existing_blocks = [block.model_dump(mode="json") for block in candidate.description_blocks]
        if (
            candidate.description_text == description_text
            and existing_blocks == serialized_blocks
        ):
            summary.jobs_skipped += 1
            return

        self.repository.update_job_description_content(
            job_id=candidate.job_id,
            description_text=description_text,
            description_blocks=serialized_blocks,
        )
        summary.jobs_updated += 1


def summarize_preview_rows(
    candidates: Iterable[DescriptionBackfillCandidate],
) -> list[dict[str, object]]:
    return [
        {
            "canonical_job_key": candidate.canonical_job_key,
            "job_id": str(candidate.job_id),
            "existing_block_count": len(candidate.description_blocks),
            "description_present": bool(candidate.description_text),
        }
        for candidate in candidates
    ]
