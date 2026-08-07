# Orchestration Engine

Python + LangGraph service that compiles workflow specs (`/workflows`)
into executable graphs and runs them. Internal-only — not exposed
directly to the public API; see `docs/architecture.md` §4.2 for the
internal RPC/HTTP interface the ASP.NET backend calls.

## Layout

- `graph_builder.py` — compiles a `WorkflowSpec` YAML into a LangGraph `StateGraph`
- `node_registry.py` — resolves node `type` (agent/function/human/subgraph) to executables
- `routing_registry.py` — named routing/guard functions referenced by workflow specs
- `retry_policy.py` — failure classification and retry/escalation rules
- `adapters/` — VCS provider adapters (GitHub, Azure DevOps)
- `schema.sql` — initial Postgres schema (convert to real migrations before use)

## Status

Skeleton only. See `docs/architecture.md` §19 Roadmap, Phase 1, for the
current build order.
