---
title: "AI SDLC Orchestrator"
subtitle: "Developer Manual"
date: "August 7, 2026"
---

# AI SDLC Orchestrator — Developer Manual

**Version:** 0.1 (draft)
**Status:** Design blueprint — not yet implemented
**Audience:** Engineers building or contributing to the Orchestrator platform

---

## Table of Contents

1. Introduction
2. System Overview & Architecture
3. Core Concepts (Graph Engineering Primer)
4. Backend Architecture
5. Data Model (PostgreSQL Schema)
6. Workflow Specification Format (YAML)
7. AI Role Definitions & Prompt Library
8. Orchestration Engine (LangGraph)
9. Retry & Escalation Engine
10. Multi-Project & Multi-Tenant Execution Model
11. External Integrations
12. API Reference
13. Security Model
14. Observability & Logging
15. Deployment (Docker / Kubernetes)
16. Repository Structure
17. Local Development Setup
18. Testing Strategy
19. Roadmap
20. Appendix: Reference Implementation

---

## 1. Introduction

### 1.1 Purpose

The **AI SDLC Orchestrator** coordinates multiple AI agents across the software development lifecycle — planning, coding, review, testing, and deployment — as a managed, auditable workflow instead of a single unstructured chat session.

This manual is the implementation-facing companion to the project's conceptual vision document. Where the vision document explains *why* the platform exists, this manual explains *how* to build it: architecture, schemas, contracts, engine internals, and operational concerns.

### 1.2 Design Principles

- **Explicit over implicit.** Every transition between AI-driven steps is a defined edge with a routing condition in code, not a decision hidden inside a prompt.
- **Deterministic where possible.** Business rules and thresholds are plain code. LLMs are reserved for genuine ambiguity, interpretation, generation, or planning.
- **Human authority preserved.** Consequential actions (merges, deployments, refunds-equivalent operations) pass through a human-in-the-loop gate by default.
- **Everything is inspectable.** Full state, routing decisions, and node outputs are persisted and queryable — no silent steps.
- **Reusable across projects.** A workflow defined once (as a graph) should run unmodified across many registered projects/tenants.

### 1.3 Relationship to Graph Engineering

The Orchestrator implements the **graph engineering** pattern as its core execution model:

| Concept | Meaning in this system |
|---|---|
| Node | A bounded unit of work — an AI agent call, a deterministic function, a test run, a human approval gate |
| Edge | A permitted transition between nodes, governed by a routing function |
| State | The shared, typed record of a workflow run, persisted in PostgreSQL |
| Checkpoint | A durable snapshot enabling pause/resume across long-running SDLC tasks |
| Interrupt | A pause point requesting human input before continuing |

---

## 2. System Overview & Architecture

### 2.1 C4 Level 1 — System Context

```
                    ┌─────────────────────────┐
                    │        Developer          │
                    │   (registers projects,    │
                    │  approves gates, reviews)  │
                    └────────────┬─────────────┘
                                 │
                                 ▼
                 ┌───────────────────────────────┐
                 │      AI SDLC Orchestrator       │
                 │   (this system)                 │
                 └───┬─────────────┬───────────┬───┘
                     │             │           │
                     ▼             ▼           ▼
              ┌───────────┐ ┌───────────┐ ┌───────────┐
              │  GitHub /  │ │  Cursor    │ │   LLM      │
              │Azure DevOps│ │Automation  │ │ Providers  │
              └───────────┘ └───────────┘ └───────────┘
```

### 2.2 C4 Level 2 — Containers

| Container | Responsibility | Technology |
|---|---|---|
| **API Gateway / Backend** | Auth, project registration, REST API, webhooks | ASP.NET Core |
| **Orchestration Engine** | Executes workflow graphs, manages state & checkpoints | Python + LangGraph |
| **Task Queue** | Decouples API from long-running graph execution | (e.g., Redis-backed queue) |
| **Primary Datastore** | Projects, workflows, runs, state, audit log | PostgreSQL |
| **Agent Prompt Library** | Versioned prompt templates per AI role | Git-tracked YAML/Markdown |
| **Integration Adapters** | GitHub, Azure DevOps, Cursor Automation clients | Language-appropriate SDKs |
| **Web UI (optional, later phase)** | Human approval gates, run inspection, dashboards | Not yet scoped |

### 2.3 C4 Level 3 — Components (Orchestration Engine)

