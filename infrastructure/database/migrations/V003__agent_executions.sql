CREATE TABLE IF NOT EXISTS knowledge.agent_executions (
    id uuid PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    state text NOT NULL CHECK (state IN ('Pending','Running','AwaitingApproval','Completed','Failed','Cancelled')),
    snapshot jsonb NOT NULL,
    request jsonb NOT NULL,
    next_sequence bigint NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS agent_executions_queue ON knowledge.agent_executions(state,created_at);
CREATE TABLE IF NOT EXISTS knowledge.agent_execution_events (
    execution_id uuid NOT NULL REFERENCES knowledge.agent_executions(id),
    sequence bigint NOT NULL,
    event jsonb NOT NULL,
    PRIMARY KEY(execution_id,sequence)
);
