from __future__ import annotations

import httpx
import pytest
from tenacity import Retrying, retry_if_exception, stop_after_attempt, wait_none

import job_intake.adapters.linkedin.fetch as linkedin_fetch_module
from job_intake.adapters.linkedin import (
    LinkedInFetchError,
    fetch_job_detail_page,
    fetch_search_results_page,
)


def test_fetch_search_results_page_returns_html_for_successful_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text="<html>ok</html>",
            request=request,
        ),
    )
    client = httpx.Client(transport=transport)

    result = fetch_search_results_page(
        "https://www.linkedin.com/jobs/search/?keywords=data",
        client=client,
    )

    assert result.status_code == 200
    assert result.html == "<html>ok</html>"
    assert result.requested_url == "https://www.linkedin.com/jobs/search/?keywords=data"


def test_fetch_search_results_page_raises_for_non_200_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(429, text="Too Many Requests", request=request),
    )
    client = httpx.Client(transport=transport)

    with pytest.raises(LinkedInFetchError, match="429"):
        fetch_search_results_page(
            "https://www.linkedin.com/jobs/search/?keywords=data",
            client=client,
        )


def test_fetch_job_detail_page_returns_html_for_successful_response() -> None:
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200,
            text="<html>detail</html>",
            request=request,
        ),
    )
    client = httpx.Client(transport=transport)

    result = fetch_job_detail_page(
        "https://www.linkedin.com/jobs/view/4185654374/",
        client=client,
    )

    assert result.status_code == 200
    assert result.html == "<html>detail</html>"
    assert result.requested_url == "https://www.linkedin.com/jobs/view/4185654374/"


def test_fetch_job_detail_page_retries_retryable_errors_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(429, text="Too Many Requests", request=request)
        return httpx.Response(200, text="<html>detail</html>", request=request)

    monkeypatch.setattr(
        linkedin_fetch_module,
        "_build_detail_retrying",
        lambda: Retrying(
            stop=stop_after_attempt(3),
            wait=wait_none(),
            retry=retry_if_exception(linkedin_fetch_module._is_retryable_fetch_error),
            reraise=True,
        ),
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = fetch_job_detail_page(
        "https://www.linkedin.com/jobs/view/4185654374/",
        client=client,
    )

    assert attempts["count"] == 3
    assert result.status_code == 200


def test_fetch_job_detail_page_stops_after_max_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        return httpx.Response(429, text="Too Many Requests", request=request)

    monkeypatch.setattr(
        linkedin_fetch_module,
        "_build_detail_retrying",
        lambda: Retrying(
            stop=stop_after_attempt(3),
            wait=wait_none(),
            retry=retry_if_exception(linkedin_fetch_module._is_retryable_fetch_error),
            reraise=True,
        ),
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(LinkedInFetchError, match="429"):
        fetch_job_detail_page(
            "https://www.linkedin.com/jobs/view/4185654374/",
            client=client,
        )

    assert attempts["count"] == 3
