import asyncio
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class MEFScraper:
    """Scraper para MEF Portal Transparencia"""

    BASE_URL = "https://www.portal.transparencia.gob.pe"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def scrape_patrimonio(self, dni: str) -> dict | None:
        """
        Scrape patrimonio de un funcionario desde MEF Transparencia.

        Returns dict with patrimonio_por_año and variacion_patrimonio,
        or None if funcionario not found or request fails.
        """
        try:
            search_url = f"{self.BASE_URL}/buscador/funcionario?dni={dni}"
            response = await self.client.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            detail_link = soup.find("a", class_="funcionario-link")
            if not detail_link:
                logger.warning(f"MEF: No se encontró funcionario con DNI {dni}")
                return None

            detail_url = f"{self.BASE_URL}{detail_link['href']}"
            detail_response = await self.client.get(detail_url)
            detail_soup = BeautifulSoup(detail_response.text, "html.parser")

            patrimonio_por_año: dict = {}
            table = detail_soup.find("table", class_="patrimonio")

            if table:
                rows = table.find_all("tr")[1:]
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 4:
                        año = cols[0].text.strip()
                        patrimonio_por_año[año] = {
                            "bienes_inmuebles": float(
                                cols[1].text.replace("S/.", "").replace(",", "")
                            ),
                            "bienes_muebles": float(
                                cols[2].text.replace("S/.", "").replace(",", "")
                            ),
                            "ingresos": float(
                                cols[3].text.replace("S/.", "").replace(",", "")
                            ),
                        }

            años = sorted(patrimonio_por_año.keys())
            variacion = 0.0
            if len(años) >= 2:
                último = (
                    patrimonio_por_año[años[-1]]["bienes_inmuebles"]
                    + patrimonio_por_año[años[-1]]["bienes_muebles"]
                )
                anterior = (
                    patrimonio_por_año[años[-2]]["bienes_inmuebles"]
                    + patrimonio_por_año[años[-2]]["bienes_muebles"]
                )
                if anterior > 0:
                    variacion = (último - anterior) / anterior

            await asyncio.sleep(2)

            return {
                "dni": dni,
                "patrimonio_por_año": patrimonio_por_año,
                "variacion_patrimonio": variacion,
            }

        except Exception as e:
            logger.error(f"MEF scraper error para DNI {dni}: {e}")
            return None


class INFOBRAScraper:
    """Scraper para INFOBRAS"""

    BASE_URL = "https://www.infobras.com.pe"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = None

    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()

    async def scrape_obras_por_responsable(self, dni: str) -> list:
        """
        Scrape obras públicas de un responsable desde INFOBRAS.

        Returns list of obra dicts with presupuesto, estado, and sobrecosto_pct.
        """
        try:
            url = f"{self.BASE_URL}/obras?responsable={dni}"
            response = await self.client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            obras = []
            obra_cards = soup.find_all("div", class_="obra-card")

            for card in obra_cards:
                try:
                    nombre = card.find("h3").text.strip()
                    presupuesto_aprobado = float(
                        card.find("p", class_="presupuesto-aprobado")
                        .text.replace("S/.", "")
                        .replace(",", "")
                    )
                    presupuesto_ejecutado = float(
                        card.find("p", class_="presupuesto-ejecutado")
                        .text.replace("S/.", "")
                        .replace(",", "")
                    )
                    estado = card.find("p", class_="estado").text.strip().lower()

                    sobrecosto_pct = (
                        (presupuesto_ejecutado - presupuesto_aprobado)
                        / presupuesto_aprobado
                        * 100
                        if presupuesto_aprobado > 0
                        else 0
                    )

                    obras.append(
                        {
                            "nombre": nombre,
                            "presupuesto_aprobado": presupuesto_aprobado,
                            "presupuesto_ejecutado": presupuesto_ejecutado,
                            "responsable_dni": dni,
                            "estado": estado,
                            "sobrecosto_pct": sobrecosto_pct,
                        }
                    )

                except Exception as e:
                    logger.warning(f"Error parsing obra card: {e}")
                    continue

            await asyncio.sleep(2)

            return obras

        except Exception as e:
            logger.error(f"INFOBRAS scraper error para DNI {dni}: {e}")
            return []
