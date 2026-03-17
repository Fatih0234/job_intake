"""Thin orchestration for the student-job intake pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from job_intake.adapters.linkedin import parse_job_detail_page, parse_search_results_page
from job_intake.classifiers import classify_canonical_job
from job_intake.config_loader import load_all_configs
from job_intake.logging import get_logger
from job_intake.models import (
    CanonicalJob,
    JobClassification,
    JobDiscovery,
    PipelineRun,
    SearchDefinition,
)
from job_intake.notion.sync import NotionSyncCandidate, NotionSyncResult, NotionSyncService
from job_intake.search_definitions import build_executable_searches
from job_intake.settings import Settings, get_settings


class PipelineRepository(Protocol):
    def insert_pipeline_run(self, pipeline_run: PipelineRun) -> UUID: ...
    def update_pipeline_run(
        self,
        *,
        pipeline_run_id: UUID,
        status: str,
        finished_at: object | None = None,
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
    def upsert_job(self, job: CanonicalJob) -> UUID: ...
    def upsert_job_classification(
        self,
        job_id: UUID,
        classification: JobClassification,
    ) -> UUID: ...


@dataclass(slots=True)
class PipelineSummary:
    searches: int = 0
    discoveries: int = 0
    details: int = 0
    classified: int = 0
    shortlisted: int = 0
    synced_created: int = 0
    synced_updated: int = 0
    synced_skipped: int = 0
    errors: list[str] = field(default_factory=list)


class JobIntakePipeline:
    def __init__(
        self,
        *,
        repository: PipelineRepository | None = None,
        sync_service: NotionSyncService | None = None,
    ) -> None:
        self.repository = repository
        self.sync_service = sync_service
        self.logger = get_logger(__name__)

    def run_fixture_slice(
        self,
        *,
        discovery_html_by_search_name: dict[str, str],
        detail_html_by_url: dict[str, str],
        settings: Settings | None = None,
        limit_searches: int = 1,
    ) -> PipelineSummary:
        active_settings = settings or get_settings()
        configs = load_all_configs(active_settings)
        executable_searches = build_executable_searches(configs.linkedin_searches)[:limit_searches]
        summary = PipelineSummary(searches=len(executable_searches))
        sync_candidates: list[NotionSyncCandidate] = []

        pipeline_run_id = None
        if self.repository is not None:
            pipeline_run_id = self.repository.insert_pipeline_run(
                PipelineRun(
                    stage="pipeline",
                    status="running",
                    counters={"searches": summary.searches},
                )
            )

        try:
            definitions_by_name = {
                definition.name: definition
                for definition in configs.linkedin_searches.search_definitions
            }

            for search in executable_searches:
                self.logger.info("Processing search %s", search.definition_name)
                definition = definitions_by_name[search.definition_name]
                if self.repository is not None:
                    self.repository.upsert_search_definition(definition)

                discovery_html = discovery_html_by_search_name.get(search.definition_name)
                if discovery_html is None:
                    summary.errors.append(
                        f"Missing discovery HTML for search {search.definition_name}.",
                    )
                    continue

                discoveries = parse_search_results_page(
                    discovery_html,
                    source_search_name=search.definition_name,
                )
                summary.discoveries += len(discoveries)

                for discovery in discoveries:
                    if self.repository is not None:
                        self.repository.insert_job_discovery(
                            discovery.to_job_discovery(),
                            pipeline_run_id=pipeline_run_id,
                        )

                    detail_html = detail_html_by_url.get(discovery.job_url)
                    if detail_html is None:
                        summary.errors.append(
                            f"Missing detail HTML for job URL {discovery.job_url}.",
                        )
                        continue

                    detail = parse_job_detail_page(
                        detail_html,
                        source_search_name=search.definition_name,
                    )
                    job = detail.to_canonical_job()
                    classification = classify_canonical_job(job)
                    summary.details += 1
                    summary.classified += 1

                    if classification.shortlist_decision:
                        summary.shortlisted += 1
                    sync_candidates.append(
                        NotionSyncCandidate(
                            job=job,
                            classification=classification,
                        )
                    )

                    if self.repository is not None:
                        job_id = self.repository.upsert_job(job)
                        self.repository.upsert_job_classification(job_id, classification)

            if self.sync_service is not None:
                sync_result = self.sync_service.sync_shortlisted_jobs(sync_candidates)
            else:
                sync_result = NotionSyncResult()

            summary.synced_created = sync_result.created
            summary.synced_updated = sync_result.updated
            summary.synced_skipped = sync_result.skipped

            return summary
        finally:
            if self.repository is not None and pipeline_run_id is not None:
                self.repository.update_pipeline_run(
                    pipeline_run_id=pipeline_run_id,
                    status="succeeded" if not summary.errors else "completed_with_errors",
                    counters={
                        "searches": summary.searches,
                        "discoveries": summary.discoveries,
                        "details": summary.details,
                        "classified": summary.classified,
                        "shortlisted": summary.shortlisted,
                        "synced_created": summary.synced_created,
                        "synced_updated": summary.synced_updated,
                        "synced_skipped": summary.synced_skipped,
                        "errors": len(summary.errors),
                    },
                    summary={"errors": summary.errors},
                )
