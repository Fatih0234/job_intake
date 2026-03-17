from __future__ import annotations

from job_intake.storage.inspection import (
    DEFAULT_SNAPSHOT_QUERIES,
    load_pipeline_snapshot,
    select_snapshot_queries,
)


class FakeCursor:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self.rows = rows

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, int]]] = []

    def execute(self, sql: str, params: dict[str, int]) -> FakeCursor:
        self.calls.append((sql, params))
        return FakeCursor([{"limit": params["limit"]}])


def test_default_snapshot_queries_cover_expected_sections() -> None:
    assert [query.section_name for query in DEFAULT_SNAPSHOT_QUERIES] == [
        "pipeline_runs",
        "search_definitions",
        "jobs",
        "job_classifications",
        "job_discoveries",
    ]


def test_load_pipeline_snapshot_executes_each_query_with_its_default_limit() -> None:
    connection = FakeConnection()

    snapshot = load_pipeline_snapshot(connection)

    assert list(snapshot) == [
        "pipeline_runs",
        "search_definitions",
        "jobs",
        "job_classifications",
        "job_discoveries",
    ]
    assert [call[1]["limit"] for call in connection.calls] == [5, 10, 10, 10, 10]
    assert snapshot["pipeline_runs"] == [{"limit": 5}]
    assert snapshot["job_discoveries"] == [{"limit": 10}]


def test_select_snapshot_queries_filters_and_preserves_requested_section_order() -> None:
    queries = select_snapshot_queries(
        section_names=["jobs", "pipeline_runs"],
        limit=None,
    )

    assert [query.section_name for query in queries] == ["jobs", "pipeline_runs"]
    assert [query.limit for query in queries] == [10, 5]


def test_select_snapshot_queries_applies_limit_override_to_selected_sections() -> None:
    queries = select_snapshot_queries(
        section_names=["pipeline_runs", "job_discoveries"],
        limit=3,
    )

    assert [query.section_name for query in queries] == [
        "pipeline_runs",
        "job_discoveries",
    ]
    assert [query.limit for query in queries] == [3, 3]
