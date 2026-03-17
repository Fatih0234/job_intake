"""Shared enums and primitive types used across the pipeline."""

from __future__ import annotations

from enum import StrEnum


class Platform(StrEnum):
    LINKEDIN = "linkedin"


class RoleFamily(StrEnum):
    DATA_ENGINEERING = "data_engineering"
    ANALYTICS_ENGINEERING = "analytics_engineering"
    ANALYTICS_BI = "analytics_bi"
    ML_AI_ENGINEERING = "ml_ai_engineering"
    OUT_OF_SCOPE = "out_of_scope"


class StudentFit(StrEnum):
    TARGET_STUDENT_JOB = "target_student_job"
    POSSIBLE_STUDENT_JOB = "possible_student_job"
    NOT_STUDENT_JOB = "not_student_job"
