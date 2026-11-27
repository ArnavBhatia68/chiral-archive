"""A small, polite MediaWiki API client.

Requests go out one at a time with a minimum gap between them. Transient failures
(HTTP 429 and 5xx, `maxlag`, dropped connections) are retried with backoff, using
the server's Retry-After header when it sends one.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

import httpx

RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})


class MediaWikiError(RuntimeError):
    """The API answered, but with an error instead of data."""


class MediaWikiClient:
    def __init__(
        self,
        api_url: str,
        user_agent: str,
        *,
        min_interval: float = 1.0,
        max_retries: int = 5,
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.api_url = api_url
        self.min_interval = min_interval
        self.max_retries = max_retries
        self._sleep = sleep
        self._clock = clock
        self._last_request: float | None = None
        self._http = httpx.Client(
            headers={"User-Agent": user_agent},
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )

    def __enter__(self) -> MediaWikiClient:
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._http.close()

    def get(self, **params: Any) -> dict[str, Any]:
        """Make one API call and return the decoded JSON."""
        params = {"format": "json", "formatversion": 2, "maxlag": 5, **params}
        attempt = 0
        while True:
            self._wait_for_turn()
            try:
                response = self._http.get(self.api_url, params=params)
            except httpx.TransportError:
                if attempt >= self.max_retries:
                    raise
                self._sleep(self._backoff(attempt))
                attempt += 1
                continue

            data = _json(response) if response.status_code == 200 else None
            lagged = data is not None and data.get("error", {}).get("code") == "maxlag"
            if (response.status_code in RETRY_STATUSES or lagged) and attempt < self.max_retries:
                self._sleep(_retry_after(response) or self._backoff(attempt))
                attempt += 1
                continue

            response.raise_for_status()
            assert data is not None  # a 200 always parses, or _json raised
            if "error" in data:
                error = data["error"]
                raise MediaWikiError(f"{error.get('code')}: {error.get('info')}")
            return data

    def query_all(self, **params: Any) -> Iterator[dict[str, Any]]:
        """Run an action=query request, following `continue` until the results run out."""
        continuation: dict[str, Any] = {}
        while True:
            data = self.get(action="query", **{**params, **continuation})
            yield data
            if "continue" not in data:
                return
            continuation = data["continue"]

    def _wait_for_turn(self) -> None:
        if self._last_request is not None:
            wait = self._last_request + self.min_interval - self._clock()
            if wait > 0:
                self._sleep(wait)
        self._last_request = self._clock()

    @staticmethod
    def _backoff(attempt: int) -> float:
        return min(60.0, 2.0 * 2**attempt)


def _json(response: httpx.Response) -> dict[str, Any]:
    try:
        return response.json()
    except ValueError as exc:
        snippet = response.text[:120].replace("\n", " ")
        raise MediaWikiError(f"expected JSON, got: {snippet!r}") from exc


def _retry_after(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After", "")
    return float(value) if value.isdigit() else None
