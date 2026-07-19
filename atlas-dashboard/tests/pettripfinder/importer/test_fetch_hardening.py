"""AES-DATA-004E (Task 4/7) -- compliant fetcher hardening: headers, bounded
transient-5xx retry, per-domain pacing. Fake session/sleep injection only --
no real network, no real sleeping."""

from __future__ import annotations

from requests.structures import CaseInsensitiveDict

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.fetch import RequestsPageFetcher, _request_headers

_PUBLIC = "http://93.184.216.34"


class _FakeResp:
    def __init__(self, status, headers, chunks=(b"<html>ok</html>",)):
        self.status_code = status
        self.headers = CaseInsensitiveDict(headers)
        self._chunks = chunks

    def iter_content(self, chunk_size=16384):
        for c in self._chunks:
            yield c

    def close(self):
        pass


class _SequenceSession:
    """Returns responses in order for repeated calls to the SAME url --
    used to test the bounded transient-5xx retry."""

    def __init__(self, sequence_by_url):
        self._sequence = {k: list(v) for k, v in sequence_by_url.items()}
        self.call_count = 0
        self.calls = []

    def get(self, url, **kw):
        self.call_count += 1
        self.calls.append((url, kw))
        seq = self._sequence[url]
        return seq.pop(0) if len(seq) > 1 else seq[0]


class _RecordingSleep:
    def __init__(self):
        self.calls = []

    def __call__(self, seconds):
        self.calls.append(seconds)


# --------------------------------------------------------------------------- #
# Headers.
# --------------------------------------------------------------------------- #

def test_headers_are_ordinary_non_deceptive():
    headers = _request_headers()
    assert headers["User-Agent"] == C.USER_AGENT
    assert "AtlasImporter" in headers["User-Agent"]
    assert "Chrome" not in headers["User-Agent"]
    assert "Mozilla" not in headers["User-Agent"]
    assert headers["Accept-Language"] == C.ACCEPT_LANGUAGE_HEADER
    assert headers["Accept-Encoding"] == C.ACCEPT_ENCODING_HEADER
    assert "text/html" in headers["Accept"]


def test_fetch_sends_the_hardened_headers():
    url = _PUBLIC + "/ok"
    session = _SequenceSession({url: [_FakeResp(200, {"Content-Type": "text/html"})]})
    fetcher = RequestsPageFetcher(session=session, sleep_fn=_RecordingSleep())
    r = fetcher.fetch(url)
    assert r.ok
    sent_headers = session.calls[0][1]["headers"]
    assert sent_headers == _request_headers()


# --------------------------------------------------------------------------- #
# Bounded transient-5xx retry.
# --------------------------------------------------------------------------- #

def test_transient_502_retried_once_then_succeeds():
    url = _PUBLIC + "/flaky"
    session = _SequenceSession({url: [
        _FakeResp(502, {"Content-Type": "text/html"}),
        _FakeResp(200, {"Content-Type": "text/html"}),
    ]})
    sleep = _RecordingSleep()
    fetcher = RequestsPageFetcher(session=session, sleep_fn=sleep)
    r = fetcher.fetch(url)
    assert r.ok is True
    assert session.call_count == 2
    assert sleep.calls == [C.TRANSIENT_SERVER_ERROR_RETRY_DELAY_SECONDS]


def test_transient_503_retried_exactly_once_then_gives_up():
    url = _PUBLIC + "/downforcount"
    session = _SequenceSession({url: [_FakeResp(503, {"Content-Type": "text/html"})]})
    sleep = _RecordingSleep()
    fetcher = RequestsPageFetcher(session=session, sleep_fn=sleep)
    r = fetcher.fetch(url)
    assert r.ok is False
    assert r.reason == C.REASON_FETCH_FAILED
    # Exactly ONE retry (two attempts total) -- never unbounded.
    assert session.call_count == 1 + C.TRANSIENT_SERVER_ERROR_RETRY_COUNT