```
Orchestration Engine
├── GraphBuilder        — compiles a WorkflowSpec (YAML) into a LangGraph StateGraph
├── NodeRegistry         — maps node "type" strings to executable node functions
├── RoutingRegistry      — maps route names to routing/guard functions
├── StateStore           — persists/retrieves checkpointed state (Postgres-backed)
├── InterruptHandler      — manages human-in-the-loop pause/resume
├── RetryPolicyEngine    — classifies failures and applies retry/escalation rules
└── ExecutionTracer      — emits structured events for observability
```

### 2.4 Request Flow (typical run)

1. A trigger (webhook, manual API call, schedule) creates a **WorkflowRun** for a registered **Project**.
2. The Backend enqueues the run; the Orchestration Engine picks it up.
3. `GraphBuilder` compiles the project's assigned `WorkflowSpec` into an executable graph (cached after first compile).
4. The graph executes node by node; each node's output updates persisted state.
5. On an interrupt node (e.g., "approve before deploy"), execution pauses and a checkpoint is stored; the Backend notifies the developer.
6. On resume, the same `thread_id` (run ID) reloads state and continues.
7. On completion or terminal failure, the run is marked closed and the audit trail is finalized.

---

## 3. Core Concepts (Graph Engineering Primer)

*(See the companion vision document, §3, for the full conceptual treatment. Summarized here for implementers.)*

- **Nodes are not all AI agents.** A node may be an LLM call, a full tool-using agent, a plain Python/C# function, a database query, an external API call, a policy check, a test suite invocation, or a human approval request.
- **Routing logic lives in code, not prompts.** Every conditional edge is backed by a testable function that inspects state and returns the next node name.
- **State reducers matter for parallel nodes.** When two nodes write to the same state field concurrently (e.g., two review agents both appending findings), a reducer defines how updates merge — append, overwrite-latest, custom merge.
- **Checkpointing is mandatory in production**, not optional. `InMemorySaver`-style checkpointing is for local dev only; production requires a durable, queryable store (§5).
- **Interrupts are first-class**, not a workaround. Human approval nodes explicitly pause the graph and persist enough context for a developer to make an informed decision out-of-band.

---

## 4. Backend Architecture

### 4.1 Service Boundary

Two cooperating services:

1. **API/Backend (ASP.NET Core)** — owns authentication, project/tenant management, the public REST API, webhook ingestion, and notification dispatch. Does **not** run LangGraph directly.
2. **Orchestration Engine (Python)** — owns graph compilation and execution, LLM calls, and workflow state. Exposed to the Backend via an internal RPC/HTTP interface (not public-facing).

Rationale: keeps the .NET backend's surface area small and stable, while allowing the Python orchestration layer (tightly coupled to the fast-moving LangGraph ecosystem) to evolve independently.

### 4.2 Internal Interface (Backend → Engine)

```
POST /internal/runs
  { project_id, workflow_id, trigger_payload } → { run_id }

GET /internal/runs/{run_id}
  → { status, current_node, state_summary, pending_interrupt? }

POST /internal/runs/{run_id}/resume
  { action, payload } → { status }

POST /internal/runs/{run_id}/cancel
  → { status }
```

### 4.3 Technology Choices (as scoped)

| Layer | Choice | Notes |
|---|---|---|
| Backend framework | ASP.NET Core | REST API, auth, project registration |
| Orchestration | Python + LangGraph | Graph compilation & execution |
| Database | PostgreSQL | Single source of truth for state, audit, config |
| Containerization | Docker | All services containerized |
| Orchestration (infra) | Kubernetes | Target production deployment |
| VCS Integration | GitHub API / Azure DevOps API | PR creation, status checks, branch ops |
| IDE Automation | Cursor Automation | Delegated coding-node execution |

---

## 5. Data Model (PostgreSQL Schema)

### 5.1 Core Tables

