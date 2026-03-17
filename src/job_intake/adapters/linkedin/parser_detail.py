"""Parser for LinkedIn public job detail pages."""

from __future__ import annotations

import re
from html import unescape

from job_intake.adapters.linkedin.models import LinkedInJobDetail, parse_iso_datetime

CLASS_ATTR_RE = re.compile(r'class="[^"]*\b{class_name}\b[^"]*"')
ATTR_RE_TEMPLATE = r'{attribute}="(?P<value>[^"]+)"'
JOB_ID_RE = re.compile(r"/jobs/view/(?P<job_id>\d+)")
CRITERIA_ITEM_RE = re.compile(
    r"<li\b[^>]*class=\"[^\"]*description__job-criteria-item[^\"]*\"[^>]*>(?P<item>.*?)</li>",
    re.IGNORECASE | re.DOTALL,
)


def _strip_tags(value: str) -> str:
    return " ".join(unescape(re.sub(r"<[^>]+>", " ", value)).split())


def _extract_attr(block: str, *, class_name: str, attribute: str) -> str | None:
    pattern = re.compile(
        rf"<(?P<tag>\w+)\b[^>]*{CLASS_ATTR_RE.pattern.format(class_name=re.escape(class_name))}"
        rf'[^>]*{ATTR_RE_TEMPLATE.format(attribute=re.escape(attribute))}[^>]*>',
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(block)
    return unescape(match.group("value")).strip() if match else None


def _extract_text(block: str, *, class_name: str, tag: str) -> str | None:
    pattern = re.compile(
        rf"<{tag}\b[^>]*{CLASS_ATTR_RE.pattern.format(class_name=re.escape(class_name))}[^>]*>"
        rf"(?P<value>.*?)</{tag}>",
        re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(block)
    if not match:
        return None
    cleaned = _strip_tags(match.group("value"))
    return cleaned or None


def _extract_criteria(block: str) -> dict[str, str]:
    criteria: dict[str, str] = {}
    for match in CRITERIA_ITEM_RE.finditer(block):
        item = match.group("item")
        heading = _extract_text(item, class_name="description__job-criteria-subheader", tag="h3")
        value = _extract_text(item, class_name="description__job-criteria-text", tag="span")
        if heading and value:
            criteria[heading.lower()] = value
    return criteria


def parse_job_detail_page(html: str, *, source_search_name: str | None = None) -> LinkedInJobDetail:
    job_url = _extract_attr(html, class_name="topcard__link", attribute="href") or _extract_attr(
        html,
        class_name="topcard__content-left",
        attribute="data-job-url",
    )
    title = _extract_text(html, class_name="topcard__title", tag="h1")
    company = _extract_text(html, class_name="topcard__org-name-link", tag="a")
    if not company:
        company = _extract_text(html, class_name="topcard__flavor", tag="span")

    location_raw = _extract_text(html, class_name="topcard__flavor--bullet", tag="span")
    posted_text = _extract_text(html, class_name="posted-time-ago__text", tag="span")
    description_text = _extract_text(html, class_name="show-more-less-html__markup", tag="div")
    posted_datetime = _extract_attr(html, class_name="posted-time-ago__text", attribute="datetime")
    criteria = _extract_criteria(html)

    if not job_url or not title or not company:
        raise ValueError("LinkedIn detail page is missing one of: job_url, title, company.")

    external_job_id_match = JOB_ID_RE.search(job_url)
    industries_value = criteria.get("industries")
    industries = (
        [part.strip() for part in industries_value.split(" and ")]
        if industries_value
        else []
    )

    return LinkedInJobDetail(
        external_job_id=external_job_id_match.group("job_id") if external_job_id_match else None,
        job_url=job_url,
        title=title,
        company=company,
        location_raw=location_raw,
        description_text=description_text,
        employment_type=criteria.get("employment type"),
        seniority=criteria.get("seniority level"),
        job_function=criteria.get("job function"),
        industries=industries,
        posted_text=posted_text,
        posted_at=parse_iso_datetime(posted_datetime),
        source_search_name=source_search_name,
        raw_payload={"detail_html": html},
    )
