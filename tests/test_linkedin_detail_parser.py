from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from job_intake.adapters.linkedin import parse_job_detail_page

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "linkedin"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_parse_job_detail_page_extracts_normalized_detail() -> None:
    detail = parse_job_detail_page(
        read_fixture("job_detail.html"),
        source_search_name="berlin_data_engineering_student",
    )

    canonical_job = detail.to_canonical_job()

    assert detail.external_job_id == "4185654374"
    assert [(block.type, block.text) for block in detail.description_blocks] == [
        (
            "paragraph",
            "Build and monitor pipelines for analytics workloads in a modern data platform.",
        )
    ]
    assert detail.employment_type == "Part-time"
    assert detail.seniority == "Internship"
    assert detail.industries == ["Software Development", "Data Infrastructure"]
    assert canonical_job.canonical_job_key == "linkedin:4185654374"
    assert canonical_job.city == "Berlin"
    assert canonical_job.metadata["job_function"] == "Engineering and Information Technology"


def test_parse_job_detail_page_handles_missing_optional_fields_explicitly() -> None:
    detail = parse_job_detail_page(read_fixture("job_detail_missing_optional_fields.html"))

    canonical_job = detail.to_canonical_job()

    assert detail.posted_text is None
    assert detail.seniority is None
    assert detail.job_function is None
    assert detail.industries == []
    assert canonical_job.canonical_job_key == "linkedin:4185654375"


def test_parse_job_detail_page_handles_live_public_guest_shape() -> None:
    detail = parse_job_detail_page(
        read_fixture("job_detail_live_public_de.html"),
        source_search_name="berlin_data_engineering_student",
    )

    canonical_job = detail.to_canonical_job()

    assert detail.external_job_id == "4382858518"
    assert [(block.type, block.text) for block in detail.description_blocks] == [
        ("paragraph", "Baue Datenpipelines und Analytics-Workflows in einer modernen Plattform.")
    ]
    assert (
        detail.job_url
        == "https://de.linkedin.com/jobs/view/werkstudent-data-engineering-bei-acme-analytics-4382858518"
    )
    assert detail.employment_type == "Teilzeit"
    assert detail.seniority == "Ausbildung/Praktikum"
    assert detail.job_function == "Ingenieurwesen und Informationstechnologie"
    assert detail.industries == [
        "Software Development",
        "Data Infrastructure",
        "IT Services",
    ]
    assert detail.posted_text == "Vor 5 Tagen"
    assert detail.posted_at == datetime(2026, 3, 11, 8, 29, 15, tzinfo=UTC)
    assert canonical_job.canonical_job_key == "linkedin:4382858518"
    assert canonical_job.city == "Berlin"


def test_parse_job_detail_page_falls_back_to_jsonld_for_required_fields() -> None:
    detail = parse_job_detail_page(
        """
        <html>
          <head>
            <link
              rel="canonical"
              href="https://de.linkedin.com/jobs/view/data-engineering-intern-4399999999"
            />
            <script type="application/ld+json">
              {
                "@context": "http://schema.org",
                "@type": "JobPosting",
                "title": "Data Engineering Intern",
                "datePosted": "2026-03-12T09:30:00.000Z",
                "description": "&lt;p&gt;Build reliable ETL pipelines.&lt;/p&gt;",
                "hiringOrganization": {
                  "@type": "Organization",
                  "name": "Fallback Corp"
                },
                "jobLocation": {
                  "@type": "Place",
                  "address": {
                    "@type": "PostalAddress",
                    "addressLocality": "Hamburg",
                    "addressCountry": "DE"
                  }
                }
              }
            </script>
          </head>
          <body></body>
        </html>
        """,
    )

    assert detail.external_job_id == "4399999999"
    assert detail.title == "Data Engineering Intern"
    assert detail.company == "Fallback Corp"
    assert detail.location_raw == "Hamburg"
    assert detail.description_text == "Build reliable ETL pipelines."
    assert [(block.type, block.text) for block in detail.description_blocks] == [
        ("paragraph", "Build reliable ETL pipelines.")
    ]
    assert detail.posted_at == datetime(2026, 3, 12, 9, 30, tzinfo=UTC)


def test_parse_job_detail_page_preserves_headings_and_lists_in_description_blocks() -> None:
    detail = parse_job_detail_page(
        """
        <html>
          <body>
            <div class="topcard__content-left" data-job-url="https://www.linkedin.com/jobs/view/4400000001/">
              <h1 class="topcard__title">Data Engineering Working Student</h1>
              <a class="topcard__org-name-link" href="https://www.linkedin.com/company/acme-analytics/">
                Acme Analytics
              </a>
              <span class="topcard__flavor topcard__flavor--bullet">Berlin, Germany</span>
            </div>
            <div class="show-more-less-html__markup">
              <p><strong>Your tasks:</strong></p>
              <ul>
                <li>Build pipelines</li>
                <li>Maintain dbt models</li>
              </ul>
              <p>Work closely with analytics stakeholders.</p>
            </div>
          </body>
        </html>
        """,
    )

    assert [(block.type, block.text) for block in detail.description_blocks] == [
        ("paragraph", "Your tasks:"),
        ("bulleted_list_item", "Build pipelines"),
        ("bulleted_list_item", "Maintain dbt models"),
        ("paragraph", "Work closely with analytics stakeholders."),
    ]
    assert detail.description_text == (
        "Your tasks:\n\n"
        "Build pipelines\n\n"
        "Maintain dbt models\n\n"
        "Work closely with analytics stakeholders."
    )


def test_parse_job_detail_page_raises_when_required_fields_are_missing() -> None:
    with pytest.raises(ValueError, match="missing one of"):
        parse_job_detail_page("<html><body><h1 class=\"topcard__title\">Broken</h1></body></html>")
