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

    `retries=0` -- a request that stops matching its cassette raises
    `CannotOverwriteExistingCassetteException`. With retries on, that surfaces
    as a misleading `ModelAPIError: Connection error` after two backoff sleeps.
    No network is involved either way; this just keeps the real cause visible.

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
    errored = [o.case_name for o in report.candidate_outcomes if o.status == "errored"]
    assert not errored, f"cases errored (suspect a stale cassette): {errored}"

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
