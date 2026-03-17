from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "backfill_job_description_blocks.py"
)
SPEC = importlib.util.spec_from_file_location(
    "backfill_job_description_blocks_script",
    SCRIPT_PATH,
)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_args_defaults() -> None:
    args = MODULE.parse_args([])

    assert args.apply is False
    assert args.limit_jobs == 100
    assert args.force is False


def test_parse_args_rejects_non_positive_limit_jobs() -> None:
    with pytest.raises(SystemExit):
        MODULE.parse_args(["--limit-jobs", "0"])
