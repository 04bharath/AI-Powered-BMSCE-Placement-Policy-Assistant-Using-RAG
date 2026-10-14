"""Optional, server-side web search for non-policy questions."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx


class WebSearchError(RuntimeError):
    """The configured web-search provider could not return results."""


@dataclass(frozen=True)
class WebSearchResult:
    title: str
    content: str
    url: str


class WebSearch(Protocol):
    def search(self, query: str) -> list[WebSearchResult]: ...


class TavilyWebSearch:
    """Small adapter for Tavily's web search API.

    The key is sent only to Tavily from the backend and is never returned to a
    browser, logged, or included in an exception message.
    """

    _URL = "https://api.tavily.com/search"

    def __init__(self, api_key: str, max_results: int = 4, timeout: float = 15.0) -> None:
        self._api_key = api_key
        self._max_results = max(1, min(max_results, 10))
        self._timeout = timeout

    def search(self, query: str) -> list[WebSearchResult]:
        payload = {
            "api_key": self._api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": self._max_results,
            "include_answer": False,
        }
        try:
            response = httpx.post(self._URL, json=payload, timeout=self._timeout)
        except httpx.HTTPError as exc:
            raise WebSearchError(f"Could not reach the web-search service: {type(exc).__name__}") from exc

        if response.status_code in (401, 403):
            raise WebSearchError("The web-search API rejected TAVILY_API_KEY.")
        if response.status_code == 429:
            raise WebSearchError("The web-search rate limit was reached. Try again shortly.")
        if response.status_code != 200:
            raise WebSearchError(f"The web-search service returned HTTP {response.status_code}.")

        try:
            raw_results = response.json().get("results", [])
        except (AttributeError, ValueError) as exc:
            raise WebSearchError("The web-search service returned an invalid response.") from exc
        if not isinstance(raw_results, list):
            raise WebSearchError("The web-search service returned an invalid response.")

        results: list[WebSearchResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            content = str(item.get("content", "")).strip()
            if not content:
                continue
            results.append(
                WebSearchResult(
                    title=str(item.get("title", "Web result")).strip() or "Web result",
                    content=content[:4000],
                    url=str(item.get("url", "")).strip(),
                )
            )
        return results


__all__ = ["TavilyWebSearch", "WebSearch", "WebSearchError", "WebSearchResult"]
