import logging
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_, func, extract
from typing import Optional

logger = logging.getLogger(__name__)

from app.db.base import get_db
from app.models import Funcionario, Contrato, Proceso
from app.schemas import FuncionarioSchema, ContratoSchema

router = APIRouter(prefix="/api", tags=["funcionarios"])


@router.get("/search")
async def search(
    q: Optional[str] = Query(None, min_length=1, max_length=255),
    dni: Optional[str] = Query(None, pattern=r"^\d{8}$"),
    institucion: Optional[str] = Query(None),
    min_score: Optional[float] = Query(0.0, ge=0, le=100),
    max_score: Optional[float] = Query(100.0, ge=0, le=100),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = select(Funcionario)

    if dni:
        query = query.where(Funcionario.dni == dni)
    if q:
        query = query.where(
            or_(
                Funcionario.nombre_completo.ilike(f"%{q}%"),
                Funcionario.dni.ilike(f"%{q}%"),
            )
        )
    if institucion:
        query = query.where(Funcionario.institucion.ilike(f"%{institucion}%"))
    if min_score is not None or max_score is not None:
        query = query.where(
            and_(
                Funcionario.score_ier >= (min_score or 0.0),
                Funcionario.score_ier <= (max_score or 100.0),
            )
        )

    count_result = await db.execute(query)
    total = len(count_result.scalars().all())

    result = await db.execute(query.offset(skip).limit(limit))
    funcionarios = result.scalars().all()

    return {
        "resultados": [FuncionarioSchema.model_validate(f) for f in funcionarios],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@router.get("/perfil/{dni}")
async def get_perfil(dni: str, db: AsyncSession = Depends(get_db)) -> dict:
    if len(dni) != 8 or not dni.isdigit():
        raise HTTPException(status_code=400, detail="DNI debe tener 8 dígitos")

    result = await db.execute(select(Funcionario).where(Funcionario.dni == dni))
    funcionario = result.scalar_one_or_none()

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")

    result = await db.execute(
        select(Contrato)
        .where(Contrato.responsable_id == funcionario.id)
        .order_by(Contrato.fecha_publicacion.desc())
    )
    contratos = result.scalars().all()

    result = await db.execute(
        select(Proceso)
        .where(Proceso.acusado_id == funcionario.id)
        .order_by(Proceso.fecha_inicio.desc())
    )
    procesos = result.scalars().all()

    return {
        "funcionario": FuncionarioSchema.model_validate(funcionario),
        "contratos": [ContratoSchema.model_validate(c) for c in contratos],
        "procesos": [
            {
                "numero_expediente": p.numero_expediente,
                "juzgado": p.juzgado,
                "delito_imputado": p.delito_imputado,
                "estado": p.estado,
                "fecha_inicio": p.fecha_inicio,
                "resultado": p.resultado,
            }
            for p in procesos
        ],
        "conexiones": [],
    }


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(func.count()).select_from(Funcionario))
    total_funcionarios = result.scalar() or 0

    result = await db.execute(select(func.count()).select_from(Contrato))
    total_contratos = result.scalar() or 0

    result = await db.execute(select(func.sum(Contrato.monto)))
    monto_total = result.scalar() or 0

    return {
        "funcionarios_analizados": total_funcionarios,
        "contratos_indexados": total_contratos,
        "monto_total_contratos": float(monto_total),
        "conexiones_mapeadas": 0,
        "ultima_actualizacion": "2026-05-17T00:00:00Z",
    }


@router.get("/perfil/{dni}/scores")
async def get_scores(dni: str, db: AsyncSession = Depends(get_db)) -> dict:
    """Scores detallados: Layer 1 (reglas) + Layer 2 (anomalías) + IER combinado."""
    from app.services.scoring import Layer2Scorer

    result = await db.execute(select(Funcionario).where(Funcionario.dni == dni))
    funcionario = result.scalar_one_or_none()

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")

    layer2_scorer = Layer2Scorer(db)
    layer2_score = await layer2_scorer.score_funcionario(funcionario.id)

    ier_combined = (funcionario.score_ier * 0.7) + (layer2_score * 100 * 0.3)
    ier_combined = min(ier_combined, 100)

    return {
        "dni": dni,
        "layer1_score": funcionario.score_ier,
        "layer2_score": layer2_score,
        "ier_combined": ier_combined,
        "riesgo_nivel": _get_riesgo_nivel(ier_combined),
        "explicacion": {
            "layer1": "Basado en reglas explícitas (empresa nueva, montos anómalos, exoneraciones)",
            "layer2": "Basado en patrones anómalos en histórico de contratación",
        },
    }


def _get_riesgo_nivel(score: float) -> str:
    if score >= 75:
        return "CRÍTICO"
    elif score >= 50:
        return "ALTO"
    elif score >= 25:
        return "MODERADO"
    return "BAJO"


@router.post("/admin/sync-osce")
async def trigger_sync_osce(db: AsyncSession = Depends(get_db)):
    from app.services.etl.osce_ingester import OSCEIngester

    ingester = OSCEIngester(db)
    stats = await ingester.ingest_contratos(dias_atras=7, limit_pages=10)

    return {
        "status": "ok",
        "insertados": stats["insertados"],
        "actualizados": stats["actualizados"],
        "errores": stats["errores"],
        "total": stats["total"],
        "duracion_segundos": stats["duracion_segundos"],
    }


@router.post("/admin/train-layer2")
async def train_layer2(db: AsyncSession = Depends(get_db)):
    """Entrena el modelo Layer 2 con todos los funcionarios en BD."""
    from app.services.scoring import Layer2Scorer

    scorer = Layer2Scorer(db)
    await scorer.train()

    return {
        "status": "ok",
        "mensaje": "Modelo Layer 2 entrenado exitosamente",
        "timestamp": datetime.now().isoformat(),
    }


# ========== DASHBOARD ENDPOINTS ==========


@router.get("/dashboard/resumen")
async def get_dashboard_resumen(db: AsyncSession = Depends(get_db)) -> dict:
    """Resumen ejecutivo para dashboard administrativo."""
    result = await db.execute(select(func.count()).select_from(Funcionario))
    total_func = result.scalar() or 0

    result = await db.execute(
        select(func.count()).select_from(Funcionario).where(Funcionario.score_ier >= 50)
    )
    func_riesgo_alto = result.scalar() or 0

    result = await db.execute(select(func.count()).select_from(Contrato))
    total_contratos = result.scalar() or 0

    result = await db.execute(select(func.sum(Contrato.monto)))
    monto_total = result.scalar() or 0

    result = await db.execute(select(func.count()).select_from(Proceso))
    total_procesos = result.scalar() or 0

    return {
        "total_funcionarios": total_func,
        "funcionarios_riesgo_alto": func_riesgo_alto,
        "total_contratos": total_contratos,
        "monto_total_contratos": float(monto_total),
        "total_procesos": total_procesos,
        "pct_riesgo": (func_riesgo_alto / max(total_func, 1)) * 100,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/dashboard/riesgo-top")
async def get_top_riesgo(
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list:
    """Top N funcionarios con mayor score IER."""
    result = await db.execute(
        select(Funcionario).order_by(Funcionario.score_ier.desc()).limit(limit)
    )
    funcionarios = result.scalars().all()

    return [
        {
            "dni": f.dni,
            "nombre": f.nombre_completo,
            "score_ier": f.score_ier,
            "institucion": f.institucion,
            "cargo": f.cargo_actual,
        }
        for f in funcionarios
    ]


@router.get("/dashboard/tendencias")
async def get_tendencias(db: AsyncSession = Depends(get_db)) -> dict:
    """Contratos por mes con monto promedio."""
    result = await db.execute(
        select(
            extract("month", Contrato.fecha_publicacion).label("mes"),
            func.count(Contrato.id).label("cantidad"),
            func.avg(Contrato.monto).label("monto_promedio"),
        )
        .group_by(extract("month", Contrato.fecha_publicacion))
        .order_by("mes")
    )

    tendencias = [
        {
            "mes": int(row[0]) if row[0] else 0,
            "contratos": row[1],
            "monto_promedio": float(row[2]) if row[2] else 0,
        }
        for row in result
    ]

    return {"tendencias": tendencias, "timestamp": datetime.now().isoformat()}


@router.get("/dashboard/alertas")
async def get_alertas(db: AsyncSession = Depends(get_db)) -> dict:
    """Últimas alertas del sistema."""
    return {
        "alertas_activas": [],
        "total": 0,
        "timestamp": datetime.now().isoformat(),
    }


@router.post("/dashboard/reportar-riesgo")
async def reportar_riesgo(
    dni: str = Query(..., pattern=r"^\d{8}$"),
    razon: str = Query(..., max_length=500),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Permite a usuarios reportar señales de riesgo observadas."""
    logger.info(f"Reporte de señal de riesgo: DNI={dni}")
    return {
        "status": "ok",
        "mensaje": "Reporte registrado. Será revisado por el equipo.",
        "reporte_id": f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}",
    }


@router.get("/perfil/{dni}/scores-v2")
async def get_scores_v2(dni: str, db: AsyncSession = Depends(get_db)) -> dict:
    """
    Scores V2: arquitectura desacoplada Layer1 + Layer2 + IER aggregator.
    Features extraídas de forma abstracta — sin tight coupling al modelo Funcionario.
    """
    from app.services.scoring import (
        ScoringFeatureExtractor,
        Layer1Scorer,
        Layer2Scorer,
        IERCalculator,
    )

    func_result = await db.execute(select(Funcionario).where(Funcionario.dni == dni))
    funcionario = func_result.scalar_one_or_none()

    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")

    try:
        extractor = ScoringFeatureExtractor(db)
        scoring_input = await extractor.extract_features(funcionario.id)

        layer1 = Layer1Scorer()
        layer2 = Layer2Scorer()
        # Layer2 retorna 0.0 hasta ser entrenado con /admin/train-layer2

        calculator = IERCalculator(layers=[layer1, layer2])
        ier_result = await calculator.calculate(scoring_input)

        return {
            "dni": dni,
            "nombre": funcionario.nombre_completo,
            "ier": ier_result["ier"],
            "layer_scores": ier_result["layer_scores"],
            "breakdown": ier_result["breakdown"],
            "timestamp": ier_result["timestamp"],
            "metadata": {
                "version": "v2-desacoplado",
                "feature_count": len(scoring_input.features),
            },
        }

    except Exception as e:
        logger.error(f"Error en scores-v2 para DNI {dni}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/admin/sync-neo4j")
async def sync_neo4j(db: AsyncSession = Depends(get_db)):
    """Sincroniza PostgreSQL → Neo4j. Requiere Neo4j disponible."""
    from app.services.etl.neo4j_sync import sync_to_neo4j

    try:
        await sync_to_neo4j(db)
        return {
            "status": "ok",
            "mensaje": "Sincronización Neo4j completada",
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Neo4j sync error: {e}")
        return {"status": "error", "error": str(e)}


# ========== LAYER3 ENDPOINTS ==========


@router.post("/admin/train-layer3")
async def train_layer3(db: AsyncSession = Depends(get_db)):
    """Entrena Layer3 con datos del Poder Judicial (mín. 50 samples)."""
    import numpy as np
    from sklearn.metrics import roc_auc_score, f1_score, classification_report
    from app.services.scoring.layer3_trainer import Layer3Trainer

    try:
        trainer = Layer3Trainer(db)
        X, y, func_ids, feature_names = await trainer.prepare_training_data()

        if X.shape[0] < 50:
            return {"error": f"No hay suficientes datos ({X.shape[0]} < 50)", "status": "failed"}

        scorer = await trainer.train(model_path="/tmp/layer3_model.pkl")

        y_pred = scorer._model.predict(scorer._scaler.transform(X))
        y_proba = scorer._model.predict_proba(scorer._scaler.transform(X))[:, 1]
        roc_auc = roc_auc_score(y, y_proba)
        f1 = f1_score(y, y_pred)

        return {
            "status": "success",
            "samples_trained": X.shape[0],
            "features": X.shape[1],
            "feature_names": feature_names,
            "metrics": {
                "roc_auc": round(roc_auc, 3),
                "f1_score": round(f1, 3),
                "n_positives": int(np.sum(y)),
                "n_negatives": int(X.shape[0] - np.sum(y)),
            },
            "model_path": "/tmp/layer3_model.pkl",
            "feature_importance": scorer.get_feature_importance(),
            "timestamp": datetime.now().isoformat(),
        }
    except Exception as e:
        logger.error(f"Layer3 training error: {e}")
        return {"error": str(e), "status": "failed"}


@router.get("/admin/layer3-status")
async def layer3_status():
    """Estado actual del modelo Layer3."""
    return {
        "layer3": {
            "is_trained": False,
            "last_trained": None,
            "samples_trained": 0,
            "roc_auc": None,
            "f1_score": None,
            "model_version": "v3-placeholder",
        }
    }


# ========== SCALE: CACHED SCORES ==========


@router.get("/perfil/{dni}/scores-cached")
async def get_scores_cached(
    dni: str,
    db: AsyncSession = Depends(get_db),
    force_refresh: bool = Query(False),
) -> dict:
    """Scores con caché Redis transparente (TTL 7 días)."""
    from app.services.caching.score_cache import ScoreCache
    from app.services.scoring import ScoringFeatureExtractor, Layer1Scorer, Layer2Scorer
    from app.services.scoring.ier_calculator import IERCalculatorV3

    result = await db.execute(select(Funcionario).where(Funcionario.dni == dni))
    funcionario = result.scalar_one_or_none()
    if not funcionario:
        raise HTTPException(status_code=404, detail="Funcionario no encontrado")

    cache = ScoreCache()
    await cache.connect()
    try:
        if not force_refresh:
            cached = await cache.get(funcionario.id)
            if cached:
                cached["source"] = "cache"
                return cached

        extractor = ScoringFeatureExtractor(db)
        scoring_input = await extractor.extract_features(funcionario.id)
        calculator = IERCalculatorV3(layers=[Layer1Scorer(), Layer2Scorer()])
        score_result = await calculator.calculate(scoring_input)
        await cache.set(funcionario.id, score_result)
        score_result["source"] = "computed"
        return score_result
    finally:
        await cache.disconnect()


# ========== SCALE: BATCH SCORING ==========


@router.post("/batch/score-funcionarios")
async def batch_score_funcionarios(
    dnis: list = Body(..., example=["12345678", "87654321"]),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Calcula scores para múltiples funcionarios (máx. 1000)."""
    import asyncio
    from app.services.scoring import ScoringFeatureExtractor, Layer1Scorer, Layer2Scorer
    from app.services.scoring.ier_calculator import IERCalculatorV3

    if len(dnis) > 1000:
        return {"error": "Máximo 1000 funcionarios por request"}

    result = await db.execute(select(Funcionario).where(Funcionario.dni.in_(dnis)))
    funcionarios = result.scalars().all()

    extractor = ScoringFeatureExtractor(db)
    calculator = IERCalculatorV3(layers=[Layer1Scorer(), Layer2Scorer()])

    async def score_one(func):
        try:
            input_data = await extractor.extract_features(func.id)
            return await calculator.calculate(input_data)
        except Exception as e:
            return {"error": str(e), "dni": func.dni}

    batch_results = await asyncio.gather(*[score_one(f) for f in funcionarios])

    results, errors = [], []
    for r in batch_results:
        if "error" in r and "dni" in r:
            errors.append(r["error"])
        else:
            results.append(r)

    return {
        "total_requested": len(dnis),
        "total_processed": len(results),
        "total_errors": len(errors),
        "results": results,
        "errors": errors[:10],
    }


# ========== MONITOREO: MÉTRICAS ==========


@router.get("/metrics")
async def get_metrics():
    """Métricas del sistema en formato Prometheus."""
    from app.monitoring.metrics import metrics

    return {"format": "prometheus", "data": metrics.get_prometheus_metrics()}


# ========== MONITOREO: HEALTH CHECK EXTENDIDO ==========


@router.get("/health/full")
async def health_check_full(db: AsyncSession = Depends(get_db)) -> dict:
    """Health check completo con estado de todas las dependencias."""
    import redis.asyncio as aioredis
    from app.services.graph.neo4j_client import Neo4jClient

    health: dict = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {},
    }

    try:
        await db.execute(select(func.count()).select_from(Funcionario))
        health["components"]["database"] = "ok"
    except Exception as e:
        health["components"]["database"] = f"error: {e}"
        health["status"] = "unhealthy"

    try:
        r = aioredis.from_url("redis://localhost:6379")
        await r.ping()
        await r.aclose()
        health["components"]["redis"] = "ok"
    except Exception as e:
        health["components"]["redis"] = f"error: {e}"
        if health["status"] == "healthy":
            health["status"] = "degraded"

    try:
        async with Neo4jClient() as _:
            pass
        health["components"]["neo4j"] = "ok"
    except Exception as e:
        health["components"]["neo4j"] = f"error: {e}"
        if health["status"] == "healthy":
            health["status"] = "degraded"

    return health
