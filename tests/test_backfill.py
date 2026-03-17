from __future__ import annotations

from typing import Any

from job_intake.storage.backfill import (
    apply_job_discovery_backfill,
    build_job_discovery_backfill_report,
)


class FakeCursor:
    def __init__(
        self,
        *,
        row: dict[str, object] | None = None,
        rows: list[dict[str, object]] | None = None,
    ) -> None:
        self.row = row
        self.rows = rows or []

    def fetchone(self) -> dict[str, object] | None:
        return self.row

    def fetchall(self) -> list[dict[str, object]]:
        return self.rows


class FakeConnection:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.next_fetchone_rows: list[dict[str, Any]] = [
            {
                "candidate_rows": 4,
                "rows_missing_search_definition": 4,
                "rows_missing_job": 4,
                "rows_matchable_search_definition": 4,
                "rows_matchable_job": 4,
                "rows_unmatched_search_definition": 0,
                "rows_unmatched_job": 0,
            },
            {
                "rows_updated": 4,
                "search_definition_links_applied": 4,
                "job_links_applied": 4,
            },
        ]
        self.next_fetchall_rows: list[list[dict[str, Any]]] = [
            [
                {
                    "id": "discovery-1",
                    "matched_search_definition_id": "search-1",
                    "matched_job_id": "job-1",
                }
            ],
        ]

    def execute(self, sql: str, params: dict[str, object]) -> FakeCursor:
        self.calls.append((sql, params))
        if "limit %(limit)s" in sql:
            return FakeCursor(rows=self.next_fetchall_rows.pop(0))
        return FakeCursor(row=self.next_fetchone_rows.pop(0))


def test_build_job_discovery_backfill_report_returns_counts_and_preview() -> None:
    connection = FakeConnection()

    report = build_job_discovery_backfill_report(connection, preview_limit=5)

    assert report.candidate_rows == 4
    assert report.rows_matchable_search_definition == 4
    assert report.rows_matchable_job == 4
    assert report.preview_rows == [
        {
            "id": "discovery-1",
            "matched_search_definition_id": "search-1",
            "matched_job_id": "job-1",
        }
    ]
    assert connection.calls[1][1] == {"limit": 5}


def test_apply_job_discovery_backfill_returns_applied_counts() -> None:
    connection = FakeConnection()
    _ = build_job_discovery_backfill_report(connection)

    result = apply_job_discovery_backfill(connection)

    assert result == {
        "rows_updated": 4,
        "search_definition_links_applied": 4,
        "job_links_applied": 4,
    }
