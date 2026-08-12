# skill-eval demo

A worked example of [skill-eval](https://github.com/EmadMokhtar/skill-evaluator), and the
place it gets dogfooded against skills that were never written with it in mind.

The repository has two arms, because a demo and a canary want opposite things. A demo
should be stable, cheap and green; a canary should be real, and is therefore noisy. Trying
to be both in one job produces a build nobody trusts.

| | `skills/` | `canary/` |
| --- | --- | --- |
| Subject | Skills this repo owns | [mattpocock/skills](https://github.com/mattpocock/skills), pinned |
| Live run | Weekly, and on demand | Weekly, and on demand |
| Gates the build | Yes, at 100% | Never |
| Samples per case | 1 | 5 (`repeat`) |

**Every push runs the demo suites for free**, off recorded provider traffic. `validate.yml`
parses every case with `skill-eval list`, then replays both suites through the real runner
and judge from cassettes in `tests/cassettes/` — real trajectories, real rubric verdicts,
no provider, no secret, no cost.

The live runs still matter, which is why they stay on a schedule. A cassette catches
regressions in the skills, the eval files and skill-eval itself; only a live run catches
the provider changing its behaviour underneath us. Paying tokens on every push to
re-learn what a recording already knows buys nothing.

Re-record when a live run goes red and the change is legitimate:

```bash
export OPENAI_API_KEY=...
uv run pytest --record-mode=once
```

Recording is the deliberate, key-bearing act. Replay is the default, so a contributor
without a key gets skips rather than surprise spend, and a cassette that stops matching
its request fails loudly rather than quietly going back to the provider. Credentials are
scrubbed from both sides of the exchange before anything reaches disk — see
[`tests/conftest.py`](tests/conftest.py), which is the difference between a shared fixture
and a leak.

## The demo skills

Two skills, chosen so that between them they exercise every kind of check skill-eval
offers.

**[`commit-message`](skills/commit-message/SKILL.md)** — the mechanical end. The skill
commits to a grammar, so its suite is mostly `regex` and `contains`: a Conventional
Commits subject, a `!` on a breaking change, a subject under 72 characters. One trajectory
case proves it read the diff before writing, which is the failure that looks identical to
success in the output. Two judged cases cover what a pattern cannot — rewriting a bare
summary, and spotting that one diff wants to be two commits.

**[`incident-triage`](skills/incident-triage/SKILL.md)** — the trajectory end. Two of its
three decisions are things you *do*, not things you say: paging on-call and posting to a
status page are tool calls, so `forbidden` and `order` carry the suite. It has both sides
of all three policy lines, including an internal SEV1 that must page and must *not* reach
the status page — the case that catches an agent treating "severe" as "tell everyone".

## The canary

`canary/evals/` holds eval suites for nine of Matt Pocock's skills. **No third-party
`SKILL.md` is committed here.** skill-eval discovers eval files beside the skill they
test, and `--evals` takes one path applied to every skill, so a multi-skill run can't keep
its suites out of tree. [`canary/sync.sh`](canary/sync.sh) is that gap: it clones the
commit pinned in [`canary/UPSTREAM`](canary/UPSTREAM) and copies our suites in beside each
skill. Bumping that SHA is a deliberate pull request, so the diff is the record of which
upstream revision a given result describes.

**Read the repeat rates, not the headline.** Two identical runs of this exact set, with
nothing changed between them, scored 80% and 83% — with a *different* set of failures each
time. Only one red reproduced with the same cause across both. A single sample here is
noise wearing a number, which is why this arm runs at `repeat = 5` and never gates.

The one finding that did reproduce: `code-review` closes with a single cross-axis "most
important problem" when asked for one, which the skill explicitly forbids. The suites also
caught `code-review` spawning both of its parallel sub-agents on an empty diff — the exact
waste its own instructions exist to prevent — behind an output the judge scored 3/3. That
one is invisible without a trajectory check.

## Running it locally

Everything runs through [uv](https://docs.astral.sh/uv/). One sync installs skill-eval
and the test harness — no virtualenv to activate, no global installs.

```bash
uv sync
```

skill-eval comes from git rather than PyPI, where it is not published, with the
`[pydantic-ai]` extra that supplies the real runner and judge; without it the only runner
available is the fake one, which reports every `mode: offered` and every judged case as
errored. Both are pinned in [`pyproject.toml`](pyproject.toml).

**Free and offline** — no key needed, and what CI runs on every push:

```bash
uv run pytest -rs
```

```bash
uv run skill-eval list ./skills
```

**Against the live provider** — costs about a cent per run:

```bash
export OPENAI_API_KEY=...
```

```bash
uv run skill-eval run ./skills --config skill-eval.toml --markdown-output report.md
```

The canary, against the pinned upstream:

```bash
uv run skill-eval run "$(./canary/sync.sh)/skills" --config canary/skill-eval.toml --markdown-output report.md
```

## Notes

Both configs pin `openai:gpt-5.6-luna` with `temperature = "unset"`. It is a reasoning
model and rejects an explicit temperature — sending `0.0` doesn't fail, it warns and
ignores, which leaves the run sampling at the provider default while the config claims
determinism. Swap the model in the two `skill-eval.toml` files to run this anywhere else.

Upstream skills are MIT, Copyright (c) 2026 Matt Pocock. The eval suites in `canary/` are
this repository's own work and are not endorsed by their author; they are written to
exercise skill-eval, not to rank anybody's skills.
