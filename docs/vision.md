---
title: "AI SDLC Orchestrator"
subtitle: "Project Context & Working Draft"
date: "August 7, 2026"
---

# AI SDLC Orchestrator

**Working draft — consolidated context**
*Compiled from project discussion, August 2026*

---

## 1. Executive Summary

The **AI SDLC Orchestrator** is a proposed platform for coordinating multiple AI agents across the software development lifecycle (SDLC) — planning, coding, review, testing, and deployment — rather than relying on a single, unstructured chat session with one AI.

The core idea builds on a pattern increasingly referred to as **"graph engineering"**: instead of prompting an AI turn-by-turn, the work is represented as a graph of **nodes** (units of work — an agent, a tool call, a validation step, a human approval) connected by **edges** (dependencies and routing rules), sharing a common **state** (the record of what the system knows at any point).

This document consolidates:
1. The original project outline (from the initial guidebook drafting session)
2. Background on the "graph engineering" concept the platform is built around
3. A survey of tools and frameworks relevant to implementation
4. A worked, runnable example of the underlying orchestration pattern (LangGraph)
5. Open questions and next steps

---

## 2. Original Guidebook Outline (v1)

The first draft guidebook produced for this project covered:

- Executive vision
- Business justification
- Core architecture
- AI role definitions
- Workflow contracts
- LangGraph orchestration model
- State machine design
- Multi-project execution model
- Docker deployment strategy
- Roadmap
- LangGraph node definitions
- Repository structure
- Architecture diagrams

### Proposed v2 scope (expanded architecture handbook)

A more comprehensive follow-up (50–100 pages) was scoped to include:

- C4 architecture diagrams
- LangGraph implementation in Python
- ASP.NET Core backend design
- PostgreSQL schema
- Project registration model
- Workflow YAML specifications
- Agent prompts library
- Retry & escalation engine
- Multi-tenant architecture
- GitHub / Azure DevOps integration
- Cursor Automation integration
- Docker / Kubernetes deployment
- Sequence diagrams
- Security model
- Step-by-step implementation roadmap

This v2 scope is intended as the **technical design blueprint** for building the platform, not just a conceptual overview.

### Recommended knowledge-base structure

To keep the project reusable across AI tools (Claude, GPT, Cursor, etc.) rather than trapped in a single chat transcript, the recommended repository layout is:

```
ai-sdlc-orchestrator/
├── README.md
├── AI_SOFTWARE_FACTORY_VISION.md
├── /docs
│   ├── vision.md
│   ├── architecture.md
│   ├── workflow-model.md
│   ├── langgraph-design.md
│   ├── orchestrator-engine.md
│   └── /conversations
├── /roles
├── /workflows
├── /contracts
└── /architecture
```

The rationale: any AI assistant can be given this repository as context and continue the design work productively, whereas a raw chat transcript degrades as a durable reference.

---

## 3. Conceptual Foundation: Graph Engineering

### 3.1 Definition

Graph engineering is the practice of representing an AI application as an **executable graph** — agents, tools, deterministic functions, validators, data sources, and humans coordinating through defined structure, rather than a single autonomous agent making all decisions inside one context window.

A useful way to place it alongside adjacent disciplines:

| Layer | Controls |
|---|---|
| Prompt engineering | Individual model calls |
| Context engineering | What each model call sees |
| Agent / loop engineering | How one agent reasons and uses tools |
| **Graph engineering** | How multiple agents, loops, functions, validators, tools, and humans work together |

### 3.2 Core components

