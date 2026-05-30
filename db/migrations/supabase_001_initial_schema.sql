-- ============================================================
-- GARENDIL — Esquema inicial para Supabase
-- Ejecutar en: Supabase Dashboard → SQL Editor
-- Idempotente: seguro de ejecutar múltiples veces
-- ============================================================

-- ── Extensiones ───────────────────────────────────────────────────────────────

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pg_trgm";     -- búsqueda fuzzy por similitud
CREATE EXTENSION IF NOT EXISTS "unaccent";    -- búsqueda sin tildes

-- ── Trigger: updated_at automático ───────────────────────────────────────────

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ── Tabla: funcionarios ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS funcionarios (
    id                 SERIAL PRIMARY KEY,
    dni                VARCHAR(8)    UNIQUE NOT NULL,
    nombre_completo    VARCHAR(255)  NOT NULL,
    cargo_actual       VARCHAR(255),
    institucion        VARCHAR(255),

    score_ier          FLOAT         DEFAULT 0.0,
    score_competencia  FLOAT         DEFAULT 0.0,
    score_adecuacion   FLOAT         DEFAULT 0.0,

    foto_url           VARCHAR(512),
    descripcion        TEXT,
    verificado         BOOLEAN       DEFAULT FALSE,
    activo             BOOLEAN       DEFAULT TRUE,

    created_at         TIMESTAMPTZ   DEFAULT NOW() NOT NULL,
    updated_at         TIMESTAMPTZ   DEFAULT NOW() NOT NULL
);

DROP TRIGGER IF EXISTS trg_funcionarios_updated_at ON funcionarios;
CREATE TRIGGER trg_funcionarios_updated_at
    BEFORE UPDATE ON funcionarios
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Índices funcionarios
CREATE INDEX IF NOT EXISTS idx_func_dni
    ON funcionarios(dni);

CREATE INDEX IF NOT EXISTS idx_func_institucion
    ON funcionarios(institucion);

-- Búsqueda fuzzy por nombre (pg_trgm) — permite LIKE '%nombre%' con índice
CREATE INDEX IF NOT EXISTS idx_func_nombre_trgm
    ON funcionarios USING GIN (nombre_completo gin_trgm_ops);

-- Unaccent search helper (nombre sin tildes)
CREATE INDEX IF NOT EXISTS idx_func_nombre_unaccent_trgm
    ON funcionarios USING GIN (unaccent(nombre_completo) gin_trgm_ops);

-- Ranking por score IER descendente
CREATE INDEX IF NOT EXISTS idx_func_score_ier_desc
    ON funcionarios(score_ier DESC);

-- ── Tabla: empresas ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS empresas (
    id                     SERIAL PRIMARY KEY,
    ruc                    VARCHAR(11)   UNIQUE NOT NULL,
    nombre_razon_social    VARCHAR(255)  NOT NULL,

    estado                 VARCHAR(50),
    fecha_creacion         VARCHAR(10),
    domicilio              VARCHAR(512),

    creada_recientemente   BOOLEAN       DEFAULT FALSE,
    concentracion_alta     BOOLEAN       DEFAULT FALSE,

    created_at             TIMESTAMPTZ   DEFAULT NOW() NOT NULL,
    updated_at             TIMESTAMPTZ   DEFAULT NOW() NOT NULL
);

DROP TRIGGER IF EXISTS trg_empresas_updated_at ON empresas;
CREATE TRIGGER trg_empresas_updated_at
    BEFORE UPDATE ON empresas
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_emp_ruc
    ON empresas(ruc);
CREATE INDEX IF NOT EXISTS idx_emp_creada_recientemente
    ON empresas(creada_recientemente);
CREATE INDEX IF NOT EXISTS idx_emp_nombre_trgm
    ON empresas USING GIN (nombre_razon_social gin_trgm_ops);

-- ── Tabla: contratos ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS contratos (
    id                    SERIAL PRIMARY KEY,
    osce_id               VARCHAR(50)   UNIQUE NOT NULL,
    titulo                VARCHAR(500)  NOT NULL,
    descripcion           TEXT,

    entidad_contratante   VARCHAR(255)  NOT NULL,
    entidad_ruc           VARCHAR(11),

    -- FKs: responsable (funcionario) y proveedor (empresa)
    responsable_id        INTEGER       REFERENCES funcionarios(id) ON DELETE SET NULL,
    proveedor_id          INTEGER       REFERENCES empresas(id)     ON DELETE SET NULL,

    monto                 FLOAT         NOT NULL,
    moneda                VARCHAR(3)    DEFAULT 'PEN',
    presupuesto_base      FLOAT,

    tipo_proceso          VARCHAR(50)   NOT NULL,
    estado                VARCHAR(50)   NOT NULL,

    fecha_publicacion     TIMESTAMPTZ   NOT NULL,
    fecha_inicio          TIMESTAMPTZ,
    fecha_fin             TIMESTAMPTZ,

    -- Flags de alerta (calculados por IER Layer 1)
    empresa_nueva         BOOLEAN       DEFAULT FALSE,
    monto_anomalo         BOOLEAN       DEFAULT FALSE,
    proceso_exonerado     BOOLEAN       DEFAULT FALSE,

    datos_osce_json       TEXT,

    created_at            TIMESTAMPTZ   DEFAULT NOW() NOT NULL,
    updated_at            TIMESTAMPTZ   DEFAULT NOW() NOT NULL
);

DROP TRIGGER IF EXISTS trg_contratos_updated_at ON contratos;
CREATE TRIGGER trg_contratos_updated_at
    BEFORE UPDATE ON contratos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_con_responsable  ON contratos(responsable_id);
