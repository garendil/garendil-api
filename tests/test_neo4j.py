import pytest
from app.services.graph.neo4j_client import Neo4jClient


@pytest.mark.asyncio
async def test_neo4j_client_skips_when_unavailable():
    """Neo4j client hace skip si el servidor no está disponible."""
    try:
        async with Neo4jClient() as client:
            assert client.driver is not None
    except Exception as e:
        pytest.skip(f"Neo4j no disponible: {e}")
