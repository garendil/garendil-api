import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import Funcionario, Empresa, Contrato
from app.services.etl.osce_client import OSCEClient

logger = logging.getLogger(__name__)

class OSCEIngester:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def ingest_contratos(
        self,
        dias_atras: int = 30,
        limit_pages: Optional[int] = None,
    ) -> dict:
        stats = {
            "insertados": 0,
            "actualizados": 0,
            "errores": 0,
            "total": 0,
            "tiempo_inicio": datetime.now(),
        }

        try:
            async with OSCEClient() as client:
                async for contrato_raw in client.get_contratos_batch(
                    total_pages=limit_pages,
                    estado="completado",
                ):
                    try:
                        await self._procesar_contrato(contrato_raw)
                        stats["insertados"] += 1
                    except Exception as e:
                        logger.error(f"[ingester] Error procesando contrato: {e}")
                        stats["errores"] += 1
                    stats["total"] += 1
                    if stats["total"] % 100 == 0:
                        logger.info(f"[ingester] Progreso: {stats['total']} contratos")

            await self.db.commit()

        except Exception as e:
            logger.error(f"[ingester] Error en ingesta: {e}")
            await self.db.rollback()
            stats["errores"] += 1

        stats["tiempo_final"] = datetime.now()
        stats["duracion_segundos"] = (
            stats["tiempo_final"] - stats["tiempo_inicio"]
        ).total_seconds()
        return stats

    async def _procesar_contrato(self, contrato_raw: dict):
        osce_id = contrato_raw.get("id")
        responsable_dni = contrato_raw.get("proveedor", {}).get("responsable_dni")
        proveedor_ruc = contrato_raw.get("proveedor", {}).get("ruc")

        funcionario = None
        if responsable_dni:
            result = await self.db.execute(
                select(Funcionario).where(Funcionario.dni == responsable_dni)
            )
            funcionario = result.scalar_one_or_none()
            if not funcionario:
                funcionario = Funcionario(
                    dni=responsable_dni,
                    nombre_completo=contrato_raw.get("proveedor", {}).get("nombre", "Desconocido"),
                    institucion=contrato_raw.get("entidad_contratante", {}).get("nombre"),
                    score_ier=0.0,
                )
                self.db.add(funcionario)
                await self.db.flush()

        empresa = None
        if proveedor_ruc:
            result = await self.db.execute(
                select(Empresa).where(Empresa.ruc == proveedor_ruc)
            )
            empresa = result.scalar_one_or_none()
            if not empresa:
                empresa = Empresa(
                    ruc=proveedor_ruc,
                    nombre_razon_social=contrato_raw.get("proveedor", {}).get("nombre", "Desconocido"),
                    estado="activa",
                    fecha_creacion=contrato_raw.get("proveedor", {}).get("fecha_creacion"),
                )
                self.db.add(empresa)
                await self.db.flush()

        result = await self.db.execute(
            select(Contrato).where(Contrato.osce_id == osce_id)
        )
        contrato_existente = result.scalar_one_or_none()

        if contrato_existente:
            contrato_existente.titulo = contrato_raw.get("titulo")
            contrato_existente.descripcion = contrato_raw.get("descripcion")
            contrato_existente.monto = float(contrato_raw.get("monto", 0))
            contrato_existente.estado = contrato_raw.get("estado", "activo")
            contrato_existente.datos_osce_json = json.dumps(contrato_raw)
        else:
            contrato = Contrato(
                osce_id=osce_id,
                titulo=contrato_raw.get("titulo"),
                descripcion=contrato_raw.get("descripcion"),
                entidad_contratante=contrato_raw.get("entidad_contratante", {}).get("nombre", "Desconocido"),
                entidad_ruc=contrato_raw.get("entidad_contratante", {}).get("ruc"),
                responsable_id=funcionario.id if funcionario else None,
                proveedor_id=empresa.id if empresa else None,
                monto=float(contrato_raw.get("monto", 0)),
                moneda=contrato_raw.get("moneda", "PEN"),
                presupuesto_base=float(contrato_raw["presupuesto_base"]) if contrato_raw.get("presupuesto_base") else None,
                tipo_proceso=contrato_raw.get("tipo_proceso", "licitacion_publica"),
                estado=contrato_raw.get("estado", "activo"),
                fecha_publicacion=datetime.fromisoformat(
                    contrato_raw.get("fecha_publicacion", datetime.now().isoformat())
                ),
                fecha_inicio=datetime.fromisoformat(contrato_raw["fecha_inicio"]) if contrato_raw.get("fecha_inicio") else None,
                fecha_fin=datetime.fromisoformat(contrato_raw["fecha_fin"]) if contrato_raw.get("fecha_fin") else None,
                datos_osce_json=json.dumps(contrato_raw),
            )
            await self._aplicar_flags_layer1(contrato, empresa)
            self.db.add(contrato)

    async def _aplicar_flags_layer1(self, contrato: Contrato, empresa: Optional[Empresa]):
        if empresa and empresa.fecha_creacion:
            fecha_creacion = datetime.strptime(empresa.fecha_creacion, "%Y-%m-%d")
            if (datetime.now() - fecha_creacion).days < 30:
                contrato.empresa_nueva = True
                empresa.creada_recientemente = True

        if contrato.presupuesto_base and contrato.monto > 0:
            exceso_pct = ((contrato.monto - contrato.presupuesto_base) / contrato.presupuesto_base) * 100
            if exceso_pct > 20:
                contrato.monto_anomalo = True

        if contrato.tipo_proceso == "exoneración":
            contrato.proceso_exonerado = True