CREATE INDEX IF NOT EXISTS idx_con_proveedor    ON contratos(proveedor_id);
CREATE INDEX IF NOT EXISTS idx_con_fecha        ON contratos(fecha_publicacion DESC);
CREATE INDEX IF NOT EXISTS idx_con_monto        ON contratos(monto DESC);
CREATE INDEX IF NOT EXISTS idx_con_tipo_estado  ON contratos(tipo_proceso, estado);

-- ── Tabla: procesos ──────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS procesos (
    id                  SERIAL PRIMARY KEY,
    numero_expediente   VARCHAR(50)   UNIQUE NOT NULL,
    juzgado             VARCHAR(255)  NOT NULL,

    acusado_id          INTEGER       REFERENCES funcionarios(id) ON DELETE SET NULL,
    acusado_nombre      VARCHAR(255),

    delito_imputado     VARCHAR(500)  NOT NULL,
    estado              VARCHAR(50)   NOT NULL,

    fecha_inicio        TIMESTAMPTZ   NOT NULL,
    fecha_sentencia     TIMESTAMPTZ,

    resultado           VARCHAR(255),
    pena_anos           INTEGER,

    fuente              VARCHAR(50)   DEFAULT 'poder_judicial',
    url_fuente          VARCHAR(512),

    created_at          TIMESTAMPTZ   DEFAULT NOW() NOT NULL,
    updated_at          TIMESTAMPTZ   DEFAULT NOW() NOT NULL
);

DROP TRIGGER IF EXISTS trg_procesos_updated_at ON procesos;
CREATE TRIGGER trg_procesos_updated_at
    BEFORE UPDATE ON procesos
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_proc_acusado   ON procesos(acusado_id);
CREATE INDEX IF NOT EXISTS idx_proc_estado    ON procesos(estado);
CREATE INDEX IF NOT EXISTS idx_proc_delito    ON procesos(delito_imputado);

-- ── Tabla: conexiones ────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS conexiones (
    id           SERIAL PRIMARY KEY,
    origen_id    INTEGER     NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
    destino_id   INTEGER     NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
    tipo         VARCHAR(50) NOT NULL,
    fortaleza    FLOAT       DEFAULT 0.5,
    evidencia    TEXT,
    fuente       VARCHAR(255),

    created_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at   TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

DROP TRIGGER IF EXISTS trg_conexiones_updated_at ON conexiones;
CREATE TRIGGER trg_conexiones_updated_at
    BEFORE UPDATE ON conexiones
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE INDEX IF NOT EXISTS idx_cnx_origen   ON conexiones(origen_id);
CREATE INDEX IF NOT EXISTS idx_cnx_destino  ON conexiones(destino_id);
CREATE INDEX IF NOT EXISTS idx_cnx_tipo     ON conexiones(tipo);

-- ── Tabla: user_profiles (usuarios de la plataforma) ─────────────────────────
-- auth_user_id referencia auth.users.id de Supabase Auth
-- Las queries de negocio NO usan auth.users directamente

CREATE TABLE IF NOT EXISTS user_profiles (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    auth_user_id    UUID        UNIQUE NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    email           TEXT        NOT NULL,
    plan            VARCHAR(10) DEFAULT 'free' CHECK (plan IN ('free', 'pro')),

    -- Contadores de uso para rate limiting (DEC-009)
    consultas_hoy   INTEGER     DEFAULT 0,
    consultas_mes   INTEGER     DEFAULT 0,

    created_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at      TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

DROP TRIGGER IF EXISTS trg_user_profiles_updated_at ON user_profiles;
CREATE TRIGGER trg_user_profiles_updated_at
    BEFORE UPDATE ON user_profiles
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ── RLS: solo user_profiles tiene RLS (datos privados del usuario) ───────────
-- Las tablas públicas (funcionarios, contratos, etc.) son datos abiertos del Estado

ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "user_profiles: select own" ON user_profiles;
CREATE POLICY "user_profiles: select own"
    ON user_profiles FOR SELECT
    USING (auth.uid() = auth_user_id);

DROP POLICY IF EXISTS "user_profiles: update own" ON user_profiles;
CREATE POLICY "user_profiles: update own"
    ON user_profiles FOR UPDATE
    USING (auth.uid() = auth_user_id)
    WITH CHECK (auth.uid() = auth_user_id);

DROP POLICY IF EXISTS "user_profiles: insert own" ON user_profiles;
CREATE POLICY "user_profiles: insert own"
    ON user_profiles FOR INSERT
    WITH CHECK (auth.uid() = auth_user_id);

-- Service role bypass (para el backend con SUPABASE_SERVICE_KEY)
DROP POLICY IF EXISTS "user_profiles: service role" ON user_profiles;
CREATE POLICY "user_profiles: service role"
    ON user_profiles
    USING (auth.role() = 'service_role');

-- ── Función: auto-crear perfil al registrarse ─────────────────────────────────

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.user_profiles (auth_user_id, email)
    VALUES (NEW.id, NEW.email)
    ON CONFLICT (auth_user_id) DO NOTHING;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ── Verificación final ───────────────────────────────────────────────────────

DO $$
DECLARE
    t TEXT;
    tables TEXT[] := ARRAY['funcionarios','empresas','contratos','procesos','conexiones','user_profiles'];
BEGIN
    FOREACH t IN ARRAY tables LOOP
        IF NOT EXISTS (SELECT FROM information_schema.tables WHERE table_name = t) THEN
            RAISE EXCEPTION 'Tabla % no fue creada', t;
        END IF;
    END LOOP;
    RAISE NOTICE '✅ Schema Garendil creado correctamente (6 tablas)';
END $$;
