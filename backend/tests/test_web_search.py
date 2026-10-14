import httpx
import pytest

from src.web_search import TavilyWebSearch, WebSearchError


class Resp:
    def __init__(self, status=200, body=None):
        self.status_code = status
        self._body = body if body is not None else {}

    def json(self):
        if isinstance(self._body, Exception):
            raise self._body
        return self._body


def test_tavily_search_returns_compact_results(monkeypatch):
    seen = {}

    def fake_post(url, json, timeout):
        seen.update(url=url, json=json, timeout=timeout)
        return Resp(200, {"results": [{"title": "BMSCE", "content": "Placement information", "url": "https://bmsce.ac.in"}]})

    monkeypatch.setattr(httpx, "post", fake_post)
    out = TavilyWebSearch("tvly_test", max_results=99, timeout=8).search("BMSCE placement head")

    assert seen["url"] == "https://api.tavily.com/search"
    assert seen["json"]["max_results"] == 10
    assert out[0].title == "BMSCE"
    assert out[0].content == "Placement information"


def test_tavily_errors_do_not_leak_the_api_key(monkeypatch):
    key = "tvly_super_secret"
    monkeypatch.setattr(httpx, "post", lambda *args, **kwargs: Resp(401))

    with pytest.raises(WebSearchError) as exc:
        TavilyWebSearch(key).search("test")

    assert key not in str(exc.value)
