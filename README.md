# AI SDLC Orchestrator

Coordinates multiple AI agents across the software development lifecycle
(planning, coding, review, testing, deployment) as a managed, auditable
workflow graph — rather than a single unstructured chat session.

Status: **design phase**. See `docs/` for the vision and full developer
manual before writing code.

## Start here

1. Read [`docs/vision.md`](docs/vision.md) — why this exists, the graph
   engineering concepts it's built on, and the tool landscape it draws from.
2. Read [`docs/architecture.md`](docs/architecture.md) — the complete
   developer manual: system architecture, data model, workflow spec format,
   engine internals, security, deployment, and the phased roadmap.
3. Check the [Roadmap](docs/architecture.md#19-roadmap) for current phase
   and open items before starting work.

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
