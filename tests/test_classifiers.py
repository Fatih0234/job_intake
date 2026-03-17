from __future__ import annotations

from job_intake.classifiers import (
    classify_canonical_job,
    classify_role_family,
    classify_student_fit,
)
from job_intake.classifiers.shortlist import decide_shortlist
from job_intake.config_loader import load_all_configs
from job_intake.models import CanonicalJob, RoleFamily, StudentFit


def build_job(
    *,
    title: str,
    description_text: str | None,
    city: str,
    employment_type: str | None = None,
    seniority: str | None = None,
) -> CanonicalJob:
    return CanonicalJob(
        canonical_job_key="linkedin:test",
        source_job_url="https://www.linkedin.com/jobs/view/999999999/",
        normalized_job_url="https://linkedin.com/jobs/view/999999999",
        title=title,
        company="Acme Analytics",
        city=city,
        description_text=description_text,
        employment_type=employment_type,
        seniority=seniority,
    )


def test_classify_student_fit_recognizes_german_working_student_signal() -> None:
    configs = load_all_configs()
    job = build_job(
        title="Werkstudent Data Engineering",
        description_text="Arbeite an ETL Pipelines und Airflow Jobs.",
        city="Berlin",
        employment_type="Teilzeit",
    )

    decision = classify_student_fit(job, configs.student_fit_keywords)

    assert decision.student_fit is StudentFit.TARGET_STUDENT_JOB
    assert "Werkstudent" in decision.signals["positive_terms"]


def test_classify_student_fit_marks_possible_when_only_supporting_terms_match() -> None:
    configs = load_all_configs()
    job = build_job(
        title="Data Engineer",
        description_text="Part-time role suitable for a master student.",
        city="Berlin",
    )

    decision = classify_student_fit(job, configs.student_fit_keywords)

    assert decision.student_fit is StudentFit.POSSIBLE_STUDENT_JOB
    assert "part-time" in decision.signals["supporting_terms"]


def test_classify_student_fit_rejects_senior_role_without_student_terms() -> None:
    configs = load_all_configs()
    job = build_job(
        title="Senior Data Engineer",
        description_text="Lead the platform engineering team.",
        city="Berlin",
        seniority="Senior",
    )

    decision = classify_student_fit(job, configs.student_fit_keywords)

    assert decision.student_fit is StudentFit.NOT_STUDENT_JOB
    assert "senior" in decision.signals["negative_terms"]


def test_classify_role_family_prefers_analytics_engineering_keywords() -> None:
    configs = load_all_configs()
    job = build_job(
        title="Analytics Engineering Intern",
        description_text="Build dbt models, semantic layers, and warehouse transformations.",
        city="Hamburg",
    )

    decision = classify_role_family(job, configs.role_family_keywords)

    assert decision.role_family is RoleFamily.ANALYTICS_ENGINEERING
    assert decision.scores["analytics_engineering"] > decision.scores["analytics_bi"]


def test_decide_shortlist_rejects_missing_description_or_out_of_scope_city() -> None:
    decision = decide_shortlist(
        build_job(
            title="Werkstudent BI Analyst",
            description_text=None,
            city="Paris",
        ),
        student_fit=StudentFit.TARGET_STUDENT_JOB,
        role_family=RoleFamily.ANALYTICS_BI,
        target_cities=["Berlin", "Hamburg"],
    )

    assert decision.shortlist_decision is False
    assert decision.signals["sync_candidate"] is False
    assert "city out of scope" in decision.shortlist_reason
    assert "missing required fields" in decision.shortlist_reason


def test_classify_canonical_job_returns_shortlist_reason_and_sync_candidate() -> None:
    classification = classify_canonical_job(
        build_job(
            title="Working Student Machine Learning Engineer",
            description_text="Support ML pipelines, evaluation, and MLOps tasks.",
            city="Berlin",
            employment_type="Part-time",
        )
    )

    assert classification.student_fit is StudentFit.TARGET_STUDENT_JOB
    assert classification.role_family is RoleFamily.ML_AI_ENGINEERING
    assert classification.shortlist_decision is True
    assert classification.signals["shortlist"]["sync_candidate"] is True
