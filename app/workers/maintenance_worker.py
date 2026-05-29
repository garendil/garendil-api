import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text

from app.models import Funcionario

logger = logging.getLogger(__name__)


class MaintenanceWorker:
    """Tareas de mantenimiento periódico (limpiar caché, actualizar stats, ANALYZE)."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def run_daily_maintenance(self) -> dict:
        logger.info("Iniciando mantenimiento diario...")
        results = {
            "cache_cleaned": await self.cleanup_expired_cache(),
            "stats_updated": await self.update_statistics(),
            "indexes_analyzed": await self.analyze_indexes(),
            "timestamp": datetime.now().isoformat(),
        }
        logger.info(f"Mantenimiento completado: {results}")
        return results

    async def cleanup_expired_cache(self) -> int:
        try:
            result = await self.db.execute(
                text("DELETE FROM scoring_cache WHERE expires_at < NOW()")
            )
            await self.db.commit()
            count = result.rowcount
            logger.info(f"Limpiado caché: {count} entradas expiradas")
            return count
        except Exception as e:
            logger.error(f"Error limpiando caché: {e}")
            return 0

    async def update_statistics(self) -> dict:
        try:
            result = await self.db.execute(select(Funcionario))
            funcionarios = result.scalars().all()
            total = len(funcionarios)
            riesgo_alto = sum(1 for f in funcionarios if f.score_ier and f.score_ier >= 50)
            logger.info(f"Stats: {total} funcionarios, {riesgo_alto} con riesgo alto")
            return {"total_funcionarios": total, "riesgo_alto": riesgo_alto}
        except Exception as e:
            logger.error(f"Error actualizando estadísticas: {e}")
            return {}

    async def analyze_indexes(self) -> bool:
        try:
            await self.db.execute(text("ANALYZE;"))
            await self.db.commit()
            logger.info("Índices analizados")
            return True
        except Exception as e:
            logger.error(f"Error analizando índices: {e}")
            return False
