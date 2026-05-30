"""
Cliente supabase-py — SOLO para auth y storage.
Las queries de negocio usan SQLAlchemy + asyncpg directamente.
"""
import os
from supabase import create_client, Client

_client: Client | None = None


def get_supabase_client() -> Client:
    """Singleton. Usa SUPABASE_SERVICE_KEY para operaciones server-side."""
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_KEY"]
        _client = create_client(url, key)
    return _client
