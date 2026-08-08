# AI SDLC Orchestrator

Coordinates multiple AI agents across the software development lifecycle
(planning, coding, review, testing, deployment) as a managed, auditable
workflow graph — rather than a single unstructured chat session.

Status: **design phase**. See `docs/` for the vision and full developer
manual before writing code.

## Why this project

- **One graph, every project.** A workflow is defined once and reused
  across every registered project — onboard the 10th project for almost
  nothing, instead of re-explaining your dev process to an AI each time.
- **Nothing ships without a human looking at it.** Every run pauses at a
  human-approval gate before merge/deploy, with full state checkpointed.
  AI-speed iteration on coding/review/test — but a person is always the
  last gate before production.
- **A full audit trail, for free.** Every node execution, routing
  decision, retry, and human decision is written to `run_events`. If
  something ships broken, you have a literal timeline instead of guesswork.
- **Failures are handled by category, not by panic.** Rate limits,
  invalid input, and policy violations are each handled differently — no
  infinite retry loops, no silent failures on things that needed a human.
- **Change one piece without breaking the rest.** Prompts (`roles/`),
  workflow shape (`workflows/`), and routing logic (Python) are separate
  layers — edit one without risking the others.
- **Scales down as well as up.** A single developer using Claude Code
  subagents is already doing this pattern at a small scale. This project
  is what it looks like when that needs to run unattended, across many
  projects, with accountability — adopt it incrementally.
- **Good engineering discipline, not just AI plumbing.** Idempotency on
  side-effecting nodes, tenant isolation at the query layer, least-
  privilege tool access per role — useful practice regardless of the AI
  framing.

## Use cases

Three short stories showing what a run actually looks like — a Friday
feature request that gets approved from a phone, a flaky dependency that
escalates itself only when a human is truly needed, and one agency
reusing a single workflow across a dozen client projects.

Read the full stories in [`docs/use-cases.md`](docs/use-cases.md).

## Start here

1. Read [`docs/vision.md`](docs/vision.md) — why this exists, the graph
   engineering concepts it's built on, and the tool landscape it draws from.
2. Read [`docs/architecture.md`](docs/architecture.md) — the complete
   developer manual: system architecture, data model, workflow spec format,
   engine internals, security, and deployment.
3. Read [`docs/implementation-plan.md`](docs/implementation-plan.md) —
   the phased build order, exit criteria per phase, and what "v1 done"
   means. Check current phase and open items before starting work.

## Repository layout

```
ai-sdlc-orchestrator/
├── docs/                 Vision, architecture, and design docs
│   └── conversations/    Saved design-discussion transcripts
├── roles/                AI role definitions (prompt library)
├── workflows/             Workflow spec YAML files
├── contracts/             Node/tool contracts, JSON schemas
├── architecture/          Diagrams (C4, sequence)
├── src/
│   ├── api/               ASP.NET Core backend
│   └── engine/             Python LangGraph orchestration engine
├── tests/
└── deploy/
    └── k8s/                Kubernetes manifests
```

## Local development

See [`docs/architecture.md` §17](docs/architecture.md#17-local-development-setup)
for the full setup walkthrough (Docker Compose, Postgres, running the engine
worker and API locally).

## Design principles

- **Explicit over implicit.** Every AI-driven transition is a defined edge
  with a routing condition in code — never a decision hidden in a prompt.
- **Deterministic where possible.** Business rules are plain code. LLMs are
  reserved for genuine ambiguity, interpretation, generation, or planning.
- **Human authority preserved.** Deployments, merges, and other consequential
  actions pass through a human-in-the-loop gate by default.
- **Everything is inspectable.** Full state, routing decisions, and node
  outputs are persisted and queryable.
- **Reusable across projects.** A workflow defined once should run
  unmodified across every registered project/tenant.

## Contributing

This repo is the source of truth for the Orchestrator's own design and
implementation. When working with an AI assistant (Claude, GPT, Cursor,
etc.) on this codebase, point it at `docs/architecture.md` first — it
contains the schemas, interfaces, and conventions the rest of the code
must follow.