```sql
-- Tenants (organizations)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Projects registered with the Orchestrator
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    repo_url TEXT,
    vcs_provider TEXT CHECK (vcs_provider IN ('github', 'azure_devops')),
    default_workflow_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Versioned workflow definitions (compiled from YAML spec, §6)
CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    version INT NOT NULL,
    spec_yaml TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name, version)
);

-- A single execution of a workflow against a project
CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    thread_id TEXT NOT NULL UNIQUE,       -- LangGraph checkpoint thread id
    status TEXT NOT NULL CHECK (status IN
        ('pending','running','waiting_human','failed','completed','cancelled')),
    current_node TEXT,
    trigger_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

-- Checkpointed graph state (LangGraph-compatible checkpoint store)
CREATE TABLE workflow_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES workflow_runs(id),
    thread_id TEXT NOT NULL,
    checkpoint_data JSONB NOT NULL,
    node_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Structured audit / observability trail (one row per node execution)
CREATE TABLE run_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES workflow_runs(id),
    node_name TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN
        ('node_start','node_complete','route_selected','tool_call',
         'retry','escalation','human_decision','error')),
    payload JSONB,
    latency_ms INT,
    token_usage JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Human-in-the-loop approval requests
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES workflow_runs(id),
    node_name TEXT NOT NULL,
    context JSONB NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected')),
    decided_by TEXT,
    decided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### 5.2 Indexing Notes

- `workflow_runs(project_id, status)` — for dashboards listing active runs per project.
- `run_events(run_id, created_at)` — for chronological trace reconstruction.
- `workflow_checkpoints(thread_id, created_at DESC)` — for fast "latest checkpoint" lookup on resume.

---

## 6. Workflow Specification Format (YAML)

Workflows are authored as YAML and compiled into a LangGraph `StateGraph` at runtime by `GraphBuilder`.

### 6.1 Example: Feature Development Workflow

```yaml
name: feature-development
version: 1

state_schema:
  ticket_id: str
  spec: str
  diff: str
  review_feedback: str
  review_approved: bool
  tests_passed: bool
  human_approved: bool
  revision_count: int

nodes:
  - id: plan
    type: agent
    role: planner            # references roles/planner.yaml (§7)
    outputs: [spec]

  - id: code
    type: agent
    role: coder
    inputs: [spec]
    outputs: [diff]
    tools: [cursor_automation, repo_read, repo_write]

  - id: review
    type: agent
    role: reviewer
    inputs: [diff]
    outputs: [review_feedback, review_approved]

  - id: test
    type: function            # deterministic, not an LLM call
    handler: run_test_suite
    inputs: [diff]
    outputs: [tests_passed]

  - id: revise
    type: agent
    role: coder
    inputs: [diff, review_feedback]
    outputs: [diff]

  - id: human_approval
    type: human
    context_fields: [diff, review_feedback, tests_passed]
    allowed_actions: [approve, reject]

  - id: merge
    type: function
    handler: create_pull_request
    inputs: [diff]

edges:
  - from: START
    to: plan
  - from: plan
    to: code
  - from: code
    to: review
  - from: review
    to: test

routes:
  - from: test
    condition: route_after_test
    targets:
      revise: revise
      human_approval: human_approval

  - from: revise
    to: review               # loop back into review after revision

  - from: human_approval
    condition: route_after_human
    targets:
      merge: merge
      revise: revise

  - from: merge
    to: END

limits:
  revision_count_max: 3       # hard cap — enforced by route_after_test
```

### 6.2 Node Type Reference

| `type` | Meaning | Requires |
|---|---|---|
| `agent` | An LLM-backed node bound to a role defined in the prompt library (§7) | `role`, `inputs`, `outputs` |
| `function` | A deterministic handler registered in `NodeRegistry` | `handler`, `inputs`, `outputs` |
| `human` | An interrupt node — pauses for approval | `context_fields`, `allowed_actions` |
| `subgraph` | Embeds another named `WorkflowSpec` as a single node | `workflow_ref` |

### 6.3 Route Functions

Route conditions (`route_after_test`, `route_after_human`, etc.) are **not** written inline in YAML — they are registered Python functions in `RoutingRegistry`, keyed by the name referenced in the spec. This keeps hard business logic (e.g., revision caps) in tested code rather than in configuration.

---

## 7. AI Role Definitions & Prompt Library

### 7.1 Role File Format

Each AI role used by `agent`-type nodes is defined in its own versioned file under `/roles`.

```yaml
# roles/reviewer.yaml
name: reviewer
version: 1
model: claude-sonnet-5
system_prompt: |
  You are a senior code reviewer. You will be given a diff.
  Evaluate correctness, security, and adherence to project conventions.
  Do not approve diffs with unresolved TODOs or missing tests.
tools: [repo_read, static_analysis]
output_schema:
  review_feedback: str
  review_approved: bool
