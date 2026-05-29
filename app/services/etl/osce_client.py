import httpx
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class OSCEClient:
    BASE_URL = "https://api.osce.go.pe"
    API_KEY = os.getenv("OSCE_API_KEY", "demo")

    def __init__(self):
        self.client: Optional[httpx.AsyncClient] = None
        self.rate_limit_reset = 0.0

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers={"Authorization": f"Bearer {self.API_KEY}"},
            timeout=30.0
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def get_contratos(
        self,
        page: int = 1,
        per_page: int = 100,
        estado: Optional[str] = None,
        fecha_desde: Optional[str] = None,
        fecha_hasta: Optional[str] = None,
    ) -> Dict[str, Any]:
        if datetime.now().timestamp() < self.rate_limit_reset:
            wait_time = self.rate_limit_reset - datetime.now().timestamp()
            logger.warning(f"[osce] Rate limit: esperando {wait_time:.1f}s")
            await asyncio.sleep(wait_time + 1)

        params: Dict[str, Any] = {"page": page, "per_page": min(per_page, 1000)}
        if estado:
            params["estado"] = estado
        if fecha_desde:
            params["fecha_desde"] = fecha_desde
        if fecha_hasta:
            params["fecha_hasta"] = fecha_hasta

        try:
            assert self.client is not None
            response = await self.client.get("/contratos", params=params)
            response.raise_for_status()

            remaining = response.headers.get("X-RateLimit-Remaining", 100)
            reset = response.headers.get("X-RateLimit-Reset")
            if reset:
                self.rate_limit_reset = float(reset)

            logger.info(f"[osce] page={page}, remaining={remaining}")
            return response.json()

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                self.rate_limit_reset = datetime.now().timestamp() + 60
                logger.error("[osce] Rate limited: esperar 60s")
            elif e.response.status_code == 401:
                logger.error("[osce] API Key inválida")
            else:
                logger.error(f"[osce] HTTP error: {e}")
            raise
        except Exception as e:
            logger.error(f"[osce] Error: {e}")
            raise

    async def get_contratos_batch(
        self,
        total_pages: Optional[int] = None,
        estado: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        page = 1
        pages_fetched = 0

        while True:
            data = await self.get_contratos(page=page, per_page=1000, estado=estado)

            for contrato in data.get("data", []):
                yield contrato

            pages_fetched += 1
            pagination = data.get("pagination", {})
            if not data.get("data") or page >= pagination.get("total_pages", page):
                break
            if total_pages and pages_fetched >= total_pages:
                break

            page += 1
            await asyncio.sleep(1)
