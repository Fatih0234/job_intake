"""Live LinkedIn public search page fetching helpers."""

from __future__ import annotations

from dataclasses import dataclass
from logging import Logger

import httpx
from tenacity import (
    RetryCallState,
    Retrying,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

from job_intake.logging import get_logger

DEFAULT_LINKEDIN_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/136.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}
DEFAULT_LINKEDIN_TIMEOUT_SECONDS = 20.0
DETAIL_FETCH_MAX_ATTEMPTS = 3
DETAIL_FETCH_MAX_WAIT_SECONDS = 8.0


class LinkedInFetchError(RuntimeError):
    """Raised when a public LinkedIn page request fails."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


@dataclass(frozen=True, slots=True)
class LinkedInFetchedPage:
    requested_url: str
    final_url: str
    status_code: int
    html: str


def _is_retryable_fetch_error(exception: BaseException) -> bool:
    return isinstance(exception, LinkedInFetchError) and exception.retryable


def _log_detail_retry(retry_state: RetryCallState) -> None:
    if retry_state.outcome is None or not retry_state.outcome.failed:
        return
    exception = retry_state.outcome.exception()
    if exception is None:
        return
    next_action = retry_state.next_action
    sleep_seconds = next_action.sleep if next_action is not None else 0.0
    logger: Logger = get_logger(__name__)
    logger.warning(
        "Retrying LinkedIn detail fetch after attempt %s due to %s; sleeping %.2fs",
        retry_state.attempt_number,
        exception,
        sleep_seconds,
    )


def _build_detail_retrying() -> Retrying:
    return Retrying(
        stop=stop_after_attempt(DETAIL_FETCH_MAX_ATTEMPTS),
        wait=wait_exponential_jitter(initial=1, max=DETAIL_FETCH_MAX_WAIT_SECONDS),
        retry=retry_if_exception(_is_retryable_fetch_error),
        before_sleep=_log_detail_retry,
        reraise=True,
    )


def _fetch_public_page(
    url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_LINKEDIN_TIMEOUT_SECONDS,
) -> LinkedInFetchedPage:
    def _fetch(active_client: httpx.Client) -> LinkedInFetchedPage:
        try:
            response = active_client.get(url)
        except httpx.HTTPError as exc:
            raise LinkedInFetchError(
                f"LinkedIn public request failed for {url}: {exc}",
                retryable=True,
            ) from exc

        if response.status_code != httpx.codes.OK:
            retryable = response.status_code in {
                httpx.codes.TOO_MANY_REQUESTS,
                httpx.codes.BAD_GATEWAY,
                httpx.codes.SERVICE_UNAVAILABLE,
                httpx.codes.GATEWAY_TIMEOUT,
            }
            raise LinkedInFetchError(
                "LinkedIn public request returned "
                f"{response.status_code} for {url}.",
                status_code=response.status_code,
                retryable=retryable,
            )

        html = response.text.strip()
        if not html:
            raise LinkedInFetchError(
                f"LinkedIn public request returned an empty response for {url}.",
            )

        return LinkedInFetchedPage(
            requested_url=url,
            final_url=str(response.url),
            status_code=response.status_code,
            html=html,
        )

    if client is not None:
        return _fetch(client)

    with httpx.Client(
        follow_redirects=True,
        headers=DEFAULT_LINKEDIN_HEADERS,
        timeout=timeout,
    ) as managed_client:
        return _fetch(managed_client)


def fetch_search_results_page(
    search_url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_LINKEDIN_TIMEOUT_SECONDS,
) -> LinkedInFetchedPage:
    return _fetch_public_page(search_url, client=client, timeout=timeout)


def fetch_job_detail_page(
    job_url: str,
    *,
    client: httpx.Client | None = None,
    timeout: float = DEFAULT_LINKEDIN_TIMEOUT_SECONDS,
) -> LinkedInFetchedPage:
    retrying = _build_detail_retrying()
    return retrying(_fetch_public_page, job_url, client=client, timeout=timeout)
