-- Migración 001: Crear tablas iniciales
BEGIN;

CREATE TABLE IF NOT EXISTS funcionarios (
    id SERIAL PRIMARY KEY,
    dni VARCHAR(8) UNIQUE NOT NULL,
    nombre_completo VARCHAR(255) NOT NULL,
    cargo_actual VARCHAR(255),
    institucion VARCHAR(255),
    score_ier FLOAT DEFAULT 0.0,
    score_competencia FLOAT DEFAULT 0.0,
    score_adecuacion FLOAT DEFAULT 0.0,
    foto_url VARCHAR(512),
    descripcion TEXT,
    verificado BOOLEAN DEFAULT FALSE,
    activo BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_funcionario_dni ON funcionarios(dni);
CREATE INDEX IF NOT EXISTS idx_funcionario_nombre ON funcionarios(nombre_completo);
CREATE INDEX IF NOT EXISTS idx_funcionario_institucion ON funcionarios(institucion);
CREATE INDEX IF NOT EXISTS idx_funcionario_score ON funcionarios(score_ier);

CREATE TABLE IF NOT EXISTS empresas (
    id SERIAL PRIMARY KEY,
    ruc VARCHAR(11) UNIQUE NOT NULL,
    nombre_razon_social VARCHAR(255) NOT NULL,
    estado VARCHAR(50),
    fecha_creacion VARCHAR(10),
    domicilio VARCHAR(512),
    creada_recientemente BOOLEAN DEFAULT FALSE,
    concentracion_alta BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_empresa_ruc ON empresas(ruc);
CREATE INDEX IF NOT EXISTS idx_empresa_nombre ON empresas(nombre_razon_social);
CREATE INDEX IF NOT EXISTS idx_empresa_creada_recientemente ON empresas(creada_recientemente);

CREATE TABLE IF NOT EXISTS contratos (
    id SERIAL PRIMARY KEY,
    osce_id VARCHAR(50) UNIQUE NOT NULL,
    titulo VARCHAR(500) NOT NULL,
    descripcion TEXT,
    entidad_contratante VARCHAR(255) NOT NULL,
    entidad_ruc VARCHAR(11),
    responsable_id INTEGER REFERENCES funcionarios(id) ON DELETE SET NULL,
    proveedor_id INTEGER REFERENCES empresas(id) ON DELETE SET NULL,
    monto FLOAT NOT NULL,
    moneda VARCHAR(3) DEFAULT 'PEN',
    presupuesto_base FLOAT,
    tipo_proceso VARCHAR(50) NOT NULL,
    estado VARCHAR(50) NOT NULL,
    fecha_publicacion TIMESTAMP NOT NULL,
    fecha_inicio TIMESTAMP,
    fecha_fin TIMESTAMP,
    empresa_nueva BOOLEAN DEFAULT FALSE,
    monto_anomalo BOOLEAN DEFAULT FALSE,
    proceso_exonerado BOOLEAN DEFAULT FALSE,
    datos_osce_json TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_contrato_osce_id ON contratos(osce_id);
CREATE INDEX IF NOT EXISTS idx_contrato_responsable ON contratos(responsable_id);
CREATE INDEX IF NOT EXISTS idx_contrato_proveedor ON contratos(proveedor_id);
CREATE INDEX IF NOT EXISTS idx_contrato_fecha ON contratos(fecha_publicacion);
CREATE INDEX IF NOT EXISTS idx_contrato_monto ON contratos(monto);

CREATE TABLE IF NOT EXISTS procesos (
    id SERIAL PRIMARY KEY,
    numero_expediente VARCHAR(50) UNIQUE NOT NULL,
    juzgado VARCHAR(255) NOT NULL,
    acusado_id INTEGER REFERENCES funcionarios(id) ON DELETE SET NULL,
    acusado_nombre VARCHAR(255),
    delito_imputado VARCHAR(500) NOT NULL,
    estado VARCHAR(50) NOT NULL,
    fecha_inicio TIMESTAMP NOT NULL,
    fecha_sentencia TIMESTAMP,
    resultado VARCHAR(255),
    pena_anos INTEGER,
    fuente VARCHAR(50) DEFAULT 'poder_judicial',
    url_fuente VARCHAR(512),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_proceso_expediente ON procesos(numero_expediente);
CREATE INDEX IF NOT EXISTS idx_proceso_acusado ON procesos(acusado_id);
CREATE INDEX IF NOT EXISTS idx_proceso_estado ON procesos(estado);

CREATE TABLE IF NOT EXISTS conexiones (
    id SERIAL PRIMARY KEY,
    origen_id INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
    destino_id INTEGER NOT NULL REFERENCES funcionarios(id) ON DELETE CASCADE,
    tipo VARCHAR(50) NOT NULL,
    fortaleza FLOAT DEFAULT 0.5,
    evidencia TEXT,
    fuente VARCHAR(255),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conexion_origen_destino ON conexiones(origen_id, destino_id);
CREATE INDEX IF NOT EXISTS idx_conexion_tipo ON conexiones(tipo);

COMMIT;