max_tokens: 4000
temperature: 0.2
```

### 7.2 Minimum Role Set (initial scope)

| Role | Responsibility | Typical node type |
|---|---|---|
| `planner` | Turns a ticket/spec into an actionable plan | `agent` |
| `coder` | Produces or revises a code diff | `agent` (+ Cursor Automation tool) |
| `reviewer` | Evaluates a diff for correctness/style/conventions | `agent` |
| `security-reviewer` | Evaluates a diff specifically for security issues, by severity | `agent` |
| `tester` | Interprets test suite output — diagnoses regressions vs. flaky failures | `agent`, backed by a `function` test-runner node |
| `monitor` | Assesses post-deploy health signals, flags suspected regressions | `agent` |
| `release-notes-writer` | Summarizes merged changes | `agent` |
| `deployer` | Executes or requests approval for deployment steps | mix of `function` + `human` |

`reviewer` and `security-reviewer` are deliberately separate roles, not one role with two concerns — this keeps each role's system prompt focused and lets a workflow spec require both independently (a diff can be style-approved but security-blocked, or vice versa).

### 7.3 Prompt Versioning Rule

Role files are versioned (`version: N`) and immutable once referenced by a compiled `WorkflowSpec`. Changing a role's prompt requires bumping its version; existing workflow specs continue to reference the version they were authored against unless explicitly upgraded. This prevents silent behavior drift in already-deployed workflows.

---

## 8. Orchestration Engine (LangGraph)

### 8.1 GraphBuilder — compiling YAML into LangGraph

```python
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver  # production checkpointer
import yaml

def build_graph(spec_yaml: str, node_registry, routing_registry):
    spec = yaml.safe_load(spec_yaml)
    StateSchema = build_typed_dict(spec["state_schema"])  # dynamic TypedDict

    builder = StateGraph(StateSchema)

    for node in spec["nodes"]:
        handler = node_registry.resolve(node)   # agent / function / human / subgraph
        builder.add_node(node["id"], handler)

    for edge in spec.get("edges", []):
        src = START if edge["from"] == "START" else edge["from"]
        dst = END if edge["to"] == "END" else edge["to"]
        builder.add_edge(src, dst)

    for route in spec.get("routes", []):
        if "condition" in route:
            route_fn = routing_registry.resolve(route["condition"])
            builder.add_conditional_edges(route["from"], route_fn, route["targets"])
        else:
            dst = END if route["to"] == "END" else route["to"]
            builder.add_edge(route["from"], dst)

    checkpointer = PostgresSaver.from_conn_string(DATABASE_URL)
    return builder.compile(checkpointer=checkpointer)
```

### 8.2 NodeRegistry — resolving node types to executables

```python
class NodeRegistry:
    def __init__(self):
        self._functions = {}   # handler name -> callable
        self._roles = {}       # role name -> RoleConfig

    def register_function(self, name, fn):
        self._functions[name] = fn

    def register_role(self, name, role_config):
        self._roles[name] = role_config

    def resolve(self, node_spec):
        if node_spec["type"] == "agent":
            role = self._roles[node_spec["role"]]
            return make_agent_node(role, node_spec)
        if node_spec["type"] == "function":
            return self._functions[node_spec["handler"]]
        if node_spec["type"] == "human":
            return make_human_node(node_spec)
        if node_spec["type"] == "subgraph":
            return make_subgraph_node(node_spec)
        raise ValueError(f"Unknown node type: {node_spec['type']}")
```

### 8.3 Human Node Implementation

```python
from langgraph.types import interrupt

def make_human_node(node_spec):
    def human_node(state):
        context = {field: state.get(field) for field in node_spec["context_fields"]}
        decision = interrupt({
            "message": f"Approval required at node '{node_spec['id']}'.",
            "context": context,
            "allowed_actions": node_spec["allowed_actions"],
        })
        return {"human_approved": decision.get("action") == "approve"}
    return human_node
```

### 8.4 Running & Resuming a Compiled Graph

```python
graph = build_graph(workflow.spec_yaml, node_registry, routing_registry)
config = {"configurable": {"thread_id": run.thread_id}}

result = graph.invoke(initial_state, config=config)
if "__interrupt__" in result:
    persist_approval_request(run.id, result["__interrupt__"])
    mark_run_status(run.id, "waiting_human")

