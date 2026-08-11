#!/usr/bin/env bash
#
# Clone the pinned upstream skills and lay our eval suites in beside them.
#
# skill-eval discovers eval files next to the SKILL.md they test, and --evals
# takes a single path applied to every skill, so a multi-skill run cannot keep
# its suites out of tree. This script is that gap, and it is why no third-party
# SKILL.md is committed to this repository.
#
#   ./canary/sync.sh            # clone into canary/.work and copy suites in
#   ./canary/sync.sh --print    # print the prepared path and exit
#
# The prepared tree is disposable: it is .gitignored, and re-running rebuilds
# it from scratch so a stale copy can never be what gets scored.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
work="$here/.work"

# shellcheck disable=SC1091
source "$here/UPSTREAM"

if [[ -z "${REPO:-}" || -z "${SHA:-}" ]]; then
  echo "canary/UPSTREAM must define REPO and SHA" >&2
  exit 2
fi

# Rebuild from scratch. A partial tree left by an interrupted run would score
# whichever suites happened to land, and report it as a complete run.
rm -rf "$work"
mkdir -p "$work"

git init --quiet "$work"
git -C "$work" remote add origin "$REPO"
# Fetch exactly the pinned commit rather than a branch: a moving ref would make
# a canary result describe an upstream revision nobody recorded.
git -C "$work" fetch --quiet --depth 1 origin "$SHA"
git -C "$work" checkout --quiet FETCH_HEAD

copied=0
while IFS= read -r suite; do
  rel="${suite#"$here/evals/"}"          # engineering/tdd/tdd.eval.yaml
  skill_dir="$work/skills/$(dirname "$rel")"
  if [[ ! -f "$skill_dir/SKILL.md" ]]; then
    echo "no SKILL.md at skills/$(dirname "$rel") -- upstream moved or renamed it" >&2
    echo "the suite at canary/evals/$rel now has nothing to test" >&2
    exit 1
  fi
  mkdir -p "$skill_dir/evals"
  cp "$suite" "$skill_dir/evals/"
  copied=$((copied + 1))
done < <(find "$here/evals" -name '*.eval.yaml' | sort)

if [[ "$copied" -eq 0 ]]; then
  echo "no eval suites found under canary/evals -- nothing would be scored" >&2
  exit 1
fi

if [[ "${1:-}" == "--print" ]]; then
  echo "$work"
  exit 0
fi

echo "prepared $copied suite(s) against $REPO @ ${SHA:0:7} in $work" >&2
echo "$work"
