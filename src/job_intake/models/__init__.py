"""Typed domain models for the job intake pipeline foundation."""

from job_intake.models.common import Platform, RoleFamily, StudentFit
from job_intake.models.config import (
    LoadedConfigs,
    RoleFamilyKeywordRules,
    SearchDefinitionsConfig,
    StudentFitKeywordRules,
)
from job_intake.models.core import (
    CanonicalJob,
    DescriptionBlock,
    JobClassification,
    JobDiscovery,
    SearchDefinition,
)
from job_intake.models.storage import (
    ClassifiedJobRecord,
    DescriptionBackfillCandidate,
    NotionSyncState,
    PipelineRun,
)
from job_intake.search_definitions import ExecutableSearch

__all__ = [
    "CanonicalJob",
    "ClassifiedJobRecord",
    "DescriptionBlock",
    "DescriptionBackfillCandidate",
    "ExecutableSearch",
    "JobClassification",
    "JobDiscovery",
    "LoadedConfigs",
    "NotionSyncState",
    "Platform",
    "PipelineRun",
    "RoleFamily",
    "RoleFamilyKeywordRules",
    "SearchDefinition",
    "SearchDefinitionsConfig",
    "StudentFit",
    "StudentFitKeywordRules",
]
