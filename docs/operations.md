---
name: operations
description: Full inventory of operations the Orchestrator performs, grouped by where each happens
sources: [chat]
---

# Operations Reference

**Related:** [`vision.md`](vision.md) · [`architecture.md`](architecture.md) · [`implementation-plan.md`](implementation-plan.md) · [`motivations.md`](motivations.md)

A complete inventory of the operations this system performs, grouped by where each happens. Cross-referenced against `architecture.md` where a section already specifies the mechanism; flagged as **not yet designed** where it isn't.

---

## Project & workflow management (CLI/API)

- Register a project (repo URL, VCS provider)
- Validate & store VCS credentials
- Assign/change a project's default workflow
- Create the GitHub webhook for a project
- Register/version a workflow spec (YAML) — see `architecture.md` §6
- Register/version a role definition (YAML) — see `architecture.md` §7

## Triggering & controlling runs

- Trigger a run manually
- Trigger a run via webhook (push, PR, schedule)
- Get run status
- Cancel an in-progress run
- List pending approvals
- Submit an approval decision (approve/reject)
- Resume a paused run from its checkpoint

See `architecture.md` §12 for the corresponding API endpoints.

## Graph execution (engine internals)

- Compile a workflow YAML spec into an executable graph — `GraphBuilder`, §8.1
- Resolve each node to its executable (agent / function / human / subgraph) — `NodeRegistry`, §8.2
- Execute an agent node (LLM call, structured output)
- Execute a function node (deterministic logic)
- Execute a human node (interrupt + pause) — §8.3
- Evaluate a conditional edge / routing function — `RoutingRegistry`, §6.3
- Merge concurrent state updates (reducers, for parallel nodes)
- Write a checkpoint after each node
- Detect and resume from the latest checkpoint

## Per-role agent operations

- **Planner** — read the ticket/spec, produce an implementation plan
- **Coder** — read code, write/edit a diff, open a branch
- **Reviewer** — read a diff, produce structured approve/reject + feedback
- **Deployer** — summarize a merged change, assess risk level for approval

See `architecture.md` §7.2 for the full role set and `/roles/*.yaml` in the repo for current definitions.

## VCS operations (via adapter)

- Read a file from the repo
- Create a branch
- Create a pull request
- Post a status check
- Merge / trigger deploy after approval

See `architecture.md` §11.1, `VcsAdapter` protocol.

## Reliability operations

- Classify a failure (transient network, rate limit, invalid input, permission denied, policy violation, model format error, unknown)
- Retry with backoff, per category's policy
- Escalate to a human when retries are exhausted or category demands it
- Enforce idempotency on side-effecting nodes (dedupe repeated attempts)

See `architecture.md` §9, `FailureCategory` / `RETRY_POLICY`.

## Observability operations

- Emit `node_start` / `node_complete` events (with latency)
- Emit `route_selected` events (which edge fired, why)
- Emit `tool_call` events (tool, args, result summary)
- Emit `retry` / `escalation` / `human_decision` events
- Reconstruct a full run trace from `run_events`

See `architecture.md` §14.

## Multi-project / multi-tenant operations (Phase 9–10)

- Isolate state and credentials per tenant
- Run concurrent workflows across different projects without state leakage
- Acquire an advisory lock for concurrent runs touching the same branch
- Aggregate portfolio-level status across all managed projects

See `architecture.md` §10; `implementation-plan.md` Phase 9–10.

## Notification & human-facing operations

- Notify a human that approval is pending
- Present run context (diff, feedback, test results) for review
- Surface an escalation reason in plain language

---

## Not yet designed

Two operation categories are named as core motivations (`motivations.md` #1–#3) but have no corresponding mechanism in `architecture.md` yet:

- **Vendor routing operations** — selecting the best AI vendor per task category at runtime. Currently, role files hardcode a single model (e.g. `model: claude-sonnet-5` in `roles/coder.yaml`) rather than declaring a task category resolved by a vendor-agnostic router.
- **Isolated execution operations** — sandboxing a node's execution (ephemeral container per run, scoped network egress, teardown after completion). No such boundary is currently specified for the `coder` role's tool access.

Both are open design work, not yet scheduled into a phase.

---

## Changelog

| Date | Change |
|---|---|
| 2026-08-08 | Initial operations inventory |
