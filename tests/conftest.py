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

    cassette = CASSETTE_DIR / request.node.module.__name__ / f"{request.node.name}.yaml"
    if record_mode == "none" and not cassette.is_file():
        pytest.skip(
            f"cassette {cassette.name} not recorded yet -- run "
            "`uv run pytest --record-mode=once` with a real OPENAI_API_KEY exported. "
            "A missing cassette skips rather than fails: re-recording is impossible "
            "in replay mode anyway, and a red build here would say nothing about the skill."
        )