- **Nodes** — a bounded unit of execution: an LLM call, a full tool-using agent, a plain function, a database query, an API request, a policy check, a test suite, a human approval request, or a subgraph. *Not every node needs to be an AI agent* — deterministic business rules (e.g., "does this invoice exceed the approval threshold?") should stay as plain code; LLMs are for genuine ambiguity, interpretation, or generation.
- **Edges** — define which nodes may execute after another. Types include direct, conditional, parallel, looping, error, human-controlled, and event-triggered edges.
- **State** — the shared, typed record carried through the graph (e.g., a `TypedDict` in LangGraph). Nodes read only what they need and return only what they own.
- **State reducers** — rules for merging concurrent updates when parallel nodes write to the same state field (append lists, merge dicts, pick latest, custom resolution).
- **Routes / guard conditions** — functions that inspect state and decide which edge to follow. Hard constraints belong in routing code, not buried in prompts.
- **Checkpoints** — snapshots of graph state, enabling resume-after-interruption, failure recovery, and long-running or paused workflows.
- **Interrupts** — a mechanism to pause the graph and request external (human) input before continuing — e.g., approval before sending an email or issuing a refund.

### 3.3 Common orchestration patterns

- **Prompt chaining** — each node processes the previous node's output; good for fixed, verifiable stages.
- **Routing** — a router sends work to a specialized branch (deterministic when categories are exact, model-based when classification needs judgment).
- **Parallelization** — independent tasks run concurrently to cut latency; only truly independent tasks should be parallelized.
- **Orchestrator–worker** — an orchestrator decomposes a task and delegates to workers; useful when subtasks can't be known in advance.
- **Evaluator–optimizer** — one component generates, another evaluates and requests revision; works best with clear evaluation criteria.
- **Human-in-the-loop** — a human reviews before a consequential action; should be risk-based, not applied to every trivial step.

### 3.4 Three levels of implementation (informal)

1. **Level 1 — Manual.** Separate lanes sketched on a whiteboard tool (Excalidraw, tldraw). No automation.
2. **Level 2 — Assisted.** Using Claude Code, Cursor, or Codex directly: each step in the workflow writes its own file (plan.md, research.md, review.md, etc.), leaving a paper trail that can be compared and reused later.
3. **Level 3 — Orchestrated.** A dedicated framework (LangGraph, AutoGen GraphFlow, Google ADK, n8n, Make.com, or custom scripts) actually runs the graph with real state, checkpoints, and human-in-the-loop gates.

The AI SDLC Orchestrator, as scoped, targets **Level 3**.

### 3.5 Production requirements often missed in diagrams

- **Node contracts** — every node should define required inputs, produced outputs, allowed tools, timeout, retry policy, side effects, failure categories, validation rules, and ownership.
- **Idempotency** — retries must not repeat irreversible actions (e.g., a payment node must not double-charge). Use idempotency keys, transaction IDs, deduplication checks.
- **Error classification** — not every failure should be retried the same way:

  | Failure type | Handling |
  |---|---|
  | Temporary network failure | Retry |
  | Rate limit | Wait and retry |
  | Invalid input | Return to validation |
  | Missing permission | Escalate |
  | Policy violation | Stop |
  | Model formatting failure | Repair output |

- **Context isolation** — don't give every node the full graph state; scope each node's visible context to only what it needs (reduces token cost, accidental data exposure, and distraction).
- **Observability** — trace node start/completion, selected route, changed state fields, tool calls, model/prompt version, token consumption, latency, retry count, validation results, human decisions, and final outcome.

### 3.6 Known limitations of graph engineering

- Additional infrastructure and state-management complexity
- Higher testing requirements
- Synchronization challenges at parallel join points
- Increased model cost when many agents are used
- Harder versioning and migrations
- Risk of overengineering simple tasks — a graph is only useful when its structure makes the system safer, faster, or easier to maintain; not because it "has more boxes"

---

## 4. Relevant Tools & Frameworks

### 4.1 Orchestration frameworks (build-your-own-graph)

