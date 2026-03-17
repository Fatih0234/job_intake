"""Live LinkedIn detail-page orchestration for discovered jobs."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import sleep
from typing import Protocol
from uuid import UUID

from job_intake.adapters.linkedin.fetch import LinkedInFetchedPage, fetch_job_detail_page
from job_intake.adapters.linkedin.parser_detail import parse_job_detail_page
from job_intake.logging import get_logger
from job_intake.models import CanonicalJob, JobDiscovery, PipelineRun
from job_intake.settings import Settings, get_settings


class LiveDetailsRepository(Protocol):
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
    def list_latest_unlinked_job_discoveries(self, *, limit: int) -> list[JobDiscovery]: ...
    def upsert_job(self, job: CanonicalJob) -> UUID: ...
    def update_job_discovery_job_link(
        self,
        *,
        discovery_id: UUID,
        job_id: UUID,
    ) -> None: ...


class DetailPageFetcher(Protocol):
    def __call__(self, job_url: str) -> LinkedInFetchedPage: ...


@dataclass(slots=True)
class LiveDetailsSummary:
    discoveries_attempted: int = 0
    details_succeeded: int = 0
    details_failed: int = 0
    jobs_upserted: int = 0
    discoveries_linked: int = 0
    errors: list[str] = field(default_factory=list)


class LinkedInLiveDetailsRunner:
    def __init__(
        self,
        repository: LiveDetailsRepository,
        *,
        fetcher: DetailPageFetcher = fetch_job_detail_page,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.repository = repository
        self.fetcher = fetcher
        self.sleeper = sleeper
        self.logger = get_logger(__name__)

    def run(
        self,
        *,
        settings: Settings | None = None,
        limit_discoveries: int = 25,
        request_delay_seconds: float = 0.0,
    ) -> LiveDetailsSummary:
        _ = settings or get_settings()
        candidates = self.repository.list_latest_unlinked_job_discoveries(limit=limit_discoveries)
        summary = LiveDetailsSummary(discoveries_attempted=len(candidates))
        pipeline_run_id = self.repository.insert_pipeline_run(
            PipelineRun(
                stage="live_details",
                status="running",
                counters={"discoveries_attempted": summary.discoveries_attempted},
            )
        )

        try:
            for index, discovery in enumerate(candidates):
                self._run_one_discovery(
                    discovery=discovery,
                    summary=summary,
                )
                is_last_discovery = index == len(candidates) - 1
                if request_delay_seconds > 0 and not is_last_discovery:
                    self.logger.info(
                        "Sleeping %.2fs before next LinkedIn detail request",
                        request_delay_seconds,
                    )
                    self.sleeper(request_delay_seconds)

            return summary
        finally:
            self.repository.update_pipeline_run(
                pipeline_run_id=pipeline_run_id,
                status="succeeded" if not summary.errors else "completed_with_errors",
                finished_at=datetime.now(UTC),
                counters={
                    "discoveries_attempted": summary.discoveries_attempted,
                    "details_succeeded": summary.details_succeeded,
                    "details_failed": summary.details_failed,
                    "jobs_upserted": summary.jobs_upserted,
                    "discoveries_linked": summary.discoveries_linked,
                    "errors": len(summary.errors),
                },
                summary={"errors": summary.errors},
            )

    def _run_one_discovery(
        self,
        *,
        discovery: JobDiscovery,
        summary: LiveDetailsSummary,
    ) -> None:
        assert discovery.id is not None
        source_search_name = (
            str(discovery.raw_payload.get("source_search_name") or "").strip() or None
        )
        self.logger.info("Fetching LinkedIn detail %s", discovery.discovery_url)

        try:
            fetched_page = self.fetcher(discovery.discovery_url)
            detail = parse_job_detail_page(
                fetched_page.html,
                source_search_name=source_search_name,
            )
            job_id = self.repository.upsert_job(detail.to_canonical_job())
            self.repository.update_job_discovery_job_link(
                discovery_id=discovery.id,
                job_id=job_id,
            )
        except Exception as exc:
            summary.details_failed += 1
            summary.errors.append(f"{discovery.discovery_url}: {exc}")
            return

        summary.details_succeeded += 1
        summary.jobs_upserted += 1
        summary.discoveries_linked += 1
