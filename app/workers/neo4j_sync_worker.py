import logging
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Funcionario, Contrato
from app.services.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


class Neo4jSyncWorker:
    """Background worker que sincroniza datos a Neo4j sin bloquear la API."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def sync_funcionarios(self) -> int:
        result = await self.db.execute(select(Funcionario))
        funcionarios = result.scalars().all()
        synced = 0

        async with Neo4jClient() as neo4j:
            for func in funcionarios:
                try:
                    ok = await neo4j.create_funcionario_node(
                        dni=func.dni,
                        nombre=func.nombre_completo,
                        score_ier=func.score_ier or 0.0,
                    )
                    if ok:
                        synced += 1
                except Exception as e:
                    logger.error(f"Error syncing {func.dni}: {e}")

        await self.db.commit()
        logger.info(f"Sincronizados {synced}/{len(funcionarios)} funcionarios a Neo4j")
        return synced

    async def sync_contratos(self) -> int:
        result = await self.db.execute(select(Contrato))
        contratos = result.scalars().all()
        synced = 0

        async with Neo4jClient() as neo4j:
            for contrato in contratos:
                try:
                    if contrato.responsable and contrato.proveedor:
                        ok = await neo4j.create_contrata_relationship(
                            dni_funcionario=contrato.responsable.dni,
                            ruc_empresa=contrato.proveedor.ruc,
                            monto=contrato.monto,
                            contrato_id=contrato.osce_id,
                        )
                        if ok:
                            synced += 1
                except Exception as e:
                    logger.error(f"Error syncing contrato {contrato.osce_id}: {e}")

        logger.info(f"Sincronizados {synced}/{len(contratos)} contratos a Neo4j")
        return synced
