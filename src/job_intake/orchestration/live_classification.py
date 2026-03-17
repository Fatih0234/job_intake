"""DB-backed classification orchestration for canonical jobs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from job_intake.classifiers import classify_canonical_job
from job_intake.logging import get_logger
from job_intake.models import CanonicalJob, JobClassification, PipelineRun
from job_intake.settings import Settings, get_settings


class LiveClassificationRepository(Protocol):
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
    def list_latest_unclassified_jobs(self, *, limit: int) -> list[CanonicalJob]: ...
    def upsert_job_classification(
        self,
        job_id: UUID,
        classification: JobClassification,
    ) -> UUID: ...


@dataclass(slots=True)
class LiveClassificationSummary:
    jobs_attempted: int = 0
    jobs_classified: int = 0
    jobs_failed: int = 0
    shortlisted: int = 0
    errors: list[str] = field(default_factory=list)


class LinkedInLiveClassificationRunner:
    def __init__(self, repository: LiveClassificationRepository) -> None:
        self.repository = repository
        self.logger = get_logger(__name__)

    def run(
        self,
        *,
        settings: Settings | None = None,
        limit_jobs: int = 100,
    ) -> LiveClassificationSummary:
        _ = settings or get_settings()
        jobs = self.repository.list_latest_unclassified_jobs(limit=limit_jobs)
        summary = LiveClassificationSummary(jobs_attempted=len(jobs))
        pipeline_run_id = self.repository.insert_pipeline_run(
            PipelineRun(
                stage="live_classification",
                status="running",
                counters={"jobs_attempted": summary.jobs_attempted},
            )
        )

        try:
            for job in jobs:
                assert job.id is not None
                self.logger.info("Classifying job %s", job.canonical_job_key)
                try:
                    classification = classify_canonical_job(job)
                    self.repository.upsert_job_classification(job.id, classification)
                except Exception as exc:
                    summary.jobs_failed += 1
                    summary.errors.append(f"{job.canonical_job_key}: {exc}")
                    continue

                summary.jobs_classified += 1
                if classification.shortlist_decision:
                    summary.shortlisted += 1

            return summary
        finally:
            self.repository.update_pipeline_run(
                pipeline_run_id=pipeline_run_id,
                status="succeeded" if not summary.errors else "completed_with_errors",
                finished_at=datetime.now(UTC),
                counters={
                    "jobs_attempted": summary.jobs_attempted,
                    "jobs_classified": summary.jobs_classified,
                    "jobs_failed": summary.jobs_failed,
                    "shortlisted": summary.shortlisted,
                    "errors": len(summary.errors),
                },
                summary={"errors": summary.errors},
            )
