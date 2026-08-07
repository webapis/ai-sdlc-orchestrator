# Tests

See `docs/architecture.md` §18 for the full testing strategy. Planned
layout:

```
tests/
├── routing/         Pure unit tests for routing_registry.py functions
├── nodes/            Function-node unit tests (mocked adapters)
├── agents/            Agent-node contract tests (fixed mock LLM responses)
├── graphs/            Full-graph integration tests (stubbed NodeRegistry)
├── retry/             Fault-injection tests per FailureCategory
└── tenancy/            Multi-tenant isolation regression tests
```

Not yet implemented — scaffold alongside each corresponding engine
module as it's built (Phase 1 roadmap).
