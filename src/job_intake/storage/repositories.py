"""Thin repository helpers around the canonical job tables."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import Connection
from psycopg.types.json import Jsonb

from job_intake.models import CanonicalJob, JobClassification, SearchDefinition


class JobIntakeRepository:
    def __init__(self, connection: Connection[Any]) -> None:
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
                "config_payload": Jsonb(definition.metadata),
            },
        ).fetchone()
        assert row is not None
        return UUID(str(row["id"]))

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
        assert row is not None
        return UUID(str(row["id"]))

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
        assert row is not None
        return UUID(str(row["id"]))

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
        assert row is not None
        return UUID(str(row["id"]))

