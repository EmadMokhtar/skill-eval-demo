"""Run the demo eval suites against recorded traffic.

This is the same work `skill-eval run ./skills` does, driven in-process so it
can sit behind a cassette. Every push gets the real suites -- real runner, real
judge, real tool-calling trajectories -- at no cost and with no key.

What this does and does not prove: a green run here means the suites still pass
against the *recorded* model behaviour. It cannot notice that a new model
version answers differently. That is what demo.yml is for, on a schedule
against the live provider. Cassettes catch regressions in the skills, the eval
files, and skill-eval itself; the scheduled run catches the provider moving.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from skill_eval.config import load_config
from skill_eval.judges.pydantic_ai import PydanticAIJudge
from skill_eval.orchestrator import run_evals
from skill_eval.runners.pydantic_ai import PydanticAIRunner
from skill_eval.skills.loader import load_skills

REPO = Path(__file__).resolve().parent.parent
SKILLS_DIR = REPO / "skills"
CONFIG = load_config(REPO / "skill-eval.toml")


def run_suite(skill_name: str):
    """Score one skill's suite exactly as the CLI would, but in-process.

    Reads model and temperature from skill-eval.toml rather than repeating them,
    so the replayed run and the scheduled live run can never drift apart.

    Two deliberate departures from the config:

    `retries=0` -- a request that stops matching its cassette is not served from
    disk, so vcr lets it through and `--block-network` stops it at the socket.
    That surfaces as `ModelAPIError: Connection error`, which is confusing
    enough without three of them arriving a backoff apart; `_errored_detail`
    reads that signature and says "stale cassette" rather than leaving it
    looking like the provider was unreachable. Nothing reaches the network
    either way -- verified by emptying a cassette and watching it fail.

    `concurrency=1` -- the run must be sequential so one cassette per test
    holds a deterministic set of interactions.
    """
    skills = [s for s in load_skills(SKILLS_DIR) if s.name == skill_name]
    assert skills, f"no skill named {skill_name!r} under {SKILLS_DIR}"

    runner = PydanticAIRunner(
        model=CONFIG.model,
        temperature=CONFIG.temperature,
        retries=0,
    )
    judge = PydanticAIJudge(
        model=CONFIG.judge_model or CONFIG.model,
        temperature=CONFIG.judge_temperature,
        retries=0,
    )
    return run_evals(skills, [runner], judge=judge, concurrency=1)


def _errored_detail(errored) -> str:
    """Explain *why* cases errored, and say which layer to go and look at.

    Listing the case names alone is useless here: when the runner cannot reach
    the provider at all, every case in the suite errors and the list is just
    the suite back again. The error text is the diagnostic, and it lives on
    `outcome.result.error` -- runners never raise for provider failures, they
    report them there.

    Errors are grouped because they are almost always all the same one. A bad
    key produces fourteen identical 401s, and fourteen copies of it buries the
    single fact worth reading.
    """
    grouped: dict[str, list[str]] = {}
    for outcome in errored:
        # An evaluator can error too -- a judge endpoint returning 500 -- in
        # which case the runner is fine and RunResult.error is empty. Fall back
        # to the failing evaluator's own detail so that case is not reported as
        # a runner problem it isn't.
        reason = getattr(outcome.result, "error", None) or next(
            (s.detail for s in outcome.scores if s.detail and not s.passed),
            "no error recorded",
        )
        grouped.setdefault(reason, []).append(outcome.case_name)

    lines = [f"{len(errored)} case(s) errored -- the runner or judge broke, not the skill."]
    for reason, names in grouped.items():
        lines.append(f"\n  {len(names)} case(s): {reason}")
        lines.append(f"    e.g. {names[0]}")

    joined = " ".join(grouped)
    if "401" in joined or "invalid_api_key" in joined:
        lines.append(
            "\n  A 401 means the key, not the suite. Recording needs a real "
            "OPENAI_API_KEY exported in *this* shell:\n"
            "    export OPENAI_API_KEY=<your-key>"
        )
    elif "404" in joined or "model_not_found" in joined:
        lines.append(
            f"\n  A 404 usually means this key has no access to {CONFIG.model!r}. "
            "Change `model` and `judge_model` in skill-eval.toml to one it can reach."
        )
    elif "Connection error" in joined or "Cannot overwrite" in joined:
        lines.append(
            "\n  In replay mode this is a stale cassette, not a network problem: the "
            "request stopped matching what was recorded, vcr let it through to the "
            "network, and --block-network stopped it there. Nothing reached the "
            "provider. If the change that caused it is intended -- an edited task, a "
            "new case, a changed model -- record again:\n"
            "    uv run pytest --record-mode=once"
        )
    else:
        lines.append(
            "\n  Not a known signature. The full error is above; if it mentions the "
            "cassette, re-record with `uv run pytest --record-mode=once`."
        )
    return "\n".join(lines)


def assert_suite_is_green(report, expected_cases: int):
    """Assert the whole suite passed, distinguishing the ways it can fail.

    `errored` is checked before `pass_rate` and reported separately, because the
    two mean different things: a failed case is a signal about the skill, an
    errored one means the harness broke -- here, almost always a cassette that
    no longer matches. Collapsing them into one pass-rate assertion would hide
    that distinction behind a number.

    The case count is asserted too. A suite that silently stopped being
    discovered would otherwise sail through every other check on an empty run.
    """
    errored = [o for o in report.candidate_outcomes if o.status == "errored"]
    assert not errored, _errored_detail(errored)

    failed = [o.case_name for o in report.candidate_outcomes if o.status == "failed"]
    assert not failed, f"cases failed: {failed}"

    assert report.total == expected_cases, (
        f"expected {expected_cases} cases, scored {report.total} -- "
        "a suite stopped being discovered, or cases were added without updating this test"
    )


@pytest.mark.cassette
@pytest.mark.vcr
@pytest.mark.usefixtures("replay")
def test_commit_message_suite_is_green():
    assert_suite_is_green(run_suite("commit-message"), expected_cases=7)


@pytest.mark.cassette
@pytest.mark.vcr
@pytest.mark.usefixtures("replay")
def test_incident_triage_suite_is_green():
    assert_suite_is_green(run_suite("incident-triage"), expected_cases=7)
