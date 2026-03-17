"""Helpers for previewing and applying historical storage backfills."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class BackfillCursor(Protocol):
    def fetchone(self) -> dict[str, Any] | None: ...
    def fetchall(self) -> list[dict[str, Any]]: ...


class BackfillExecutor(Protocol):
    def execute(self, sql: str, params: dict[str, Any]) -> BackfillCursor: ...


@dataclass(frozen=True, slots=True)
class JobDiscoveryBackfillReport:
    candidate_rows: int
    rows_missing_search_definition: int
    rows_missing_job: int
    rows_matchable_search_definition: int
    rows_matchable_job: int
    rows_unmatched_search_definition: int
    rows_unmatched_job: int
    preview_rows: list[dict[str, Any]]


BACKFILL_SUMMARY_SQL = """
with candidate_rows as (
    select
        jd.id,
        jd.search_definition_id,
        jd.job_id,
        sd_match.id as matched_search_definition_id,
        job_match.id as matched_job_id
    from job_discoveries jd
    left join lateral (
        select sd.id
        from search_definitions sd
        where sd.name = jd.raw_payload->>'source_search_name'
        limit 1
    ) as sd_match on jd.search_definition_id is null
    left join lateral (
        select j.id
        from jobs j
        where jd.external_job_id is not null
          and j.platform = jd.platform
          and j.external_job_id = jd.external_job_id
        order by j.updated_at desc nulls last, j.created_at desc
        limit 1
    ) as job_match on jd.job_id is null
    where jd.search_definition_id is null or jd.job_id is null
)
select
    count(*) as candidate_rows,
    count(*) filter (where search_definition_id is null) as rows_missing_search_definition,
    count(*) filter (where job_id is null) as rows_missing_job,
    count(*) filter (
        where search_definition_id is null and matched_search_definition_id is not null
    ) as rows_matchable_search_definition,
    count(*) filter (where job_id is null and matched_job_id is not null) as rows_matchable_job,
    count(*) filter (
        where search_definition_id is null and matched_search_definition_id is null
    ) as rows_unmatched_search_definition,
    count(*) filter (where job_id is null and matched_job_id is null) as rows_unmatched_job
from candidate_rows
"""

BACKFILL_PREVIEW_SQL = """
with candidate_rows as (
    select
        jd.id,
        jd.discovery_url,
        jd.external_job_id,
        jd.discovered_at,
        jd.raw_payload->>'source_search_name' as source_search_name,
        jd.search_definition_id,
        jd.job_id,
        sd_match.id as matched_search_definition_id,
        job_match.id as matched_job_id,
        job_match.canonical_job_key
    from job_discoveries jd
    left join lateral (
        select sd.id
        from search_definitions sd
        where sd.name = jd.raw_payload->>'source_search_name'
        limit 1
    ) as sd_match on jd.search_definition_id is null
    left join lateral (
        select j.id, j.canonical_job_key
        from jobs j
        where jd.external_job_id is not null
          and j.platform = jd.platform
          and j.external_job_id = jd.external_job_id
        order by j.updated_at desc nulls last, j.created_at desc
        limit 1
    ) as job_match on jd.job_id is null
    where jd.search_definition_id is null or jd.job_id is null
)
select
    id,
    discovery_url,
    external_job_id,
    discovered_at,
    source_search_name,
    search_definition_id,
    job_id,
    matched_search_definition_id,
    matched_job_id,
    canonical_job_key
from candidate_rows
where matched_search_definition_id is not null or matched_job_id is not null
order by discovered_at desc
limit %(limit)s
"""

BACKFILL_APPLY_SQL = """
with candidate_updates as (
    select
        jd.id,
        case
            when jd.search_definition_id is null then sd_match.id
            else null
        end as new_search_definition_id,
        case
            when jd.job_id is null then job_match.id
            else null
        end as new_job_id
    from job_discoveries jd
    left join lateral (
        select sd.id
        from search_definitions sd
        where sd.name = jd.raw_payload->>'source_search_name'
        limit 1
    ) as sd_match on jd.search_definition_id is null
    left join lateral (
        select j.id
        from jobs j
        where jd.external_job_id is not null
          and j.platform = jd.platform
          and j.external_job_id = jd.external_job_id
        order by j.updated_at desc nulls last, j.created_at desc
        limit 1
    ) as job_match on jd.job_id is null
    where (jd.search_definition_id is null and sd_match.id is not null)
       or (jd.job_id is null and job_match.id is not null)
),
updated_rows as (
    update job_discoveries jd
    set
        search_definition_id = coalesce(jd.search_definition_id, cu.new_search_definition_id),
        job_id = coalesce(jd.job_id, cu.new_job_id)
    from candidate_updates cu
    where jd.id = cu.id
    returning
        cu.new_search_definition_id,
        cu.new_job_id
)
select
    count(*) as rows_updated,
    count(*) filter (where new_search_definition_id is not null) as search_definition_links_applied,
    count(*) filter (where new_job_id is not null) as job_links_applied
from updated_rows
"""


def build_job_discovery_backfill_report(
    connection: BackfillExecutor,
    *,
    preview_limit: int = 10,
) -> JobDiscoveryBackfillReport:
    summary_row = connection.execute(BACKFILL_SUMMARY_SQL, {}).fetchone()
    assert summary_row is not None
    preview_rows = connection.execute(
        BACKFILL_PREVIEW_SQL,
        {"limit": preview_limit},
    ).fetchall()

    return JobDiscoveryBackfillReport(
        candidate_rows=int(summary_row["candidate_rows"]),
        rows_missing_search_definition=int(summary_row["rows_missing_search_definition"]),
        rows_missing_job=int(summary_row["rows_missing_job"]),
        rows_matchable_search_definition=int(summary_row["rows_matchable_search_definition"]),
        rows_matchable_job=int(summary_row["rows_matchable_job"]),
        rows_unmatched_search_definition=int(summary_row["rows_unmatched_search_definition"]),
        rows_unmatched_job=int(summary_row["rows_unmatched_job"]),
        preview_rows=preview_rows,
    )


def apply_job_discovery_backfill(connection: BackfillExecutor) -> dict[str, int]:
    row = connection.execute(BACKFILL_APPLY_SQL, {}).fetchone()
    assert row is not None
    return {
        "rows_updated": int(row["rows_updated"]),
        "search_definition_links_applied": int(row["search_definition_links_applied"]),
        "job_links_applied": int(row["job_links_applied"]),
    }
