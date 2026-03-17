from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "run_live_details.py"
SPEC = importlib.util.spec_from_file_location("run_live_details_script", SCRIPT_PATH)
assert SPEC is not None
assert SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_parse_args_defaults_delay_seconds() -> None:
    args = MODULE.parse_args([])

    assert args.limit_discoveries == 25
    assert args.delay_seconds == MODULE.DEFAULT_REQUEST_DELAY_SECONDS


def test_parse_args_accepts_explicit_delay_seconds() -> None:
    args = MODULE.parse_args(["--limit-discoveries", "10", "--delay-seconds", "1.5"])

    assert args.limit_discoveries == 10
    assert args.delay_seconds == 1.5


def test_parse_args_rejects_negative_delay_seconds() -> None:
    with pytest.raises(SystemExit):
        MODULE.parse_args(["--delay-seconds", "-0.1"])
