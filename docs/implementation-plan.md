# AI SDLC Orchestrator — Implementation Plan & Roadmap

Status: **Draft v0.1 — proposed for kickoff**
Last updated: 2026-08-07

**Related:** [`docs/vision.md`](vision.md) · [`docs/architecture.md`](architecture.md) · [`docs/use-cases.md`](use-cases.md)

---

## 1. Purpose

This document turns the developer manual's high-level roadmap (`docs/architecture.md` §19) into an actionable, sequenced implementation plan: what gets built in what order, what "done" means for each piece, and what blocks what.

**Guiding rule:** each phase must produce something that actually runs — no phase should end with only designs or stubs. If a phase can't demo a real execution by its end, it's scoped too big.

---

## 2. Scope boundaries for v1

To avoid the trap of building the whole platform before proving the core idea works, v1 deliberately narrows scope:

| In scope for v1 | Deferred past v1 |
|---|---|
| One workflow (`feature-development`) | Workflow marketplace / templates across tenants |
| GitHub only | Azure DevOps adapter |
| Single-tenant, single-project | Multi-tenant isolation, credential scoping at scale |
| Postgres-backed checkpointing | High-availability / multi-region |
| CLI + REST API | Web UI for approvals and run inspection |
| Manual role/workflow YAML authoring | AI-assisted workflow generation |

Multi-tenant, Azure DevOps, and the Web UI are real requirements — they're sequenced into Phase 4+ once the core loop is proven end-to-end on one project.

---

## 3. Phase overview

| Phase | Theme | Target duration | Exit criterion |
|---|---|---|---|
| 0 | Environment & schema | 1 week | `docker compose up` gives a working Postgres + empty engine/API skeleton |
| 1 | Engine core | 2–3 weeks | A hand-written graph runs locally end-to-end with a mocked LLM |
| 2 | First real agent nodes | 2 weeks | `planner` + `coder` + `reviewer` roles run against a real LLM on a toy repo |
| 3 | Human-in-the-loop + checkpointing | 1–2 weeks | A run pauses, survives a process restart, and resumes correctly |
| 4 | GitHub integration | 2 weeks | A run opens a real PR on a real (test) repo after approval |
| 5 | Retry & escalation | 1–2 weeks | Fault injection tests prove each failure category routes correctly |
| 6 | Backend & API | 2–3 weeks | External trigger via webhook → full run → PR, no manual engine invocation |
| 7 | Observability | 1 week | Full run trace reconstructable from `run_events` alone |
| 8 | Hardening & multi-project | 2–3 weeks | Two projects run concurrently without state leakage |
| 9 | Multi-tenant + Azure DevOps | Ongoing | Deferred — scoped only after v1 is proven |

Estimated time to a usable v1 (Phases 0–7): **~12–16 weeks** at a steady, part-time-to-moderate pace. Treat these as relative sizing, not commitments — the point is sequencing and exit criteria, not the calendar.

---

## 4. Phase details

### Phase 0 — Environment & schema
**Goal:** anyone can clone the repo and get a running (empty) system in one command.

| # | Task | Done when |
|---|---|---|
| 0.1 | `docker-compose.yml` brings up Postgres + Redis | `docker compose up -d` succeeds |
| 0.2 | Apply `src/engine/schema.sql` (or convert to Alembic migrations) | Tables exist; `\dt` in psql shows all 6 |
| 0.3 | Python engine project scaffolding + dependency install | `pip install -e .` works from `src/engine` |
| 0.4 | ASP.NET Core project scaffolding (`dotnet new webapi`) | `dotnet run` serves an empty health-check endpoint |
| 0.5 | CI: lint + unit test job runs on every PR (even with nothing to test yet) | Green check on a trivial PR |

**Blocks:** everything downstream.

---

### Phase 1 — Engine core (no real LLM yet)
**Goal:** prove `GraphBuilder` + `NodeRegistry` + `RoutingRegistry` actually work, using fake nodes.

| # | Task | Done when |
|---|---|---|
| 1.1 | Implement `_build_typed_dict` for dynamic state schemas | Unit test: YAML `state_schema` → correct `TypedDict` |
| 1.2 | Implement `GraphBuilder.build_graph` fully (nodes, edges, conditional edges) | A trivial 3-node YAML spec compiles and runs with `InMemorySaver` |
| 1.3 | Implement `NodeRegistry` function-node path | A registered plain-Python function executes as a node |
| 1.4 | Implement `NodeRegistry` human-node path (`interrupt`) | A test graph pauses at a human node and resumes via `Command(resume=...)` |
| 1.5 | Implement `RoutingRegistry` + wire `route_after_test` / `route_after_human` | Unit tests cover every branch (approve, reject, revision cap hit) |
| 1.6 | End-to-end test: run `feature-development.yaml` with **all agent nodes replaced by stub functions** | Full graph traversal completes with expected terminal state |

**Exit demo:** run the reference workflow end-to-end with zero real LLM calls — proves the skeleton is sound before spending on model calls.

---

