"""Cassette plumbing: replay recorded provider traffic, never reach the network.

The demo suites are the thing this repository is for, so they should run on
every push -- but they are model calls, and paying tokens per push to re-learn
what a recording already knows is waste. These fixtures let the same suites run
from disk: free, offline, deterministic, and no key.

Recording is the deliberate, key-bearing act. Replay is the default, so a
contributor without a key gets skips rather than surprise spend, and a cassette
that stops matching its request fails loudly rather than quietly going back to
the provider.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

CASSETTE_DIR = Path(__file__).parent / "cassettes"


def _scrub_response(response):
    """Strip account-identifying response headers before they hit disk.

    `filter_headers` only touches the *request* side in vcrpy, so response
    headers pass through untouched no matter what is listed there. Recorded
    responses carry `openai-organization`, `openai-project` and a `set-cookie`
    that are tied to whichever account did the recording. These cassettes are
    committed, so that is the difference between a shared fixture and a leak.

    `access-control-expose-headers` goes too: its value is just the *names* of
    the headers above, so leaving it would re-leak them and advertise exposure
    of headers that are no longer there.
    """
    scrub = {
        "openai-organization",
        "openai-project",
        "set-cookie",
        "x-request-id",
        "cf-ray",
        "access-control-expose-headers",
    }
    headers = response.get("headers")
    if headers:
        for key in list(headers):
            if key.lower() in scrub:
                del headers[key]
    return response


@pytest.fixture(scope="module")
def vcr_config():
    """Replay-only by default, with every credential scrubbed on record.

    Matching on the body as well as the path matters: every request goes to the
    same chat-completions endpoint, so the body is the only thing that tells
    one case -- or one turn of a tool-using conversation -- from the next.

    The scrub is split across two hooks because vcrpy wires them into opposite
    sides of the exchange: `filter_headers` for the credentials we send,
    `before_record_response` for what the provider sends back.
    """
    return {
        "filter_headers": [
            "authorization",
            "api-key",
            "x-api-key",
            "cookie",
        ],
        "before_record_response": _scrub_response,
        "match_on": ["method", "scheme", "host", "port", "path", "body"],
        "decode_compressed_response": True,
    }


def _cassette_for(item) -> Path:
    return CASSETTE_DIR / item.module.__name__ / f"{item.name}.yaml"


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """Discard a recording made by a run that failed.

    vcrpy writes the cassette whatever the responses were, so a recording
    session with a bad key or an unreachable model produces a cassette full of
    401s. That then replays forever as a permanently errored suite -- no key
    needed to reproduce it, and no obvious reason why. A recording is only
    worth keeping if the run it recorded actually passed; otherwise the missing
    cassette skips, says exactly that, and asks to be recorded again.

    This has to run on the *teardown* report rather than from a fixture
    finalizer. pytest-recording's `vcr` fixture is autouse and sets up before
    ours, so it tears down after: a finalizer here looks for a file vcr has not
    written yet, deletes nothing, and vcr then persists the bad cassette
    anyway. By the time the teardown report is made, every finalizer has run
    and the file is on disk.
    """
    report = yield
    setattr(item, f"rep_{report.when}", report)

    if report.when == "teardown" and item.config.getoption("--record-mode", "none") != "none":
        call_report = getattr(item, "rep_call", None)
        cassette = _cassette_for(item)
        if call_report is not None and call_report.failed and cassette.is_file():
            cassette.unlink()
            print(
                f"\ndiscarded {cassette.name}: the recording run failed, and a cassette "
                "of failures would replay as a permanent error. Fix the cause above, "
                "then record again."
            )

    return report


@pytest.fixture
def replay(request, monkeypatch, record_mode):
    """Set up a cassette-backed test: dummy key on replay, skip if never recorded.

    Provider clients refuse to construct without a key even when every response
    comes off disk, so replay mode sets a placeholder -- via `monkeypatch`, so
    it is undone after the test and can never overwrite a real exported key.

    Recording mode requires a real key and says so. An exported-but-blank value
    counts as missing, matching skill-eval's own preflight; a presence-only
    check would let it through and the recording would die at the provider with
    an opaque auth error instead of here.
    """
    if record_mode == "none":
        monkeypatch.setenv("OPENAI_API_KEY", "dummy-key-for-replay")
    elif not os.environ.get("OPENAI_API_KEY"):
        pytest.fail(
            "Recording (--record-mode=once) needs a real OPENAI_API_KEY exported. "
            "Run: export OPENAI_API_KEY=<your-key>"
        )

    # A failed recording is thrown away in pytest_runtest_makereport above,
    # which is the only place late enough to see the file vcr wrote.
    cassette = _cassette_for(request.node)
    if record_mode == "none" and not cassette.is_file():
        pytest.skip(
            f"cassette {cassette.name} not recorded yet -- run "
            "`uv run pytest --record-mode=once` with a real OPENAI_API_KEY exported. "
            "A missing cassette skips rather than fails: re-recording is impossible "
            "in replay mode anyway, and a red build here would say nothing about the skill."
        )
