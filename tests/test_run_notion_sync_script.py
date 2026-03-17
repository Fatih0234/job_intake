from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_notion_sync.py"
SPEC = importlib.util.spec_from_file_location("run_notion_sync_script", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_args_defaults_limit_jobs() -> None:
    args = MODULE.parse_args([])

    assert args.limit_jobs == 25


def test_parse_args_rejects_non_positive_limit_jobs() -> None:
    with pytest.raises(SystemExit):
        MODULE.parse_args(["--limit-jobs", "0"])