# On developer decision (via API):
final_state = graph.invoke(
    Command(resume={"action": decision, "feedback": comment}),
    config=config,
)
```

---

## 9. Retry & Escalation Engine

### 9.1 Failure Classification

Every node execution failure is classified before a retry policy is applied:

```python
class FailureCategory(str, Enum):
    TRANSIENT_NETWORK = "transient_network"
    RATE_LIMIT = "rate_limit"
    INVALID_INPUT = "invalid_input"
    PERMISSION_DENIED = "permission_denied"
    POLICY_VIOLATION = "policy_violation"
    MODEL_FORMAT_ERROR = "model_format_error"
    UNKNOWN = "unknown"

RETRY_POLICY = {
    FailureCategory.TRANSIENT_NETWORK: RetryPolicy(max_attempts=3, backoff="exponential"),
    FailureCategory.RATE_LIMIT:        RetryPolicy(max_attempts=5, backoff="exponential", wait_for_reset=True),
    FailureCategory.INVALID_INPUT:     RetryPolicy(max_attempts=0, action="return_to_validation"),
    FailureCategory.PERMISSION_DENIED: RetryPolicy(max_attempts=0, action="escalate_to_human"),
    FailureCategory.POLICY_VIOLATION:  RetryPolicy(max_attempts=0, action="stop_run"),
    FailureCategory.MODEL_FORMAT_ERROR:RetryPolicy(max_attempts=2, action="repair_output"),
}
```

### 9.2 Escalation Path

When a node exhausts its retry budget, or its category maps directly to `escalate_to_human`, the engine creates an `approval_requests` row with the failure context and transitions the run to `waiting_human` — reusing the same interrupt mechanism as planned human-approval nodes (§8.3), so escalations and planned approvals share one code path.

### 9.3 Idempotency Requirement

Any node with an external side effect (PR creation, deployment trigger, notification send) **must** accept an idempotency key derived from `(run_id, node_name, attempt_number)` and must be safe to re-invoke without duplicating the side effect. This is enforced at the `NodeRegistry.register_function` level — function nodes with side effects are required to declare an `idempotent: true` flag and an idempotency-key parameter, or the graph fails to compile.

---

## 10. Multi-Project & Multi-Tenant Execution Model

### 10.1 Isolation Boundaries

- **Tenant** — top-level isolation boundary (an organization). Owns workflows, credentials, and projects.
- **Project** — belongs to exactly one tenant; maps to one repository; has a default workflow but may override per-run.
- **Workflow run** — always scoped to exactly one project; never shares state across projects.

### 10.2 Concurrency Model

- Multiple `workflow_runs` may execute concurrently across different projects with no shared state.
- Within a single project, concurrent runs are allowed by default but should respect the same file-ownership caution called out in graph-engineering guidance generally: **do not** let two concurrently-running graphs target the same branch/PR without an explicit locking node.
- A lightweight advisory lock (e.g., a `project_locks` table keyed by `project_id` + `resource` such as a branch name) is acquired by any `function` node that writes to a shared VCS resource.

### 10.3 Credential Scoping

Per-tenant credentials (VCS tokens, LLM API keys if not using a shared pool) are stored encrypted and injected into node execution context at runtime — never embedded in workflow specs or role files, which are expected to be shareable/version-controlled artifacts.

---

## 11. External Integrations

### 11.1 GitHub / Azure DevOps

| Capability | Used by |
|---|---|
| Create/update pull request | `merge` function node |
| Post PR status check | `test`, `review` function nodes |
| Read repository content | `coder`, `reviewer` agent nodes |
| Branch creation | `code` function/agent node |

Adapters implement a common internal interface (`VcsAdapter`) so workflow specs stay provider-agnostic:

```python
class VcsAdapter(Protocol):
    def create_branch(self, project, base, name) -> None: ...
    def create_pull_request(self, project, branch, title, body) -> PullRequestRef: ...
    def post_status(self, project, ref, state, description) -> None: ...
    def read_file(self, project, path, ref) -> str: ...
