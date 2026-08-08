# Use Cases

Three short stories showing what a run through the Orchestrator actually
looks like, end to end.

---

## Story 1 — The Friday feature request

It's Friday afternoon. Priya files a ticket: *"Add a CSV export button to
the reports page."* Instead of picking it up herself, she triggers a run
against the `feature-development` workflow.

The **planner** reads the ticket and sketches an approach. The **coder**
picks it up, opens a branch, and writes the export logic using Cursor
Automation on the real repo. The **reviewer** checks the diff — flags a
missing test — and it loops back to the coder once. Tests pass. The graph
pauses.

Priya gets a notification: *"Approval required — diff ready for review."*
She reads the summary, checks the diff, and approves from her phone on
the way out. The PR opens itself. She merges it Monday morning.

She didn't write a line of code — but she made every decision that
mattered, and there's a full trace of exactly what happened while she
was gone.

---

## Story 2 — The flaky dependency

A run starts against the `payment-service` project. Midway through the
**test** node, an external API the tests depend on times out.

The engine classifies the failure as `transient_network`, not a real
problem — retries automatically with backoff, three attempts, no one
notified. Second run: the API is still down, but this time it returns a
`403`. Different category — `permission_denied` — no retry policy covers
that; the run escalates straight to a human.

Marcus gets pinged, not with a wall of logs, but with the actual
classified reason: *"Escalated — permission denied calling
payments-sandbox API."* He rotates an expired API key, resumes the run
from the exact checkpoint it paused at, and the graph finishes without
re-running anything that had already passed.

Nobody had to figure out *why* it failed — the system already knew.

---

## Story 3 — One agency, twelve client projects

Dana runs a small dev agency. Every client repo follows roughly the same
process: plan, build, review, test, ship — but each client has different
reviewers, different risk tolerance, different deploy targets.

Instead of maintaining twelve slightly-different playbooks in twelve
people's heads, Dana registers all twelve repos as projects under one
tenant, each pointing at the same `feature-development.yaml` workflow.
One client wants every deploy hand-approved; another trusts a green test
suite to merge on its own — that's a one-line change to *their* workflow
spec, not a rewrite.

When Dana onboards client thirteen, she doesn't start from scratch. She
registers the project, points it at the existing workflow, and it just
runs — the same graph, proven on twelve other codebases already.

---

## The pattern across all three

Every story is the same five beats: **trigger → graph executes → the
system decides what needs a human and what doesn't → you approve the
things that matter → it ships.** The stories differ only in *what*
triggered the run and *where* the human got pulled in — never in whether
someone stayed in control.
