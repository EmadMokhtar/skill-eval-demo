---
name: incident-triage
description: Triage a production incident — set its severity, decide whether to page on-call, and decide whether to post a status-page update. Use when the user reports an outage, a degradation, or an alert that needs a call on how far to escalate.
---

# Incident triage

Decide three things about an incident, in this order: its **severity**, whether to **page
on-call**, and whether to **post a status-page update**. Each decision has a rule, and the
rules are not interchangeable — a customer-facing SEV3 still does not page.

## Look it up first

Fetch the incident before deciding anything. Severity follows from the blast radius and
the error rate recorded on the incident, not from how the reporter phrased it — "the site
is down" from one person is frequently one degraded region.

Never set a severity, page, or post from the description alone.

## Severity

| Severity | Condition |
| --- | --- |
| SEV1 | Complete loss of a core capability, or data loss or corruption of any size. |
| SEV2 | A core capability degraded for a large share of users, or fully broken for a small one. |
| SEV3 | Reduced quality with a workaround, or a non-core capability broken. |
| SEV4 | Cosmetic, internal-only, or already mitigated. |

State the severity and the evidence you set it from. A severity asserted without the
number it came from is unreviewable.

## Paging

**Page on-call for SEV1 and SEV2. Nothing else pages.** A SEV3 or SEV4 goes to the team
channel and waits for working hours — paging on those is how a rotation stops trusting
pages at all.

Escalating "just in case" is the failure mode this rule exists to stop. When the severity
is genuinely uncertain between SEV2 and SEV3, gather the missing evidence first; if it
cannot be gathered, treat it as the higher severity and say that is what you did.

## Status page

**Post only when the incident is customer-facing.** An internal-only incident — a broken
build pipeline, a staging outage, an internal dashboard — never goes to the status page,
whatever its severity: a SEV1 on internal tooling is still invisible to customers, and
posting it invents an outage they did not have.

Say plainly which of the three decisions you made and why.
