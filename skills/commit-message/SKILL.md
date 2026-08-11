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
- Keep the subject under 72 characters. Detail belongs in the body, which explains *why* —
  the diff already shows what.

## Ask whether it breaks a caller

Before settling the subject, answer one question about the diff: **would existing code
calling this still work?** A changed status code, a renamed or removed export, a new
required argument, a changed default, a narrowed return type — each breaks a caller.

When the answer is no, the message carries both marks:

```
fix(api)!: return 404 for archived orders

BREAKING CHANGE: GET /orders/:id returned 200 with {archived: true} for archived
orders and now returns 404. Callers relying on the archived flag should treat 404
as archived.
```

The `!` goes after the type or scope; the `BREAKING CHANGE:` footer describes the
migration. Both, every time — the `!` is what tooling reads, the footer is what the person
hitting the break reads. This is independent of the type: a `fix` can break a caller just
as a `feat` can.

## Pick the type from the change, not the intent

The type describes what the commit does to the codebase:

- A new capability a user can reach is `feat`, even if it took one line.
- A change to behaviour that was already meant to work is `fix`.
- Moving code without changing behaviour is `refactor`, even when it touches many files.
- A change only to tests is `test`; a change only to CI config is `ci`.

When a change spans types, name the one that carries the user-visible outcome and describe
the rest in the body.

## Account for every hunk

The message covers the whole diff. Before writing it, walk the hunks and check each one is
described by the subject or the body — a hunk nobody mentioned is a change that lands
unrecorded, and the log stops being the thing you can read history from.

When a hunk cannot be folded in because it is unrelated to the rest — a cart bug fixed
alongside a CI runner bump — that diff is two commits. Say so first, propose a subject
line for each, and let the user decide. Do this even when asked for a single message: one
message that silently drops half the diff is the outcome this rule exists to prevent.

## Never write a bare summary

`Update auth`, `Fix bug`, `WIP`, `Address review comments` — each names a file or a mood
rather than a change. Given one, rewrite it: read the diff, then state what changed.
