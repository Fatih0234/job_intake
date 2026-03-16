"""Helpers for loading repository YAML configuration files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from job_intake.settings import Settings, get_settings

CONFIG_FILES = (
    "linkedin_searches.yaml",
    "student_fit_keywords.yaml",
    "role_family_keywords.yaml",
)


def load_yaml_file(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping at {path}, got {type(data).__name__}.")
    return data


def load_all_configs(settings: Settings | None = None) -> dict[str, dict[str, Any]]:
    active_settings = settings or get_settings()
    configs: dict[str, dict[str, Any]] = {}
    for filename in CONFIG_FILES:
        path = active_settings.configs_dir / filename
        configs[filename] = load_yaml_file(path)
    return configs

