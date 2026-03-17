"""Helpers for loading repository YAML configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from job_intake.models import (
    LoadedConfigs,
    RoleFamilyKeywordRules,
    SearchDefinitionsConfig,
    StudentFitKeywordRules,
)
from job_intake.settings import Settings, get_settings


def load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at {path}, got {type(data).__name__}.")
    return data


def load_config_model[ModelT: BaseModel](path: Path, model_type: type[ModelT]) -> ModelT:
    return model_type.model_validate(load_yaml_file(path))


def load_search_definitions_config(settings: Settings | None = None) -> SearchDefinitionsConfig:
    active_settings = settings or get_settings()
    return load_config_model(
        active_settings.configs_dir / "linkedin_searches.yaml",
        SearchDefinitionsConfig,
    )


def load_student_fit_keyword_rules(settings: Settings | None = None) -> StudentFitKeywordRules:
    active_settings = settings or get_settings()
    return load_config_model(
        active_settings.configs_dir / "student_fit_keywords.yaml",
        StudentFitKeywordRules,
    )


def load_role_family_keyword_rules(settings: Settings | None = None) -> RoleFamilyKeywordRules:
    active_settings = settings or get_settings()
    return load_config_model(
        active_settings.configs_dir / "role_family_keywords.yaml",
        RoleFamilyKeywordRules,
    )


def load_all_configs(settings: Settings | None = None) -> LoadedConfigs:
    active_settings = settings or get_settings()
    return LoadedConfigs(
        linkedin_searches=load_search_definitions_config(active_settings),
        student_fit_keywords=load_student_fit_keyword_rules(active_settings),
        role_family_keywords=load_role_family_keyword_rules(active_settings),
    )
