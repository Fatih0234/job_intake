from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from job_intake.models import CanonicalJob, JobClassification, PipelineRun
from job_intake.orchestration.live_classification import LinkedInLiveClassificationRunner


class FakeClassificationRepository:
    def __init__(self) -> None:
        self.classifications: list[tuple[UUID, JobClassification]] = []
        self.pipeline_updates: list[dict[str, object]] = []

    def insert_pipeline_run(self, pipeline_run: PipelineRun) -> UUID:
        return UUID("00000000-0000-4000-8000-000000000001")

    def update_pipeline_run(
        self,
        *,
        pipeline_run_id: UUID,
        status: str,
        finished_at: object | None = None,
        counters: dict[str, int] | None = None,
        summary: dict[str, object] | None = None,
    ) -> None:
        self.pipeline_updates.append(
            {
                "pipeline_run_id": pipeline_run_id,
                "status": status,
                "finished_at": finished_at,
                "counters": counters,
                "summary": summary,
            }
        )

    def list_latest_unclassified_jobs(self, *, limit: int) -> list[CanonicalJob]:
        return [
            CanonicalJob(
                id=UUID("00000000-0000-4000-8000-000000000010"),
                canonical_job_key="linkedin:4185654374",
                external_job_id="4185654374",
                source_job_url="https://www.linkedin.com/jobs/view/4185654374/",
                normalized_job_url="https://linkedin.com/jobs/view/4185654374",
                title="Werkstudent Data Engineer",
                company="Acme Analytics",
                city="Berlin",
                description_text="Build ETL pipelines with SQL and Airflow.",
                posted_text="2 days ago",
                source_search_name="berlin_data_engineering_student",
                last_seen_at=datetime(2026, 3, 17, 10, 0, tzinfo=UTC),
            )
        ][:limit]

    def upsert_job_classification(self, job_id: UUID, classification: JobClassification) -> UUID:
        self.classifications.append((job_id, classification))
        return UUID("00000000-0000-4000-8000-000000000011")


def test_live_classification_runner_classifies_unclassified_jobs() -> None:
    repository = FakeClassificationRepository()
    runner = LinkedInLiveClassificationRunner(repository)

    summary = runner.run(limit_jobs=1)

    assert summary.jobs_attempted == 1
    assert summary.jobs_classified == 1
    assert summary.jobs_failed == 0
    assert summary.shortlisted == 1
    assert summary.errors == []
    assert repository.classifications[0][0] == UUID("00000000-0000-4000-8000-000000000010")
    assert repository.pipeline_updates[-1]["status"] == "succeeded"