| Framework | Model | Best suited for |
|---|---|---|
| **LangGraph** (LangChain) | Directed graph, explicit nodes/edges/state | Low-level control over state, routing, persistence, subgraphs, interrupts, mixed deterministic + agentic execution |
| **Microsoft AutoGen (GraphFlow)** | Agents as conversational participants along a graph | Conversational multi-agent workflows, coding agents, rapid prototyping |
| **Google ADK (Agent Development Kit)** | Named workflow agents (sequential, parallel, loop) + routing + A2A protocol | Teams in the Google ecosystem; multi-language (Python, TS/JS, Go, Java, Kotlin); explicitly built for production, not just prototypes |
| **Microsoft Agent Framework** | Typed workflows, graph routing | Python/.NET/Go teams needing typed workflows, checkpointing, human interaction, enterprise integration |
| **CrewAI** | Role-based agent teams (not a pure graph) | Fast prototyping; simpler branching needs |
| **n8n / Make.com** | Visual no-code automation graphs | When the graph needs to reach real business tools — Slack, email, CRM, Airtable |

### 4.2 Tools already available without a separate framework

- **Claude Code** — subagents act as nodes, the main session acts as orchestrator, a shared task list acts as state. No separate framework required for Level 2 work; the Claude Agent SDK is the path to Level 3 (unattended, version-controlled, programmatically fan-out graphs).
- **Cursor** — supports up to 8 parallel agents on isolated Git branches, a two-phase Plan Mode (reasoning pass separated from execution), and "Mission Control" for managing multiple concurrent agent workflows. Also maintains its own internal code/symbol graph (distinct from an agent-orchestration graph) for fast codebase understanding.

### 4.3 Decision guidance

- Choose **LangGraph** for controlled orchestration, stateful execution, durable checkpoints, and approval workflows where reliability matters most.
- Choose **AutoGen** for conversational multi-agent collaboration and fast, quality-sensitive prototyping.
- Choose **Google ADK** if building within the Google ecosystem or needing cross-vendor agent delegation via A2A.
- Stay with **plain Python / existing workflow engines** when most of the pipeline is deterministic and only a few steps genuinely need an LLM.

---

## 5. Worked Example: LangGraph Reference Implementation

This is a runnable reference pattern illustrating the node/edge/state/interrupt model the Orchestrator's workflow engine is expected to use internally.

### 5.1 Scenario

A 7-stage pipeline: **plan → research → write → evaluate → revise (looped) → human approval → finalize.**

### 5.2 Setup

```bash
pip install -U langgraph langchain langchain-openai
```

### 5.3 Shared state definition

```python
from typing import Literal, TypedDict
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

model = init_chat_model("openai:gpt-4.1-mini")

class ResearchState(TypedDict, total=False):
    topic: str
    plan: str
    evidence: str
    draft: str
    feedback: str
    evaluator_approved: bool
    human_approved: bool
    revision_count: int

class ReviewResult(BaseModel):
    approved: bool = Field(description="Whether the draft is accurate and well grounded.")
    feedback: str = Field(description="Specific corrections required before approval.")

review_model = model.with_structured_output(ReviewResult)
```

### 5.4 Nodes

```python
def planner_node(state):
    response = model.invoke(f"Create a concise research plan for: {state['topic']}")
    return {"plan": response.content, "revision_count": 0}

def researcher_node(state):
    response = model.invoke(
        f"Produce a grounded research brief for {state['topic']} following plan: {state['plan']}"
    )
    return {"evidence": response.content}

def writer_node(state):
    response = model.invoke(
        f"Write a professional article using only this evidence: {state['evidence']}"
    )
    return {"draft": response.content}

def evaluator_node(state):
    review = review_model.invoke(
        f"Evaluate this draft against the evidence.\nEvidence: {state['evidence']}\nDraft: {state['draft']}"
    )
    return {"evaluator_approved": review.approved, "feedback": review.feedback}

def revision_node(state):
    response = model.invoke(
        f"Revise this draft based on feedback.\nDraft: {state['draft']}\nFeedback: {state['feedback']}"
    )
    return {"draft": response.content, "revision_count": state.get("revision_count", 0) + 1}

def human_review_node(state):
    decision = interrupt({
        "message": "Review this article before finalization.",
        "draft": state["draft"],
        "allowed_actions": ["approve", "reject"],
    })
    return {"human_approved": decision.get("action") == "approve"}

def finalize_node(state):
    return {"human_approved": True}
```