### Phase 2 — First real agent nodes
**Goal:** replace stubs with real model calls for the three core roles.

| # | Task | Done when |
|---|---|---|
| 2.1 | Implement `_make_agent_node` — builds a model call from `role.system_prompt` + `role.output_schema` | Unit test with a mocked model response |
| 2.2 | Wire `planner` role against a real model (e.g. via `init_chat_model`) | Given a toy ticket, produces a plausible plan |
| 2.3 | Wire `coder` role — **without** Cursor Automation yet; direct file read/write on a scratch repo | Given a plan, produces a diff as text |
| 2.4 | Wire `reviewer` role with structured output (`review_approved`, `review_feedback`) | Given a diff, returns a valid structured verdict |
| 2.5 | Run the full graph on a real toy repo (e.g. a throwaway "hello world" project) | A plausible diff is produced and reviewed without human intervention |

**Exit demo:** point the graph at a tiny real repo, trigger a run, watch it plan → code → review without any human step yet (approval comes in Phase 3).

**Risk to flag early:** model output reliability (structured output parsing failures) — this phase is where `MODEL_FORMAT_ERROR` handling (Phase 5) will first be needed in practice, even before it's formally built. Note failures observed here to inform Phase 5 design.

---

### Phase 3 — Human-in-the-loop + durable checkpointing
**Goal:** a run can be interrupted, survive a restart, and resume correctly — the platform's core safety property.

| # | Task | Done when |
|---|---|---|
| 3.1 | Replace `InMemorySaver` with `PostgresSaver` (or equivalent durable checkpointer) | Checkpoint rows appear in `workflow_checkpoints` |
| 3.2 | Wire `human_approval` node to persist an `approval_requests` row on interrupt | Row appears with correct `context` payload |
| 3.3 | Build a minimal CLI command to list pending approvals and submit a decision | `orchestrator approve <run_id> --action approve` resumes the run |
| 3.4 | **Kill-and-resume test:** interrupt a run, kill the process, restart, resume from the same `thread_id` | Run completes correctly with no lost or duplicated state |

**Exit demo:** trigger a run, let it pause for approval, restart the whole engine process, then approve — it should finish correctly. This is the single most important reliability proof in the whole plan.

---

### Phase 4 — GitHub integration
**Goal:** the loop closes against a real repository.

| # | Task | Done when |
|---|---|---|
| 4.1 | Implement `GitHubAdapter.create_branch` and `.read_file` | Integration test against a real (disposable) test repo |
| 4.2 | Implement `GitHubAdapter.create_pull_request` and `.post_status` | A real PR appears on the test repo |
| 4.3 | Wire the `merge` function node to the adapter, with idempotency key `(run_id, node_name, attempt)` | Re-invoking the node does not open a duplicate PR |
| 4.4 | Swap the Phase 2 scratch-repo coder node for real GitHub-backed read/write | Diff is committed to a real branch, not just held in memory |

**Exit demo:** trigger a run against a real (test) GitHub repo end-to-end: plan → code → review → test → approve → real PR opens.

**Note:** Cursor Automation integration (manual §11.2) is explicitly deferred past this phase — v1 can ship with direct file read/write via the GitHub API; swapping in Cursor Automation as the coder's tool is an enhancement, not a blocker.

---

### Phase 5 — Retry & escalation
**Goal:** the system degrades gracefully instead of failing opaquely.

| # | Task | Done when |
|---|---|---|
| 5.1 | Implement real `classify(exc)` logic (currently a stub returning `UNKNOWN`) | Unit tests map real exception types (timeout, 429, 403, validation error) to correct categories |
| 5.2 | Wire `RETRY_POLICY` into node execution — retry/backoff loop around each node call | Fault-injection test: forced `TRANSIENT_NETWORK` retries 3x then succeeds or fails cleanly |
| 5.3 | Wire escalation path: exhausted retries → `approval_requests` row via the same interrupt mechanism as Phase 3 | Forced `PERMISSION_DENIED` creates an escalation, not a crash |
| 5.4 | Enforce idempotency requirement at `NodeRegistry.register_function` (reject non-idempotent side-effecting nodes at compile time) | Registering a side-effecting function without an idempotency key fails graph compilation |

**Exit demo:** deliberately break something mid-run (revoke a test API key) and watch the system escalate to a human with a clear, categorized reason — not a stack trace.

---

### Phase 6 — Backend & public API
**Goal:** the engine stops being something you invoke by hand.

| # | Task | Done when |
|---|---|---|
| 6.1 | Implement `POST /api/v1/projects` (register), `POST /api/v1/workflows` | A project + workflow can be registered via HTTP |
| 6.2 | Implement `POST /api/v1/projects/{id}/runs` → internal call to the engine | Triggers a real run, returns a `run_id` |
| 6.3 | Implement `GET /api/v1/runs/{id}`, `/events`, `/approval` | Run status and audit trail visible via API |
| 6.4 | Implement `POST /api/v1/runs/{id}/approval` | Replaces the Phase 3 CLI approval path |
| 6.5 | Implement `POST /api/v1/webhooks/github` | A real GitHub push/PR event triggers a run automatically |

