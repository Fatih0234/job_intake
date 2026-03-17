"""Live LinkedIn discovery orchestration for public search pages."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from job_intake.adapters.linkedin.fetch import LinkedInFetchedPage, fetch_search_results_page
from job_intake.adapters.linkedin.parser_list import parse_search_results_page
from job_intake.config_loader import load_all_configs
from job_intake.logging import get_logger
from job_intake.models import JobDiscovery, PipelineRun, SearchDefinition
from job_intake.search_definitions import ExecutableSearch, build_executable_searches
from job_intake.settings import Settings, get_settings


class LiveDiscoveryRepository(Protocol):
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
    def upsert_search_definition(self, definition: SearchDefinition) -> UUID: ...
    def insert_job_discovery(
        self,
        discovery: JobDiscovery,
        *,
        pipeline_run_id: UUID | None = None,
        job_id: UUID | None = None,
    ) -> UUID: ...


class SearchResultsFetcher(Protocol):
    def __call__(self, search_url: str) -> LinkedInFetchedPage: ...


@dataclass(slots=True)
class LiveDiscoverySummary:
    searches_attempted: int = 0
    searches_succeeded: int = 0
    searches_failed: int = 0
    discoveries_inserted: int = 0
    errors: list[str] = field(default_factory=list)


class LinkedInLiveDiscoveryRunner:
    def __init__(
        self,
        repository: LiveDiscoveryRepository,
        *,
        fetcher: SearchResultsFetcher = fetch_search_results_page,
    ) -> None:
        self.repository = repository
        self.fetcher = fetcher
        self.logger = get_logger(__name__)

    def run(
        self,
        *,
        settings: Settings | None = None,
        limit_searches: int | None = None,
    ) -> LiveDiscoverySummary:
        active_settings = settings or get_settings()
        configs = load_all_configs(active_settings)
        executable_searches = build_executable_searches(configs.linkedin_searches)
        if limit_searches is not None:
            executable_searches = executable_searches[:limit_searches]

        summary = LiveDiscoverySummary(searches_attempted=len(executable_searches))
        pipeline_run_id = self.repository.insert_pipeline_run(
            PipelineRun(
                stage="live_discovery",
                status="running",
                counters={"searches_attempted": summary.searches_attempted},
            )
        )

        try:
            definitions_by_name = {
                definition.name: definition
                for definition in configs.linkedin_searches.search_definitions
            }

            for search in executable_searches:
                self.logger.info(
                    "Fetching LinkedIn search %s for %s",
                    search.definition_name,
                    search.query_text,
                )
                self._run_one_search(
                    search=search,
                    definition=definitions_by_name[search.definition_name],
                    pipeline_run_id=pipeline_run_id,
                    summary=summary,
                )

            return summary
        finally:
            self.repository.update_pipeline_run(
                pipeline_run_id=pipeline_run_id,
                status="succeeded" if not summary.errors else "completed_with_errors",
                finished_at=datetime.now(UTC),
                counters={
                    "searches_attempted": summary.searches_attempted,
                    "searches_succeeded": summary.searches_succeeded,
                    "searches_failed": summary.searches_failed,
                    "discoveries_inserted": summary.discoveries_inserted,
                    "errors": len(summary.errors),
                },
                summary={"errors": summary.errors},
            )

    def _run_one_search(
        self,
        *,
        search: ExecutableSearch,
        definition: SearchDefinition,
        pipeline_run_id: UUID,
        summary: LiveDiscoverySummary,
    ) -> None:
        search_definition_id = self.repository.upsert_search_definition(definition)

        try:
            fetched_page = self.fetcher(search.search_url)
            discoveries = parse_search_results_page(
                fetched_page.html,
                source_search_name=search.definition_name,
            )
        except Exception as exc:
            summary.searches_failed += 1
            summary.errors.append(f"{search.definition_name} [{search.query_text}]: {exc}")
            return

        for discovery in discoveries:
            self.repository.insert_job_discovery(
                discovery.to_job_discovery(search_definition_id=search_definition_id),
                pipeline_run_id=pipeline_run_id,
            )

        summary.searches_succeeded += 1
        summary.discoveries_inserted += len(discoveries)