```

`GitHubAdapter` and `AzureDevOpsAdapter` both implement this protocol; the workflow spec references only `vcs_provider` at the project level.

### 11.2 Cursor Automation

Used as a **tool** available to `coder`-role agent nodes for actually applying code changes inside a real editor/agent environment, rather than the Orchestrator's own agent hand-rolling file edits. The `coder` role's `tools` list (§7.1) includes `cursor_automation`; the tool implementation shells out to (or calls the API of) Cursor's automation surface and returns the resulting diff back into node output.

### 11.3 LLM Providers

Model selection is per-role (`model:` field in role YAML, §7.1), not global — allowing, for example, a cheaper/faster model for `planner` and a stronger model for `reviewer`. Provider abstraction goes through `langchain`'s `init_chat_model`, keeping provider swaps a configuration change rather than a code change.

---

## 12. API Reference (Backend, public surface)

```
POST   /api/v1/projects                      Register a new project
GET    /api/v1/projects/{id}                  Get project details
POST   /api/v1/workflows                      Register/version a workflow spec
GET    /api/v1/workflows/{id}                 Get workflow spec
POST   /api/v1/projects/{id}/runs             Trigger a workflow run
GET    /api/v1/runs/{id}                      Get run status & current state summary
GET    /api/v1/runs/{id}/events                List run_events (audit trail)
GET    /api/v1/runs/{id}/approval               Get pending approval_request (if any)
POST   /api/v1/runs/{id}/approval               Submit human decision (approve/reject)
POST   /api/v1/runs/{id}/cancel                 Cancel an in-progress run
POST   /api/v1/webhooks/github                  GitHub event ingestion (triggers runs)
POST   /api/v1/webhooks/azure-devops            Azure DevOps event ingestion
```

All endpoints require tenant-scoped authentication (bearer token). Run and project IDs are validated against the authenticated tenant on every request.

---

## 13. Security Model

- **Tenant isolation** enforced at the database query layer (every query scoped by `tenant_id`, never trusted from client input alone — derived from the authenticated principal).
- **Credential encryption at rest** for all stored VCS tokens and API keys (e.g., via a KMS-backed encryption layer).
- **Least-privilege tool access per role.** Each role's `tools` list is an allowlist; agent nodes cannot invoke tools outside their declared set, enforced by the tool-calling wrapper, not merely by prompt instruction.
- **Human gate for irreversible actions.** Deployment, merge-to-protected-branch, and any external notification/refund-equivalent action must pass through a `human` node or an explicitly risk-accepted policy exception recorded in the workflow spec.
- **Audit immutability.** `run_events` rows are append-only; no update/delete path is exposed via the API.
- **Secrets never enter workflow specs or role files.** These are treated as version-controlled, shareable artifacts (§7.3) and must not contain tenant secrets.

---

## 14. Observability & Logging

Every node execution emits structured events into `run_events` (§5.1):

- `node_start` / `node_complete` — with `latency_ms`
- `route_selected` — which conditional edge fired and why (routing function name + decision)
- `tool_call` — tool name, arguments (redacted if sensitive), result summary
- `retry` — failure category, attempt number
- `escalation` — reason, resulting `approval_requests` row
- `human_decision` — who decided, what action, timestamp
- `error` — unclassified/terminal errors

This gives a complete reconstructable trace of any run without needing to inspect raw LLM transcripts, and satisfies the "observability" requirement called out in the graph-engineering production checklist (vision doc §3.5).

---

## 15. Deployment (Docker / Kubernetes)

### 15.1 Container Layout

| Container | Image basis | Notes |
|---|---|---|
| `orchestrator-api` | ASP.NET Core runtime | Public-facing, horizontally scalable |
| `orchestrator-engine` | Python (LangGraph + deps) | Internal-only, horizontally scalable |
| `orchestrator-worker` | Same image as engine | Consumes task queue, executes graph runs |
| `postgres` | Managed/self-hosted Postgres | Stateful; use managed service in production |
| `redis` (or equivalent) | Task queue / pub-sub for interrupt notifications | |

### 15.2 Kubernetes Notes

- `orchestrator-worker` should scale on queue depth, not CPU alone — graph execution is I/O-bound (waiting on LLM calls).
- Long-running/paused runs (interrupted, `waiting_human`) hold no worker resources — they're fully checkpointed to Postgres, so workers are stateless and freely restartable.
- Use a `PodDisruptionBudget` on `orchestrator-worker` sized to tolerate in-flight run interruption gracefully (LangGraph checkpointing means an interrupted worker mid-run simply resumes from the last checkpoint on another pod).

---

## 16. Repository Structure

```
ai-sdlc-orchestrator/
├── README.md
├── AI_SOFTWARE_FACTORY_VISION.md
├── /docs
│   ├── vision.md
│   ├── architecture.md
│   ├── workflow-model.md
│   ├── langgraph-design.md
│   └── orchestrator-engine.md
├── /roles                     # role YAML files (§7)
│   ├── planner.yaml
│   ├── coder.yaml
│   ├── reviewer.yaml
│   └── deployer.yaml
├── /workflows                 # workflow spec YAML files (§6)
│   └── feature-development.yaml
├── /contracts                 # node/tool contracts, JSON schemas
├── /architecture               # diagrams (C4, sequence)
├── /src
│   ├── /api                   # ASP.NET Core backend
│   └── /engine                 # Python LangGraph engine
│       ├── graph_builder.py
│       ├── node_registry.py
│       ├── routing_registry.py
│       ├── retry_policy.py
│       └── adapters/
│           ├── github.py
│           └── azure_devops.py
├── /tests
├── docker-compose.yml
└── /deploy
    └── /k8s
