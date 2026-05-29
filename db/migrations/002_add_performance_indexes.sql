-- Performance indexes for scoring and search

CREATE INDEX IF NOT EXISTS idx_funcionario_dni
ON funcionario(dni);

CREATE INDEX IF NOT EXISTS idx_funcionario_nombre
ON funcionario(nombre_completo);

CREATE INDEX IF NOT EXISTS idx_contrato_responsable_id
ON contrato(responsable_id, fecha_publicacion DESC);

CREATE INDEX IF NOT EXISTS idx_contrato_monto
ON contrato(monto)
WHERE monto > 100000;

CREATE INDEX IF NOT EXISTS idx_proceso_funcionario_tipo
ON proceso(acusado_id, estado);

-- Score cache table
CREATE TABLE IF NOT EXISTS scoring_cache (
    id SERIAL PRIMARY KEY,
    funcionario_id INTEGER NOT NULL,
    ier_score FLOAT NOT NULL,
    layer1_score FLOAT,
    layer2_score FLOAT,
    layer3_score FLOAT,
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ DEFAULT NOW() + INTERVAL '7 days',

    UNIQUE(funcionario_id)
);

CREATE INDEX IF NOT EXISTS idx_scoring_cache_expires
ON scoring_cache(expires_at);

COMMIT;
