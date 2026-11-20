-- 0009_governance_decision_records.sql
-- VANA Phase 1: Governance Decision & Abstention Record Persistence (PostgreSQL)

CREATE TABLE IF NOT EXISTS governance_decision_record (
    decision_id TEXT PRIMARY KEY,
    execution_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    observation_id TEXT NOT NULL,
    canonical_record_id TEXT,
    context_id TEXT,
    actor_id TEXT NOT NULL,
    actor_email TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    ruling TEXT NOT NULL CHECK (ruling IN ('ALLOW', 'ABSTAIN', 'DENY')),
    decision_action TEXT NOT NULL CHECK (decision_action IN ('dispatch', 'noop')),
    decision_reason TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('governed_abstention', 'action_request_generated')),
    abstention_record_id TEXT,
    action_request_id TEXT,
    governance_allowed INTEGER NOT NULL CHECK (governance_allowed IN (0, 1)),
    evidence_payload TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_gov_decision_obs ON governance_decision_record (observation_id);
CREATE INDEX IF NOT EXISTS idx_gov_decision_ruling ON governance_decision_record (ruling);
CREATE INDEX IF NOT EXISTS idx_gov_decision_idempotency ON governance_decision_record (idempotency_key);

INSERT INTO schema_version (version, applied_at, description)
VALUES ('0.9.5', NOW(), 'Adds persistent governance decision and abstention records (Phase 1)')
ON CONFLICT (version) DO NOTHING;
