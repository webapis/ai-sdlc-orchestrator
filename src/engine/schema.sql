-- Initial schema. See docs/architecture.md §5.
-- TODO: convert to Alembic (or preferred migration tool) migrations
-- before this is used against a real environment.

CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    repo_url TEXT,
    vcs_provider TEXT CHECK (vcs_provider IN ('github', 'azure_devops')),
    default_workflow_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id),
    name TEXT NOT NULL,
    version INT NOT NULL,
    spec_yaml TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, name, version)
);

CREATE TABLE workflow_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES projects(id),
    workflow_id UUID NOT NULL REFERENCES workflows(id),
    thread_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN
        ('pending','running','waiting_human','failed','completed','cancelled')),
    current_node TEXT,
    trigger_payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE workflow_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id UUID NOT NULL REFERENCES workflow_runs(id),
    thread_id TEXT NOT NULL,
    checkpoint_data JSONB NOT NULL,
    node_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

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

CREATE INDEX idx_workflow_runs_project_status ON workflow_runs(project_id, status);
CREATE INDEX idx_run_events_run_created ON run_events(run_id, created_at);
CREATE INDEX idx_checkpoints_thread_created ON workflow_checkpoints(thread_id, created_at DESC);
