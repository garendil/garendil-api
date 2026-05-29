-- Audit trail for scoring changes (rollback support)

CREATE TABLE IF NOT EXISTS scoring_audit_log (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL,
    ier_score_old FLOAT,
    ier_score_new FLOAT,
    layer1_score FLOAT,
    layer2_score FLOAT,
    layer3_score FLOAT,
    change_reason TEXT,
    changed_by TEXT DEFAULT 'system',
    changed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scoring_audit_log_funcionario
ON scoring_audit_log(funcionario_id, changed_at DESC);

CREATE INDEX IF NOT EXISTS idx_scoring_audit_log_changed_at
ON scoring_audit_log(changed_at DESC);

COMMIT;