```

---

## 17. Local Development Setup

```bash
# 1. Clone and enter the repo
git clone <repo-url> ai-sdlc-orchestrator
cd ai-sdlc-orchestrator

# 2. Start dependencies
docker compose up -d postgres redis

# 3. Python engine environment
cd src/engine
pip install -U langgraph langchain langchain-openai psycopg2-binary
python -m alembic upgrade head    # apply schema (§5)

# 4. Run the engine worker locally
python worker.py --queue local

# 5. .NET backend
cd ../api
dotnet restore
dotnet run

# 6. Register a test project and trigger a run
curl -X POST localhost:5000/api/v1/projects -d '{"name":"demo","repo_url":"..."}'
curl -X POST localhost:5000/api/v1/projects/{id}/runs -d '{"workflow":"feature-development"}'
```

For local runs, use `InMemorySaver` or a local Postgres checkpointer (never in staging/production — see §3).

---

## 18. Testing Strategy

| Layer | Approach |
|---|---|
| Routing functions | Pure unit tests — given a state dict, assert the returned route name |
| Function nodes | Unit tests with mocked external adapters (VCS, notification) |
| Agent nodes | Contract tests against a fixed, versioned mock LLM response set; separately, periodic live-model smoke tests |
| Full graph | Integration test compiling a real `WorkflowSpec` and running it against a stubbed `NodeRegistry` to assert the traversal order and terminal state for representative input scenarios |
| Retry/escalation | Fault-injection tests — force each `FailureCategory` and assert the correct policy path and resulting run status |
| Multi-tenant isolation | Regression tests asserting no query can return rows from a different `tenant_id` than the authenticated principal |

---

## 19. Roadmap

**Phase 1 — Foundation**
- [ ] PostgreSQL schema (§5) + migrations
- [ ] `GraphBuilder` + `NodeRegistry` + `RoutingRegistry` (§8)
- [ ] Minimal role set: planner, coder, reviewer (§7.2)
- [ ] Single reference workflow: `feature-development` (§6.1)
- [ ] Local dev environment (§17)

**Phase 2 — Reliability**
- [ ] Retry & Escalation Engine (§9)
- [ ] Durable checkpointing (`PostgresSaver`) in place of `InMemorySaver`
- [ ] Observability event pipeline (§14)
- [ ] Idempotency enforcement on side-effecting function nodes

**Phase 3 — Integration**
- [ ] GitHub adapter (§11.1)
- [ ] Azure DevOps adapter
- [ ] Cursor Automation tool integration (§11.2)
- [ ] Webhook-triggered runs

**Phase 4 — Multi-Tenant & Production Hardening**
- [ ] Multi-project/multi-tenant isolation (§10)
- [ ] Credential encryption & scoping
- [ ] Kubernetes deployment (§15)
- [ ] Security review against §13 checklist

**Phase 5 — Expansion**
- [ ] Additional roles (tester, release-notes-writer, deployer)
- [ ] Web UI for approval gates & run inspection
- [ ] Workflow marketplace / template sharing across tenants

---

## 20. Appendix: Reference Implementation

A minimal, runnable LangGraph example demonstrating the node/edge/state/interrupt pattern used throughout this manual (plan → research → write → evaluate → revise → human approval → finalize) is maintained separately in `/docs/langgraph-design.md` and in the project's earlier context document (`AI_SDLC_Orchestrator.md`). Use it as a sandbox to validate `GraphBuilder` changes before wiring in real role/workflow YAML.

---

*End of Developer Manual — v0.1 draft. This is a living document; update section version notes as architecture decisions are finalized during Phase 1.*
