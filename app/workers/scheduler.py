import asyncio
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.db.base import AsyncSessionLocal
from app.services.etl.osce_ingester import OSCEIngester

logger = logging.getLogger(__name__)


async def sync_osce_contratos():
    print(f"[WORKER] Iniciando sync OSCE @ {datetime.now().isoformat()}")

    async with AsyncSessionLocal() as db:
        ingester = OSCEIngester(db)
        stats = await ingester.ingest_contratos(dias_atras=1, limit_pages=5)

    print(f"[WORKER] Sync completada: insertados={stats['insertados']} errores={stats['errores']} dur={stats['duracion_segundos']:.1f}s")


def start_scheduler() -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    scheduler.add_job(
        sync_osce_contratos,
        trigger="cron",
        hour=2,
        minute=0,
        id="sync_osce_daily",
    )

    logger.info("[scheduler] Scheduler iniciado")
    return scheduler


if __name__ == "__main__":
    asyncio.run(sync_osce_contratos())