### 5.5 Routing (the graph-engineering logic itself)

```python
def route_after_evaluation(state) -> Literal["revise", "human_review"]:
    if state.get("evaluator_approved"):
        return "human_review"
    if state.get("revision_count", 0) >= 2:
        return "human_review"
    return "revise"

def route_after_human_review(state) -> Literal["finalize", "revise"]:
    return "finalize" if state.get("human_approved") else "revise"
```

### 5.6 Building and compiling the graph

```python
builder = StateGraph(ResearchState)

for name, fn in [
    ("planner", planner_node), ("researcher", researcher_node),
    ("writer", writer_node), ("evaluator", evaluator_node),
    ("revise", revision_node), ("human_review", human_review_node),
    ("finalize", finalize_node),
]:
    builder.add_node(name, fn)

builder.add_edge(START, "planner")
builder.add_edge("planner", "researcher")
builder.add_edge("researcher", "writer")
builder.add_edge("writer", "evaluator")
builder.add_conditional_edges("evaluator", route_after_evaluation,
    {"revise": "revise", "human_review": "human_review"})
builder.add_edge("revise", "evaluator")
builder.add_conditional_edges("human_review", route_after_human_review,
    {"finalize": "finalize", "revise": "revise"})
builder.add_edge("finalize", END)

checkpointer = InMemorySaver()
graph = builder.compile(checkpointer=checkpointer)
```

### 5.7 Running and resuming (human-in-the-loop)

```python
config = {"configurable": {"thread_id": "orchestrator-job-001"}}

result = graph.invoke({"topic": "..."}, config=config)
if "__interrupt__" in result:
    print("Waiting for human approval.")

# resume later, using the same thread_id:
final_state = graph.invoke(
    Command(resume={"action": "approve", "feedback": "Approved."}),
    config=config,
)
```

**Note:** `InMemorySaver` is demonstration-only — it loses all checkpoints on process restart. A production Orchestrator needs a durable, database-backed checkpointer (this maps directly to the "PostgreSQL schema" item in the v2 scope above).

---

## 6. Mapping Graph Engineering Concepts to the Orchestrator's Architecture

| Graph engineering concept | Orchestrator equivalent |
|---|---|
| Node | An SDLC stage: plan, code, review, test, deploy — or a sub-agent within one |
| Edge / routing function | Workflow contracts / transition rules between SDLC stages |
| State | Shared project/task state, likely persisted in PostgreSQL |
| Node contract | AI role definitions (inputs, outputs, tools, failure handling per role) |
| Checkpoint | Persistent workflow state across long-running multi-day SDLC tasks |
| Interrupt / human-in-the-loop | Human approval gates (e.g., before deployment, before merging) |
| Error classification / retry policy | Retry & escalation engine |
| Multiple concurrent graphs | Multi-project execution model / multi-tenant architecture |
| Framework choice | LangGraph, as already selected in the v1/v2 outline |
| Execution environment | Docker / Kubernetes deployment strategy |
| External tool integration | GitHub / Azure DevOps / Cursor Automation integration |

---

## 7. Open Questions / Next Steps

- [ ] Finalize whether the backend is ASP.NET Core (as scoped in v2) with LangGraph as an embedded Python orchestration service, or a different service boundary
- [ ] Define the PostgreSQL schema for workflow/task/project state
- [ ] Draft the workflow YAML specification format referenced in v2 scope
- [ ] Build the initial agent prompts library per SDLC role (planner, coder, reviewer, tester, deployer)
- [ ] Design the retry & escalation engine's failure-classification rules (see §3.5)
- [ ] Decide on multi-tenant isolation model (per-project state, per-tenant credentials)
- [ ] Scope GitHub / Azure DevOps / Cursor Automation integration surface
- [ ] Stand up the recommended repository structure (§2) as the durable knowledge base for continued design work across AI tools
- [ ] Decide on checkpoint persistence backend (replace `InMemorySaver` with a durable store)

---

*Document compiled from project discussion — intended as a living reference. Update as design decisions are finalized.*