**Exit demo:** push a commit to the test repo; with no manual trigger, a run starts, executes, pauses, and you approve it through the API (or a simple `curl`) rather than the engine CLI.

---

### Phase 7 — Observability
**Goal:** every run is fully explainable after the fact, without reading raw LLM transcripts.

| # | Task | Done when |
|---|---|---|
| 7.1 | Emit `node_start` / `node_complete` events with latency | Present in `run_events` for every node |
| 7.2 | Emit `route_selected` events (which conditional edge fired and why) | Present for every conditional edge traversal |
| 7.3 | Emit `retry` / `escalation` / `human_decision` events | Present for every occurrence in Phase 3/5 tests |
| 7.4 | Build a simple trace-reconstruction script/query (`GET /runs/{id}/events` ordered) | A full run's story can be read top-to-bottom from one query |

**Exit demo:** take any completed run and answer "what exactly happened and why" using only `run_events` — no logs, no re-running.

---

### Phase 8 — Hardening & multi-project
**Goal:** prove the "one graph, every project" claim from the README is actually true.

| # | Task | Done when |
|---|---|---|
| 8.1 | Register a second, different test project against the same `feature-development` workflow | Both run independently |
| 8.2 | Concurrency test: trigger runs on both projects simultaneously | No cross-project state leakage; verified via `run_events` and `workflow_runs.project_id` |
| 8.3 | Add advisory locking for same-project concurrent runs touching the same branch | Two concurrent runs on the same project/branch serialize correctly, don't corrupt each other |
| 8.4 | Load/soak test: N runs over M hours without leaks, orphaned checkpoints, or stuck `waiting_human` runs | Clean run after soak period |

**Exit demo:** two unrelated test repos, registered as separate projects, both running the same workflow concurrently without interference.

---

### Phase 9 — Multi-tenant, Azure DevOps, Web UI (post-v1)

Only sequenced in detail once Phases 0–8 are proven. High-level shape (from `docs/architecture.md` §10, §11, §15):

- Tenant isolation at the query layer + encrypted credential scoping
- `AzureDevOpsAdapter` implementing the same `VcsAdapter` protocol proven in Phase 4
- Kubernetes deployment (`orchestrator-worker` scaling on queue depth)
- Web UI for approval gates and run inspection, replacing the CLI/`curl` workflow from Phase 6

---

## 5. Dependency graph (what blocks what)

```
Phase 0 (env/schema)
  └─▶ Phase 1 (engine core, stub nodes)
        └─▶ Phase 2 (real agent nodes)
              ├─▶ Phase 3 (human-in-the-loop + checkpointing)
              │     └─▶ Phase 5 (retry/escalation — reuses interrupt mechanism)
              └─▶ Phase 4 (GitHub integration)
                    └─▶ Phase 6 (backend + API)
                          └─▶ Phase 7 (observability)
                                └─▶ Phase 8 (hardening + multi-project)
                                      └─▶ Phase 9 (multi-tenant, ADO, Web UI)
```

Phases 3 and 4 can run in parallel once Phase 2 is done — they touch different parts of the system (interrupt handling vs. VCS I/O). Phase 5 depends on Phase 3's interrupt mechanism, not on Phase 4.

---

## 6. Risks & mitigations

| Risk | Phase most affected | Mitigation |
|---|---|---|
| LLM structured-output failures block graph progress | 2, 5 | Treat as expected from Phase 2 onward; build `MODEL_FORMAT_ERROR` repair path early, even ahead of full Phase 5 |
| Checkpoint/resume bugs cause silent data loss | 3 | The kill-and-resume test (3.4) is non-negotiable — do not proceed to Phase 4 without it passing reliably, including under induced failures |
| Idempotency gaps cause duplicate PRs or side effects on retry | 4, 5 | Idempotency key enforcement (5.4) should land before any real GitHub write path is exercised under retry conditions |
| Scope creep toward multi-tenant/Web UI before core loop is proven | All | Scope boundaries (§2) are a hard gate — Phase 9 items are explicitly out of v1 |
| Webhook-triggered runs firing unexpectedly on a real repo during testing | 6 | Use a disposable/sandbox GitHub repo for all integration testing until Phase 8 hardening is complete |

---

## 7. Definition of "v1 done"

v1 is complete when all of the following are simultaneously true on a real (sandbox) GitHub repo:

- [ ] A push to the repo triggers a run automatically (no manual invocation)
- [ ] The run executes plan → code → review → test without human intervention
- [ ] The run pauses for approval, survives an engine restart mid-pause, and resumes correctly
- [ ] Approving via the API results in a real pull request on the repo
- [ ] A forced failure (e.g., revoked credential) escalates to a human with a correctly classified reason, not a crash
- [ ] The full run is reconstructable, start to finish, from `run_events` alone
- [ ] Two different registered projects can run the same workflow concurrently without interference

---

## 8. Changelog

| Date | Change |
|---|---|
| 2026-08-07 | Initial implementation plan and roadmap v0.1 |
