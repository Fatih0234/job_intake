"""Read-only inspection helpers for recent pipeline database state."""

from __future__ import annotations

from collections import OrderedDict
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol


class QueryCursor(Protocol):
    def fetchall(self) -> list[dict[str, Any]]: ...


class QueryExecutor(Protocol):
    def execute(self, sql: str, params: dict[str, Any]) -> QueryCursor: ...


@dataclass(frozen=True, slots=True)
class SnapshotQuery:
    section_name: str
    limit: int
    sql: str


DEFAULT_SNAPSHOT_QUERIES: tuple[SnapshotQuery, ...] = (
    SnapshotQuery(
        section_name="pipeline_runs",
        limit=5,
        sql="""
        select
            id,
            stage,
            status,
            started_at,
            finished_at,
            counters,
            summary
        from pipeline_runs
        order by started_at desc
        limit %(limit)s
        """,
    ),
    SnapshotQuery(
        section_name="search_definitions",
        limit=10,
        sql="""
        select
            id,
            name,
            city,
            role_family,
            is_enabled,
            updated_at
        from search_definitions
        order by updated_at desc
        limit %(limit)s
        """,
    ),
    SnapshotQuery(
        section_name="jobs",
        limit=10,
        sql="""
        select
            id,
            canonical_job_key,
            title,
            company,
            city,
            source_search_name,
            last_seen_at
        from jobs
        order by last_seen_at desc, created_at desc
        limit %(limit)s
        """,
    ),
    SnapshotQuery(
        section_name="job_classifications",
        limit=10,
        sql="""
        select
            jc.id,
            j.canonical_job_key,
            j.title,
            jc.student_fit,
            jc.role_family,
            jc.shortlist_decision,
            jc.shortlist_reason,
            jc.updated_at
        from job_classifications jc
        join jobs j on j.id = jc.job_id
        order by jc.updated_at desc
        limit %(limit)s
        """,
    ),
    SnapshotQuery(
        section_name="job_discoveries",
        limit=10,
        sql="""
        select
            jd.id,
            jd.discovery_url,
            jd.external_job_id,
            jd.rank_position,
            jd.discovered_at,
            sd.name as search_definition_name,
            j.canonical_job_key
        from job_discoveries jd
        left join search_definitions sd on sd.id = jd.search_definition_id
        left join jobs j on j.id = jd.job_id
        order by jd.discovered_at desc, jd.created_at desc
        limit %(limit)s
        """,
    ),
)

DEFAULT_SNAPSHOT_SECTION_NAMES: tuple[str, ...] = tuple(
    query.section_name for query in DEFAULT_SNAPSHOT_QUERIES
)


def select_snapshot_queries(
    *,
    section_names: Iterable[str] | None = None,
    limit: int | None = None,
    available_queries: Iterable[SnapshotQuery] = DEFAULT_SNAPSHOT_QUERIES,
) -> tuple[SnapshotQuery, ...]:
    selected_names = list(section_names) if section_names is not None else None
    selected_name_set = set(selected_names) if selected_names is not None else None
    queries: list[SnapshotQuery] = []

    for query in available_queries:
        if selected_name_set is not None and query.section_name not in selected_name_set:
            continue
        queries.append(
            SnapshotQuery(
                section_name=query.section_name,
                limit=limit if limit is not None else query.limit,
                sql=query.sql,
            )
        )

    if selected_names is None:
        return tuple(queries)

    query_by_name = {query.section_name: query for query in queries}
    return tuple(query_by_name[name] for name in selected_names if name in query_by_name)


def load_pipeline_snapshot(
    connection: QueryExecutor,
    *,
    queries: Iterable[SnapshotQuery] = DEFAULT_SNAPSHOT_QUERIES,
) -> OrderedDict[str, list[dict[str, Any]]]:
    snapshot: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()

    for query in queries:
        rows = connection.execute(query.sql, {"limit": query.limit}).fetchall()
        snapshot[query.section_name] = rows

    return snapshot
