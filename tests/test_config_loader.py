from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from job_intake.config_loader import (
    load_config_model,
    load_search_definitions_config,
)
from job_intake.models import Platform, RoleFamily, RoleFamilyKeywordRules, SearchDefinitionsConfig
from job_intake.settings import Settings


def test_load_search_definitions_config_returns_typed_models() -> None:
    config = load_search_definitions_config(Settings())

    assert config.target_cities[0] == "Oldenburg"
    assert config.search_definitions[0].platform is Platform.LINKEDIN
    assert config.search_definitions[0].role_family is RoleFamily.DATA_ENGINEERING


def test_search_definition_config_rejects_non_target_city(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_linkedin_searches.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            target_cities:
              - Berlin
            search_definitions:
              - name: invalid_search
                platform: linkedin
                city: Munich
                role_family: data_engineering
                enabled: true
                keywords:
                  - Werkstudent Data Engineering
            """
        ).strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="non-target city"):
        load_config_model(config_path, SearchDefinitionsConfig)


def test_role_family_keyword_rules_require_all_in_scope_families(
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "invalid_role_family_keywords.yaml"
    config_path.write_text(
        textwrap.dedent(
            """
            role_families:
              data_engineering:
                keywords:
                  - airflow
            """
        ).strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Missing keyword rules"):
        load_config_model(config_path, RoleFamilyKeywordRules)
