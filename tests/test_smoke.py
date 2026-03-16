from __future__ import annotations

from job_intake.config_loader import load_all_configs
from job_intake.settings import Settings
from job_intake.smoke import run_smoke_check


def test_all_yaml_configs_parse() -> None:
    configs = load_all_configs(Settings())

    assert set(configs.keys()) == {
        "linkedin_searches.yaml",
        "student_fit_keywords.yaml",
        "role_family_keywords.yaml",
    }
    assert "search_definitions" in configs["linkedin_searches.yaml"]


def test_smoke_check_runs_without_db_credentials() -> None:
    result = run_smoke_check(Settings())

    assert result["settings_loaded"] is True
    assert result["sample_external_key"] == "linkedin:1234567890"
    assert result["sample_fallback_key"].startswith("linkedin:url:")

