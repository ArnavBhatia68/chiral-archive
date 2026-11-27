import httpx
import pytest

from chiral.ingest.mediawiki import MediaWikiClient, MediaWikiError


class FakeTime:
    """Stands in for time.monotonic and time.sleep, so the tests never actually wait."""

    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make_client(handler, fake_time, **options):
    return MediaWikiClient(
        "https://wiki.example/api.php",
        "test-agent/1.0",
        transport=httpx.MockTransport(handler),
        sleep=fake_time.sleep,
        clock=fake_time.clock,
        **options,
    )


def test_sends_the_user_agent_and_json_defaults():
    seen = {}

    def handler(request):
        seen["agent"] = request.headers["User-Agent"]
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json={"query": {}})

    make_client(handler, FakeTime()).get(action="query", meta="siteinfo")

    assert seen["agent"] == "test-agent/1.0"
    assert seen["params"] == {
        "format": "json",
        "formatversion": "2",
        "maxlag": "5",
        "action": "query",
        "meta": "siteinfo",
    }


def test_waits_between_requests():
    fake_time = FakeTime()
    client = make_client(lambda r: httpx.Response(200, json={}), fake_time, min_interval=1.5)

    client.get(action="query")
    client.get(action="query")

    assert fake_time.sleeps == [1.5]


def test_retries_429_after_the_retry_after_delay():
    fake_time = FakeTime()
    responses = iter(
        [httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={"ok": 1})]
    )
    client = make_client(lambda r: next(responses), fake_time, min_interval=0)

    assert client.get(action="query") == {"ok": 1}
    assert fake_time.sleeps == [7.0]


def test_retries_maxlag_errors():
    fake_time = FakeTime()
    lagged = {"error": {"code": "maxlag", "info": "Waiting for a database server"}}
    responses = iter(
        [
            httpx.Response(200, headers={"Retry-After": "5"}, json=lagged),
            httpx.Response(200, json={"ok": 1}),
        ]
    )
    client = make_client(lambda r: next(responses), fake_time, min_interval=0)

    assert client.get(action="query") == {"ok": 1}
    assert fake_time.sleeps == [5.0]


def test_gives_up_after_max_retries_with_exponential_backoff():
    fake_time = FakeTime()
    client = make_client(lambda r: httpx.Response(503), fake_time, min_interval=0, max_retries=2)

    with pytest.raises(httpx.HTTPStatusError):
        client.get(action="query")
    assert fake_time.sleeps == [2.0, 4.0]


def test_api_errors_raise():
    error = {"error": {"code": "missingtitle", "info": "The page you specified doesn't exist."}}
    client = make_client(lambda r: httpx.Response(200, json=error), FakeTime())

    with pytest.raises(MediaWikiError, match="missingtitle"):
        client.get(action="parse", page="Nope")


def test_non_json_responses_raise():
    page = "<html><title>Just a moment...</title></html>"
    client = make_client(lambda r: httpx.Response(200, text=page), FakeTime())

    with pytest.raises(MediaWikiError, match="expected JSON"):
        client.get(action="query")


def test_query_all_follows_continuation():
    calls = []

    def handler(request):
        params = dict(request.url.params)
        calls.append(params)
        if "gapcontinue" not in params:
            return httpx.Response(
                200,
                json={
                    "continue": {"gapcontinue": "B", "continue": "gapcontinue||"},
                    "query": {"pages": [{"title": "A"}]},
                },
            )
        return httpx.Response(200, json={"query": {"pages": [{"title": "B"}]}})

    client = make_client(handler, FakeTime())
    titles = [
        p["title"]
        for data in client.query_all(generator="allpages")
        for p in data["query"]["pages"]
    ]

    assert titles == ["A", "B"]
    assert calls[1]["gapcontinue"] == "B"
    assert calls[1]["generator"] == "allpages"
