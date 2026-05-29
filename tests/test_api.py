import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from app.main import app
from app.db.base import Base, get_db

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async def override_get_db():
        async with async_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield async_session
    app.dependency_overrides.clear()
    await engine.dispose()


@pytest.fixture
async def client(test_db):
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_health_check(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_stats_endpoint(client):
    response = await client.get("/api/stats")
    assert response.status_code == 200
    data = response.json()
    assert "funcionarios_analizados" in data
    assert "contratos_indexados" in data


@pytest.mark.asyncio
async def test_search_empty(client):
    response = await client.get("/api/search?q=test")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["resultados"] == []


@pytest.mark.asyncio
async def test_search_dni_invalid(client):
    response = await client.get("/api/search?dni=123")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_perfil_not_found(client):
    response = await client.get("/api/perfil/12345678")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_perfil_dni_invalid(client):
    response = await client.get("/api/perfil/abc")
    assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