def test_ordinary_403_is_never_retried():
    url = _PUBLIC + "/blocked"
    session = _SequenceSession({url: [_FakeResp(403, {"Content-Type": "text/html"})]})
    sleep = _RecordingSleep()
    fetcher = RequestsPageFetcher(session=session, sleep_fn=sleep)
    r = fetcher.fetch(url)
    assert r.reason == C.REASON_BLOCKED_SOURCE
    assert session.call_count == 1
    assert sleep.calls == []


def test_404_is_never_retried():
    url = _PUBLIC + "/missing"
    session = _SequenceSession({url: [_FakeResp(404, {"Content-Type": "text/html"})]})
    fetcher = RequestsPageFetcher(session=session, sleep_fn=_RecordingSleep())
    r = fetcher.fetch(url)
    assert session.call_count == 1


# --------------------------------------------------------------------------- #
# Per-domain pacing.
# --------------------------------------------------------------------------- #

class _FakeClock:
    def __init__(self, start=0.0):
        self.now = start

    def __call__(self):
        return self.now


def test_second_request_to_same_domain_within_interval_sleeps():
    url1 = _PUBLIC + "/a"
    url2 = _PUBLIC + "/b"
    session = _SequenceSession({
        url1: [_FakeResp(200, {"Content-Type": "text/html"})],
        url2: [_FakeResp(200, {"Content-Type": "text/html"})],
    })
    clock = _FakeClock(start=100.0)
    sleep = _RecordingSleep()

    def sleep_and_advance(seconds):
        sleep.calls.append(seconds)
        clock.now += seconds

    fetcher = RequestsPageFetcher(
        session=session, min_domain_interval_seconds=2.0,
        sleep_fn=sleep_and_advance, time_fn=clock)
    fetcher.fetch(url1)
    clock.now += 0.5   # only half the minimum interval has elapsed
    fetcher.fetch(url2)
    assert sleep.calls == [1.5]   # topped up to exactly the 2.0s floor


def test_request_after_interval_has_elapsed_does_not_sleep():
    url1 = _PUBLIC + "/a"
    url2 = _PUBLIC + "/b"
    session = _SequenceSession({
        url1: [_FakeResp(200, {"Content-Type": "text/html"})],
        url2: [_FakeResp(200, {"Content-Type": "text/html"})],
    })
    clock = _FakeClock(start=100.0)
    sleep = _RecordingSleep()
    fetcher = RequestsPageFetcher(
        session=session, min_domain_interval_seconds=1.0,
        sleep_fn=sleep, time_fn=clock)
    fetcher.fetch(url1)
    clock.now += 5.0   # well past the minimum interval
    fetcher.fetch(url2)
    assert sleep.calls == []


def test_pacing_is_per_domain_not_global():
    url1 = "http://93.184.216.34/a"
    url2 = "http://93.184.216.85/b"   # a different public IP-literal host
    session = _SequenceSession({
        url1: [_FakeResp(200, {"Content-Type": "text/html"})],
        url2: [_FakeResp(200, {"Content-Type": "text/html"})],
    })
    clock = _FakeClock(start=100.0)
    sleep = _RecordingSleep()
    fetcher = RequestsPageFetcher(
        session=session, min_domain_interval_seconds=5.0,
        sleep_fn=sleep, time_fn=clock)
    fetcher.fetch(url1)
    fetcher.fetch(url2)   # different host -- no pacing needed
    assert sleep.calls == []


def test_pacing_disabled_with_zero_interval():
    url1 = _PUBLIC + "/a"
    url2 = _PUBLIC + "/b"
    session = _SequenceSession({
        url1: [_FakeResp(200, {"Content-Type": "text/html"})],
        url2: [_FakeResp(200, {"Content-Type": "text/html"})],
    })
    sleep = _RecordingSleep()
    fetcher = RequestsPageFetcher(session=session, min_domain_interval_seconds=0,
                                  sleep_fn=sleep, time_fn=_FakeClock(0.0))
    fetcher.fetch(url1)
    fetcher.fetch(url2)
    assert sleep.calls == []
