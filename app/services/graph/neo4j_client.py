import os
from neo4j import AsyncGraphDatabase
from neo4j.exceptions import Neo4jError
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Cliente async para Neo4j graph database."""

    def __init__(self):
        self.uri = os.getenv("NEO4J_URL", "neo4j://localhost:7687")
        self.user = os.getenv("NEO4J_USERNAME", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "dev")
        self.driver = None

    async def __aenter__(self):
        self.driver = AsyncGraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password),
        )
        logger.info(f"Conectado a Neo4j: {self.uri}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.driver:
            await self.driver.close()
            logger.info("Desconectado de Neo4j")

    async def create_funcionario_node(self, dni: str, nombre: str, score_ier: float) -> bool:
        try:
            async with self.driver.session() as session:
                await session.execute_write(
                    self._create_funcionario_tx, dni=dni, nombre=nombre, score_ier=score_ier
                )
            return True
        except Neo4jError as e:
            logger.error(f"Neo4j error creando funcionario {dni}: {e}")
            return False

    @staticmethod
    async def _create_funcionario_tx(tx, dni: str, nombre: str, score_ier: float):
        query = """
        MERGE (f:Funcionario {dni: $dni})
        SET f.nombre = $nombre,
            f.score_ier = $score_ier,
            f.updated_at = timestamp()
        RETURN f
        """
        await tx.run(query, dni=dni, nombre=nombre, score_ier=score_ier)

    async def create_empresa_node(self, ruc: str, nombre: str, estado: str = "activa") -> bool:
        try:
            async with self.driver.session() as session:
                await session.execute_write(
                    self._create_empresa_tx, ruc=ruc, nombre=nombre, estado=estado
                )
            return True
        except Neo4jError as e:
            logger.error(f"Neo4j error creando empresa {ruc}: {e}")
            return False

    @staticmethod
    async def _create_empresa_tx(tx, ruc: str, nombre: str, estado: str):
        query = """
        MERGE (e:Empresa {ruc: $ruc})
        SET e.nombre = $nombre,
            e.estado = $estado,
            e.updated_at = timestamp()
        RETURN e
        """
        await tx.run(query, ruc=ruc, nombre=nombre, estado=estado)

    async def create_contrata_relationship(
        self,
        dni_funcionario: str,
        ruc_empresa: str,
        monto: float,
        contrato_id: str,
    ) -> bool:
        try:
            async with self.driver.session() as session:
                await session.execute_write(
                    self._create_contrata_tx,
                    dni_func=dni_funcionario,
                    ruc_emp=ruc_empresa,
                    monto=monto,
                    contrato_id=contrato_id,
                )
            return True
        except Neo4jError as e:
            logger.error(f"Neo4j error creando relación contrato {contrato_id}: {e}")
            return False

    @staticmethod
    async def _create_contrata_tx(
        tx, dni_func: str, ruc_emp: str, monto: float, contrato_id: str
    ):
        query = """
        MATCH (f:Funcionario {dni: $dni_func})
        MATCH (e:Empresa {ruc: $ruc_emp})
        MERGE (f)-[r:CONTRATA {contrato_id: $contrato_id}]->(e)
        SET r.monto = $monto,
            r.updated_at = timestamp()
        RETURN r
        """
        await tx.run(query, dni_func=dni_func, ruc_emp=ruc_emp, monto=monto, contrato_id=contrato_id)

    async def get_conexiones(self, dni: str, profundidad: int = 2) -> Dict[str, Any]:
        """Retorna {nodos, aristas} del entorno de un funcionario hasta `profundidad` saltos."""
        try:
            async with self.driver.session() as session:
                result = await session.execute_read(
                    self._get_grafo_conexiones_tx, dni=dni, profundidad=profundidad
                )
                return result
        except Neo4jError as e:
            logger.error(f"Neo4j error obteniendo conexiones para {dni}: {e}")
            return {"nodos": [], "aristas": []}

    @staticmethod
    async def _get_grafo_conexiones_tx(tx, dni: str, profundidad: int) -> Dict[str, Any]:
        query = f"""
        MATCH (f:Funcionario {{dni: $dni}})
        MATCH (f)-[r*1..{profundidad}]-(conectado)
        RETURN DISTINCT f, r, conectado
        LIMIT 100
        """
        result = await tx.run(query, dni=dni)

        nodos: set = set()
        aristas: List[Dict] = []

        async for record in result:
            if record.get("f"):
                f = record["f"]
                nodos.add((f.element_id, "Funcionario", f.get("nombre", "?")))
            if record.get("conectado"):
                c = record["conectado"]
                nodos.add((c.element_id, list(c.labels)[0] if c.labels else "?", c.get("nombre", "?")))
            if record.get("r"):
                for rel in record["r"]:
                    aristas.append(
                        {
                            "from": rel.start_node.element_id,
                            "to": rel.end_node.element_id,
                            "type": rel.type,
                            "monto": rel.get("monto"),
                        }
                    )

        return {
            "nodos": [{"id": n[0], "label": n[2], "type": n[1]} for n in nodos],
            "aristas": aristas,
        }

    async def get_redes_conexion(self) -> Dict[str, Any]:
        """Top funcionarios por volumen de empresas contratadas (detección de redes)."""
        try:
            async with self.driver.session() as session:
                result = await session.execute_read(self._get_redes_tx)
                return result
        except Neo4jError as e:
            logger.error(f"Neo4j error obteniendo redes: {e}")
            return {"redes": []}

    @staticmethod
    async def _get_redes_tx(tx) -> Dict[str, Any]:
        query = """
        MATCH (f:Funcionario)-[r:CONTRATA]->(e:Empresa)
        WITH f, COUNT(DISTINCT e) AS num_empresas, SUM(r.monto) AS monto_total
        WHERE num_empresas > 5
        RETURN f.dni AS dni, f.nombre AS nombre, num_empresas, monto_total
        ORDER BY monto_total DESC
        LIMIT 20
        """
        result = await tx.run(query)

        redes = []
        async for record in result:
            redes.append(
                {
                    "dni": record["dni"],
                    "nombre": record["nombre"],
                    "empresas_frecuentes": record["num_empresas"],
                    "monto_total": record["monto_total"],
                }
            )
        return {"redes": redes}
