from __future__ import annotations

import pytest

from job_intake.inspection_cli import parse_inspection_args


def test_parse_args_supports_limit_and_repeated_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "inspect_pipeline_db.py",
            "--limit",
            "3",
            "--section",
            "jobs",
            "--section",
            "pipeline_runs",
        ],
    )

    args = parse_inspection_args()

    assert args.limit == 3
    assert args.section == ["jobs", "pipeline_runs"]


def test_parse_args_rejects_non_positive_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["inspect_pipeline_db.py", "--limit", "0"],
    )

    with pytest.raises(SystemExit):
        parse_inspection_args()
