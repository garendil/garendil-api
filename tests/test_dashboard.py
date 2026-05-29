import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_dashboard_resumen(client: AsyncClient):
    response = await client.get("/api/dashboard/resumen")
    assert response.status_code == 200
    data = response.json()
    assert "total_funcionarios" in data
    assert "total_contratos" in data
    assert "pct_riesgo" in data


@pytest.mark.asyncio
async def test_dashboard_riesgo_top(client: AsyncClient):
    response = await client.get("/api/dashboard/riesgo-top?limit=10")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_dashboard_tendencias(client: AsyncClient):
    response = await client.get("/api/dashboard/tendencias")
    assert response.status_code == 200
    data = response.json()
    assert "tendencias" in data


@pytest.mark.asyncio
async def test_dashboard_alertas(client: AsyncClient):
    response = await client.get("/api/dashboard/alertas")
    assert response.status_code == 200
    data = response.json()
    assert "alertas_activas" in data
