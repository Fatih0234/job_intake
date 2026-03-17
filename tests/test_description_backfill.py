from __future__ import annotations

from uuid import UUID

from job_intake.models import DescriptionBackfillCandidate, DescriptionBlock, PipelineRun
from job_intake.orchestration import DescriptionBackfillRunner


class FakeDescriptionBackfillRepository:
    def __init__(self, candidates: list[DescriptionBackfillCandidate]) -> None:
        self.candidates = candidates
        self.updates: list[dict[str, object | None]] = []
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

    def list_jobs_for_description_backfill(
        self,
        *,
        limit: int,
        include_already_structured: bool = False,
    ) -> list[DescriptionBackfillCandidate]:
        if include_already_structured:
            return self.candidates[:limit]
        return [
            candidate
            for candidate in self.candidates[:limit]
            if not candidate.description_blocks
        ]

    def update_job_description_content(
        self,
        *,
        job_id: UUID,
        description_text: str | None,
        description_blocks: list[dict[str, object]],
    ) -> None:
        self.updates.append(
            {
                "job_id": job_id,
                "description_text": description_text,
                "description_blocks": description_blocks,
            }
        )


def test_description_backfill_runner_updates_jobs_from_detail_html() -> None:
    repository = FakeDescriptionBackfillRepository(
        [
            DescriptionBackfillCandidate(
                job_id=UUID("00000000-0000-4000-8000-000000000010"),
                canonical_job_key="linkedin:4185654374",
                detail_html=(
                    "<div class=\"show-more-less-html__markup\">"
                    "<p><strong>Your tasks:</strong></p>"
                    "<ul><li>Build ETL pipelines</li></ul>"
                    "</div>"
                ),
            )
        ]
    )
    runner = DescriptionBackfillRunner(repository)

    summary = runner.run(limit_jobs=10)

    assert summary.jobs_scanned == 1
    assert summary.jobs_updated == 1
    assert summary.jobs_skipped == 0
    assert summary.jobs_failed == 0
    assert repository.updates[0]["description_text"] == "Your tasks:\n\nBuild ETL pipelines"
    assert repository.updates[0]["description_blocks"] == [
        {"type": "paragraph", "text": "Your tasks:"},
        {"type": "bulleted_list_item", "text": "Build ETL pipelines"},
    ]
    assert repository.pipeline_updates[-1]["status"] == "succeeded"


def test_description_backfill_runner_skips_when_existing_content_matches() -> None:
    repository = FakeDescriptionBackfillRepository(
        [
            DescriptionBackfillCandidate(
                job_id=UUID("00000000-0000-4000-8000-000000000011"),
                canonical_job_key="linkedin:4185654375",
                description_text="Build ETL pipelines.",
                description_blocks=[
                    DescriptionBlock(type="paragraph", text="Build ETL pipelines.")
                ],
                detail_html=(
                    "<div class=\"show-more-less-html__markup\">"
                    "<p>Build ETL pipelines.</p>"
                    "</div>"
                ),
            )
        ]
    )
    runner = DescriptionBackfillRunner(repository)

    summary = runner.run(limit_jobs=10, include_already_structured=True)

    assert summary.jobs_updated == 0
    assert summary.jobs_skipped == 1
    assert repository.updates == []
