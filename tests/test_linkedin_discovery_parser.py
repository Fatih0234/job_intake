from __future__ import annotations

from pathlib import Path

from job_intake.adapters.linkedin import parse_search_results_page

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "linkedin"


def read_fixture(name: str) -> str:
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_parse_search_results_page_extracts_discovery_records() -> None:
    discoveries = parse_search_results_page(
        read_fixture("list_search_results.html"),
        source_search_name="berlin_data_engineering_student",
    )

    assert len(discoveries) == 2
    assert discoveries[0].external_job_id == "4185654374"
    assert discoveries[0].title == "Data Engineering Working Student"
    assert discoveries[0].company == "Acme Analytics"
    assert discoveries[0].location_raw == "Berlin, Germany"
    assert discoveries[0].posted_text == "2 days ago"
    assert discoveries[0].source_search_name == "berlin_data_engineering_student"
    assert discoveries[0].to_job_discovery().discovery_url.startswith("https://www.linkedin.com/jobs/view/")


def test_parse_search_results_page_skips_malformed_cards() -> None:
    discoveries = parse_search_results_page(
        read_fixture("list_search_results_with_invalid_card.html"),
        source_search_name="munich_ml_ai_student",
    )

    assert len(discoveries) == 1
    assert discoveries[0].external_job_id == "4185654376"
    assert discoveries[0].rank_position == 1


def test_parse_search_results_page_returns_empty_list_without_cards() -> None:
    discoveries = parse_search_results_page(
        "<html><body><p>No results</p></body></html>",
        source_search_name="empty",
    )

    assert discoveries == []
