import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models import Funcionario, Empresa, Contrato
from app.services.graph.neo4j_client import Neo4jClient

logger = logging.getLogger(__name__)


async def sync_to_neo4j(db: AsyncSession):
    """
    Sincroniza datos de PostgreSQL a Neo4j.
    Ejecutar después de ingestar datos de OSCE.
    """
    async with Neo4jClient() as neo4j:
        result = await db.execute(select(Funcionario))
        funcionarios = result.scalars().all()

        for func in funcionarios:
            success = await neo4j.create_funcionario_node(
                dni=func.dni,
                nombre=func.nombre_completo,
                score_ier=func.score_ier,
            )
            if not success:
                logger.warning(f"Fallo creando nodo para {func.dni}")

        logger.info(f"Sincronizados {len(funcionarios)} funcionarios a Neo4j")

        result = await db.execute(select(Empresa))
        empresas = result.scalars().all()

        for emp in empresas:
            await neo4j.create_empresa_node(
                ruc=emp.ruc,
                nombre=emp.nombre_razon_social,
                estado=getattr(emp, "estado", "activa"),
            )

        logger.info(f"Sincronizadas {len(empresas)} empresas a Neo4j")

        result = await db.execute(select(Contrato))
        contratos = result.scalars().all()

        relacionados = 0
        for cont in contratos:
            if cont.responsable and cont.proveedor:
                success = await neo4j.create_contrata_relationship(
                    dni_funcionario=cont.responsable.dni,
                    ruc_empresa=cont.proveedor.ruc,
                    monto=cont.monto,
                    contrato_id=cont.osce_id or str(cont.id),
                )
                if success:
                    relacionados += 1

        logger.info(f"Creadas {relacionados} relaciones CONTRATA en Neo4j")
