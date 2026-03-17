"""Thin repository helpers around the canonical job tables."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from psycopg.types.json import Jsonb

from job_intake.models import (
    CanonicalJob,
    DescriptionBackfillCandidate,
    JobClassification,
    JobDiscovery,
    NotionSyncState,
    PipelineRun,
    SearchDefinition,
)
from job_intake.models.storage import ClassifiedJobRecord


def _read_uuid(row: dict[str, Any] | None) -> UUID:
    assert row is not None
    return UUID(str(row["id"]))


class SQLExecutor(Protocol):
    def execute(self, sql: str, params: dict[str, Any]) -> Any: ...


class JobIntakeRepository:
    def __init__(self, connection: SQLExecutor) -> None:
        self.connection = connection

    def upsert_search_definition(self, definition: SearchDefinition) -> UUID:
        row = self.connection.execute(
            """
            insert into search_definitions (
                name,
                platform,
                city,
                role_family,
                keywords,
                query_text,
                is_enabled,
                config_payload
            )
            values (
                %(name)s,
                %(platform)s,
                %(city)s,
                %(role_family)s,
                %(keywords)s,
                %(query_text)s,
                %(is_enabled)s,
                %(config_payload)s
            )
            on conflict (name) do update
            set
                platform = excluded.platform,
                city = excluded.city,
                role_family = excluded.role_family,
                keywords = excluded.keywords,
                query_text = excluded.query_text,
                is_enabled = excluded.is_enabled,
                config_payload = excluded.config_payload,
                updated_at = timezone('utc', now())
            returning id
            """,
            {
                "name": definition.name,
                "platform": definition.platform,
                "city": definition.city,
                "role_family": definition.role_family,
                "keywords": Jsonb(definition.keywords),
                "query_text": definition.query_text,
                "is_enabled": definition.enabled,
                "config_payload": Jsonb(
                    {
                        "filters": definition.filters,
                        **definition.metadata,
                    }
                ),
            },
        ).fetchone()
        return _read_uuid(row)

    def insert_pipeline_run(self, pipeline_run: PipelineRun) -> UUID:
        row = self.connection.execute(
            """
            insert into pipeline_runs (
                stage,
                status,
                started_at,
                finished_at,
                counters,
                summary
            )
            values (
                %(stage)s,
                %(status)s,
                %(started_at)s,
                %(finished_at)s,
                %(counters)s,
                %(summary)s
            )
            returning id
            """,
            {
                "stage": pipeline_run.stage,
                "status": pipeline_run.status,
                "started_at": pipeline_run.started_at,
                "finished_at": pipeline_run.finished_at,
                "counters": Jsonb(pipeline_run.counters),
                "summary": Jsonb(pipeline_run.summary),
            },
        ).fetchone()
        return _read_uuid(row)

    def update_pipeline_run(
        self,
        *,
        pipeline_run_id: UUID,
        status: str,
        finished_at: datetime | None = None,
        counters: dict[str, int] | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        self.connection.execute(
            """
            update pipeline_runs
            set
                status = %(status)s,
                finished_at = %(finished_at)s,
                counters = coalesce(%(counters)s, counters),
                summary = coalesce(%(summary)s, summary),
                updated_at = timezone('utc', now())
            where id = %(pipeline_run_id)s
            """,
            {
                "pipeline_run_id": pipeline_run_id,
                "status": status,
                "finished_at": finished_at,
                "counters": Jsonb(counters) if counters is not None else None,
                "summary": Jsonb(summary) if summary is not None else None,
            },
        )

    def insert_job_discovery(
        self,
        discovery: JobDiscovery,
        *,
        pipeline_run_id: UUID | None = None,
        job_id: UUID | None = None,
    ) -> UUID:
        row = self.connection.execute(
            """
            insert into job_discoveries (
                search_definition_id,
                pipeline_run_id,
                job_id,
                platform,
                external_job_id,
                discovery_url,
                rank_position,
                discovered_at,
                raw_payload
            )
            values (
                %(search_definition_id)s,
                %(pipeline_run_id)s,
                %(job_id)s,
                %(platform)s,
                %(external_job_id)s,
                %(discovery_url)s,
                %(rank_position)s,
                %(discovered_at)s,
                %(raw_payload)s
            )
            returning id
            """,
            {
                "search_definition_id": discovery.search_definition_id,
                "pipeline_run_id": pipeline_run_id,
                "job_id": job_id,
                "platform": discovery.platform,
                "external_job_id": discovery.external_job_id,
                "discovery_url": discovery.discovery_url,
                "rank_position": discovery.rank_position,
                "discovered_at": discovery.discovered_at,
                "raw_payload": Jsonb(discovery.raw_payload),
            },
        ).fetchone()
        return _read_uuid(row)

    def list_latest_unlinked_job_discoveries(self, *, limit: int) -> list[JobDiscovery]:
        rows = self.connection.execute(
            """
            select
                id,
                search_definition_id,
                platform,
                external_job_id,
                discovery_url,
                rank_position,
                discovered_at,
                raw_payload
            from (
                select distinct on (coalesce(external_job_id, discovery_url))
                    id,
                    search_definition_id,
                    platform,
                    external_job_id,
                    discovery_url,
                    rank_position,
                    discovered_at,
                    raw_payload,
                    created_at
                from job_discoveries
                where job_id is null
                order by
                    coalesce(external_job_id, discovery_url),
                    discovered_at desc,
                    created_at desc
            ) latest_unlinked
            order by discovered_at desc
            limit %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        return [JobDiscovery.model_validate(row) for row in rows]

    def update_job_discovery_job_link(
        self,
        *,
        discovery_id: UUID,
        job_id: UUID,
    ) -> None:
        self.connection.execute(
            """
            update job_discoveries
            set
                job_id = %(job_id)s,
                updated_at = timezone('utc', now())
            where id = %(discovery_id)s
            """,
            {
                "discovery_id": discovery_id,
                "job_id": job_id,
            },
        )

    def list_latest_unclassified_jobs(self, *, limit: int) -> list[CanonicalJob]:
        rows = self.connection.execute(
            """
            select
                j.id,
                j.canonical_job_key,
                j.platform,
                j.external_job_id,
                j.source_job_url,
                j.normalized_job_url,
                j.title,
                j.company,
                j.city,
                j.country,
                j.location_raw,
                j.description_text,
                j.description_blocks,
                j.employment_type,
                j.seniority,
                j.posted_text,
                j.posted_at,
                j.first_seen_at,
                j.last_seen_at,
                j.source_search_name,
                j.metadata
            from jobs j
            left join job_classifications jc on jc.job_id = j.id
            where jc.job_id is null
            order by j.last_seen_at desc, j.created_at desc
            limit %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        return [CanonicalJob.model_validate(row) for row in rows]

    def list_jobs_for_description_backfill(
        self,
        *,
        limit: int,
        include_already_structured: bool = False,
    ) -> list[DescriptionBackfillCandidate]:
        structured_filter = ""
        if not include_already_structured:
            structured_filter = """
              and coalesce(jsonb_array_length(j.description_blocks), 0) = 0
            """

        rows = self.connection.execute(
            f"""
            select
                j.id as job_id,
                j.canonical_job_key,
                j.description_text,
                j.description_blocks,
                j.metadata->>'detail_html' as detail_html
            from jobs j
            where
                jsonb_typeof(j.metadata->'detail_html') = 'string'
                {structured_filter}
            order by j.last_seen_at desc, j.created_at desc
            limit %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        return [
            DescriptionBackfillCandidate.model_validate(
                {
                    "job_id": row["job_id"],
                    "canonical_job_key": row["canonical_job_key"],
                    "description_text": row["description_text"],
                    "description_blocks": row["description_blocks"] or [],
                    "detail_html": row["detail_html"],
                }
            )
            for row in rows
        ]

    def list_shortlisted_jobs_for_notion_sync(self, *, limit: int) -> list[ClassifiedJobRecord]:
        rows = self.connection.execute(
            """
            select
                j.id as job_id,
                j.canonical_job_key,
                j.platform,
                j.external_job_id,
                j.source_job_url,
                j.normalized_job_url,
                j.title,
                j.company,
                j.city,
                j.country,
                j.location_raw,
                j.description_text,
                j.description_blocks,
                j.employment_type,
                j.seniority,
                j.posted_text,
                j.posted_at,
                j.first_seen_at,
                j.last_seen_at,
                j.source_search_name,
                j.metadata,
                jc.id as classification_id,
                jc.student_fit,
                jc.role_family,
                jc.shortlist_decision,
                jc.shortlist_reason,
                jc.rule_version,
                jc.signals,
                nss.id as notion_sync_state_id,
                nss.notion_page_id,
                nss.sync_status,
                nss.last_attempted_at,
                nss.last_synced_at,
                nss.last_error,
                nss.payload_checksum
            from jobs j
            join job_classifications jc on jc.job_id = j.id
            left join notion_sync_state nss on nss.job_id = j.id
            where
                jc.shortlist_decision = true
                and jc.student_fit = 'target_student_job'
            order by j.last_seen_at desc, j.created_at desc
            limit %(limit)s
            """,
            {"limit": limit},
        ).fetchall()
        records: list[ClassifiedJobRecord] = []
        for row in rows:
            job = CanonicalJob.model_validate(
                {
                    "id": row["job_id"],
                    "canonical_job_key": row["canonical_job_key"],
                    "platform": row["platform"],
                    "external_job_id": row["external_job_id"],
                    "source_job_url": row["source_job_url"],
                    "normalized_job_url": row["normalized_job_url"],
                    "title": row["title"],
                    "company": row["company"],
                    "city": row["city"],
                    "country": row["country"],
                    "location_raw": row["location_raw"],
                    "description_text": row["description_text"],
                    "description_blocks": row["description_blocks"] or [],
                    "employment_type": row["employment_type"],
                    "seniority": row["seniority"],
                    "posted_text": row["posted_text"],
                    "posted_at": row["posted_at"],
                    "first_seen_at": row["first_seen_at"],
                    "last_seen_at": row["last_seen_at"],
                    "source_search_name": row["source_search_name"],
                    "metadata": row["metadata"],
                }
            )
            classification = JobClassification.model_validate(
                {
                    "id": row["classification_id"],
                    "job_id": row["job_id"],
                    "student_fit": row["student_fit"],
                    "role_family": row["role_family"],
                    "shortlist_decision": row["shortlist_decision"],
                    "shortlist_reason": row["shortlist_reason"],
                    "rule_version": row["rule_version"],
                    "signals": row["signals"],
                }
            )
            notion_sync_state = None
            if row["notion_sync_state_id"] is not None:
                notion_sync_state = NotionSyncState.model_validate(
                    {
                        "id": row["notion_sync_state_id"],
                        "job_id": row["job_id"],
                        "notion_page_id": row["notion_page_id"],
                        "sync_status": row["sync_status"],
                        "last_attempted_at": row["last_attempted_at"],
                        "last_synced_at": row["last_synced_at"],
                        "last_error": row["last_error"],
                        "payload_checksum": row["payload_checksum"],
                    }
                )
            records.append(
                ClassifiedJobRecord(
                    job=job,
                    classification=classification,
                    notion_sync_state=notion_sync_state,
                )
            )
        return records

    def upsert_job(self, job: CanonicalJob) -> UUID:
        row = self.connection.execute(
            """
            insert into jobs (
                canonical_job_key,
                platform,
                external_job_id,
                source_job_url,
                normalized_job_url,
                title,
                company,
                city,
                country,
                location_raw,
                description_text,
                description_blocks,
                employment_type,
                seniority,
                posted_text,
                posted_at,
                first_seen_at,
                last_seen_at,
                source_search_name,
                metadata
            )
            values (
                %(canonical_job_key)s,
                %(platform)s,
                %(external_job_id)s,
                %(source_job_url)s,
                %(normalized_job_url)s,
                %(title)s,
                %(company)s,
                %(city)s,
                %(country)s,
                %(location_raw)s,
                %(description_text)s,
                %(description_blocks)s,
                %(employment_type)s,
                %(seniority)s,
                %(posted_text)s,
                %(posted_at)s,
                %(first_seen_at)s,
                %(last_seen_at)s,
                %(source_search_name)s,
                %(metadata)s
            )
            on conflict (canonical_job_key) do update
            set
                external_job_id = excluded.external_job_id,
                source_job_url = excluded.source_job_url,
                normalized_job_url = excluded.normalized_job_url,
                title = excluded.title,
                company = excluded.company,
                city = excluded.city,
                country = excluded.country,
                location_raw = excluded.location_raw,
                description_text = excluded.description_text,
                description_blocks = excluded.description_blocks,
                employment_type = excluded.employment_type,
                seniority = excluded.seniority,
                posted_text = excluded.posted_text,
                posted_at = excluded.posted_at,
                last_seen_at = excluded.last_seen_at,
                source_search_name = excluded.source_search_name,
                metadata = excluded.metadata,
                updated_at = timezone('utc', now())
            returning id
            """,
            {
                "canonical_job_key": job.canonical_job_key,
                "platform": job.platform,
                "external_job_id": job.external_job_id,
                "source_job_url": job.source_job_url,
                "normalized_job_url": job.normalized_job_url,
                "title": job.title,
                "company": job.company,
                "city": job.city,
                "country": job.country,
                "location_raw": job.location_raw,
                "description_text": job.description_text,
                "description_blocks": Jsonb(
                    [block.model_dump(mode="json") for block in job.description_blocks]
                ),
                "employment_type": job.employment_type,
                "seniority": job.seniority,
                "posted_text": job.posted_text,
                "posted_at": job.posted_at,
                "first_seen_at": job.first_seen_at,
                "last_seen_at": job.last_seen_at,
                "source_search_name": job.source_search_name,
                "metadata": Jsonb(job.metadata),
            },
        ).fetchone()
        return _read_uuid(row)

    def update_job_description_content(
        self,
        *,
        job_id: UUID,
        description_text: str | None,
        description_blocks: list[dict[str, object]],
    ) -> None:
        self.connection.execute(
            """
            update jobs
            set
                description_text = %(description_text)s,
                description_blocks = %(description_blocks)s,
                updated_at = timezone('utc', now())
            where id = %(job_id)s
            """,
            {
                "job_id": job_id,
                "description_text": description_text,
                "description_blocks": Jsonb(description_blocks),
            },
        )

    def upsert_job_classification(self, job_id: UUID, classification: JobClassification) -> UUID:
        row = self.connection.execute(
            """
            insert into job_classifications (
                job_id,
                student_fit,
                role_family,
                shortlist_decision,
                shortlist_reason,
                rule_version,
                signals
            )
            values (
                %(job_id)s,
                %(student_fit)s,
                %(role_family)s,
                %(shortlist_decision)s,
                %(shortlist_reason)s,
                %(rule_version)s,
                %(signals)s
            )
            on conflict (job_id) do update
            set
                student_fit = excluded.student_fit,
                role_family = excluded.role_family,
                shortlist_decision = excluded.shortlist_decision,
                shortlist_reason = excluded.shortlist_reason,
                rule_version = excluded.rule_version,
                signals = excluded.signals,
                updated_at = timezone('utc', now())
            returning id
            """,
            {
                "job_id": job_id,
                "student_fit": classification.student_fit,
                "role_family": classification.role_family,
                "shortlist_decision": classification.shortlist_decision,
                "shortlist_reason": classification.shortlist_reason,
                "rule_version": classification.rule_version,
                "signals": Jsonb(classification.signals),
            },
        ).fetchone()
        return _read_uuid(row)

    def upsert_notion_sync_state(
        self,
        *,
        job_id: UUID,
        notion_page_id: str | None,
        sync_status: str,
        last_error: str | None = None,
        payload_checksum: str | None = None,
    ) -> UUID:
        row = self.connection.execute(
            """
            insert into notion_sync_state (
                job_id,
                notion_page_id,
                sync_status,
                last_attempted_at,
                last_synced_at,
                last_error,
                payload_checksum
            )
            values (
                %(job_id)s,
                %(notion_page_id)s,
                %(sync_status)s,
                timezone('utc', now()),
                case when %(sync_status)s = 'synced' then timezone('utc', now()) else null end,
                %(last_error)s,
                %(payload_checksum)s
            )
            on conflict (job_id) do update
            set
                notion_page_id = excluded.notion_page_id,
                sync_status = excluded.sync_status,
                last_attempted_at = excluded.last_attempted_at,
                last_synced_at = excluded.last_synced_at,
                last_error = excluded.last_error,
                payload_checksum = excluded.payload_checksum,
                updated_at = timezone('utc', now())
            returning id
            """,
            {
                "job_id": job_id,
                "notion_page_id": notion_page_id,
                "sync_status": sync_status,
                "last_error": last_error,
                "payload_checksum": payload_checksum,
            },
        ).fetchone()
        return _read_uuid(row)
