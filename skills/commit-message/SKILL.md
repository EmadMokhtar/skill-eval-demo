---
name: commit-message
description: Write a Conventional Commits subject line for staged changes. Use when the user is committing, asks for a commit message, or wants an existing message rewritten to the convention.
---

# Commit message

Write the subject line for a commit, in [Conventional Commits](https://www.conventionalcommits.org/)
form. Release tooling derives versions from this history, so a message off the convention is a
broken release, not an untidy log.

## Read the change first

Run the diff for the staged changes before writing anything. A message written from the
user's description rather than the diff describes what they meant to do, which is not
always what they did.

## The form

```
<type>[optional scope][!]: <description>
```

- **Type** is one of `feat`, `fix`, `docs`, `refactor`, `test`, `perf`, `build`, `ci`,
  `chore`, `style`, `revert`.
- **Description** is imperative, lowercase, and ends without a full stop — `add retry on
  timeout`, not `Added retry on timeout.`
- **Breaking changes** carry `!` after the type or scope: `feat(api)!: return 404 for
  archived orders`. Add a `BREAKING CHANGE:` footer describing the migration.
- Keep the subject under 72 characters. Detail belongs in the body, which explains *why* —
  the diff already shows what.

## Pick the type from the change, not the intent

The type describes what the commit does to the codebase:

- A new capability a user can reach is `feat`, even if it took one line.
- A change to behaviour that was already meant to work is `fix`.
- Moving code without changing behaviour is `refactor`, even when it touches many files.
- A change only to tests is `test`; a change only to CI config is `ci`.

When a change spans types, name the one that carries the user-visible outcome and describe
the rest in the body. A commit that genuinely does two unrelated things wants to be two
commits — say so.

## Never write a bare summary

`Update auth`, `Fix bug`, `WIP`, `Address review comments` — each names a file or a mood
rather than a change. Given one, rewrite it: read the diff, then state what changed.
