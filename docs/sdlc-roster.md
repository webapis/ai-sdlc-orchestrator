---
name: sdlc-roster
description: The full SDLC roster of human positions this project simulates as autonomous AI roles, and where each stands today
sources: [chat]
---

# SDLC Roster

**Related:** [`vision.md`](vision.md) · [`architecture.md`](architecture.md) · [`operations.md`](operations.md) · [`/roles`](../roles/)

A traditional software project is staffed by a roster of distinct positions, each covering a phase of the lifecycle. This document lists that full roster, and states plainly which positions this project currently simulates as an autonomous AI role (with a real file in [`/roles`](../roles/)), which stay human-only by design, and which are recognized gaps not yet built.

---

## 1. Discovery & Planning

| Position | What they do | Simulated by |
|---|---|---|
| Product Owner / PM | Defines what and why, prioritizes | **Human** — planning intent is deliberately not delegated |
| Business Analyst | Translates business need into requirements | **Human** |
| Architect | Decides how, at a system level, before code starts | Partially — [`planner`](../roles/planner.yaml) covers ticket-to-plan, not system-level architecture |

## 2. Design

| Position | What they do | Simulated by |
|---|---|---|
| Tech Lead | Breaks architecture into actionable technical plans | Partially — [`planner`](../roles/planner.yaml) |
| UX/UI Designer | Interface and interaction design | **Not simulated** — likely out of scope unless the target project is UI-heavy |

## 3. Development

| Position | What they do | Simulated by |
|---|---|---|
| Developer | Writes the code | [`coder`](../roles/coder.yaml) |
| Pair reviewer / buddy | Informal review during development | **Not simulated** — the formal `reviewer` role covers this need instead |

## 4. Quality & Review

| Position | What they do | Simulated by |
|---|---|---|
| Code Reviewer | Formal review before merge | [`reviewer`](../roles/reviewer.yaml) |
| QA / Test Engineer | Writes and runs tests, diagnoses failures | [`tester`](../roles/tester.yaml) |
| Security Engineer | Reviews for vulnerabilities | [`security-reviewer`](../roles/security-reviewer.yaml) |

## 5. Release

| Position | What they do | Simulated by |
|---|---|---|
| Release Manager | Decides what ships when, coordinates the release | Partially — [`deployer`](../roles/deployer.yaml) summarizes risk; timing decisions stay human |
| DevOps / Platform Engineer | Owns CI/CD pipelines, infrastructure-as-code | **Not simulated** — pipeline/infra definition stays human-authored |
| Approver | Accountable human sign-off before production | **Human** — the `human_approval` node by design, never delegated |

## 6. Operations

| Position | What they do | Simulated by |
|---|---|---|
| SRE / Ops Engineer | Monitors production, handles incidents | [`monitor`](../roles/monitor.yaml) — assesses health, cannot act, only recommends escalation |
| Support Engineer | Triages user-reported issues, feeds back into planning | **Not simulated** |

## 7. Cross-cutting, throughout

| Position | What they do | Simulated by |
|---|---|---|
| Technical Writer | Documentation | **Not simulated** — a real gap given this project's own manual-first stance elsewhere |
| Compliance / Governance | Audit trail, regulatory sign-off | Partially — `run_events` provides the audit trail; sign-off itself stays human |

---

## 2. Design principle behind what stays human

Three positions are **deliberately never delegated**, independent of AI capability:

- **Product Owner / PM / Business Analyst** — intent-setting. What the system should do is a human decision, not something to be inferred.
- **Approver** — the `human_approval` gate exists specifically so nothing ships unreviewed, per the project's core "nothing ships without a human looking at it" principle.
- **DevOps / infra ownership** — pipeline and infrastructure definitions are treated as configuration the system operates *within*, not something it rewrites on its own.

Everything else on this roster is a candidate for simulation — some already built, some open gaps.

---

## 3. Open gaps, in rough priority order

1. **Technical Writer** — directly relevant given this project's own documentation-first practice; currently has no role file
2. **Architect** (system-level, distinct from `planner`'s ticket-level scope) — currently underserved
3. **Support Engineer** — no mechanism to turn user-reported issues into planning input
4. **DevOps / Platform Engineer** as an agent (vs. human-owned infra) — an open question, not necessarily a gap to close; see the design principle above

None of these are scheduled into a phase in `implementation-plan.md` yet.

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-10 | Initial SDLC roster — full lifecycle position list mapped to current roles |
