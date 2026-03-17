"""Deterministic classification and shortlist helpers."""

from job_intake.classifiers.role_family import RoleFamilyDecision, classify_role_family
from job_intake.classifiers.shortlist import ShortlistDecision, decide_shortlist
from job_intake.classifiers.student_fit import StudentFitDecision, classify_student_fit
from job_intake.config_loader import load_all_configs
from job_intake.models import CanonicalJob, JobClassification


def classify_canonical_job(job: CanonicalJob) -> JobClassification:
    configs = load_all_configs()
    student_fit = classify_student_fit(job, configs.student_fit_keywords)
    role_family = classify_role_family(job, configs.role_family_keywords)
    shortlist = decide_shortlist(
        job,
        student_fit=student_fit.student_fit,
        role_family=role_family.role_family,
        target_cities=configs.linkedin_searches.target_cities,
    )

    return JobClassification(
        student_fit=student_fit.student_fit,
        role_family=role_family.role_family,
        shortlist_decision=shortlist.shortlist_decision,
        shortlist_reason=shortlist.shortlist_reason,
        signals={
            "student_fit": student_fit.signals,
            "role_family": {
                "scores": role_family.scores,
                "matched_terms": role_family.matched_terms,
            },
            "shortlist": shortlist.signals,
        },
    )


__all__ = [
    "RoleFamilyDecision",
    "ShortlistDecision",
    "StudentFitDecision",
    "classify_canonical_job",
    "classify_role_family",
    "classify_student_fit",
    "decide_shortlist",
]
