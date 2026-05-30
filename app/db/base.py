from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
import os

# Supabase Transaction Pooler URL (port 6543).
# Formato: postgresql://postgres.[ref]:[password]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
# Fallback: Postgres local para desarrollo sin Supabase.
SUPABASE_DB_URL = os.getenv(
    "SUPABASE_DB_URL",
    "postgresql://dev:dev@localhost:5432/garendil_db",
)

Base = declarative_base()

_engine = None
_AsyncSessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        url = SUPABASE_DB_URL.replace("postgresql://", "postgresql+asyncpg://")
        _engine = create_async_engine(
            url,
            echo=False,
            # Supabase free tier limita a ~15 conexiones simultáneas.
            # Con Transaction Pooler en port 6543, pool_size=5 es seguro.
            pool_size=5,
            max_overflow=0,
            pool_pre_ping=True,
            pool_recycle=300,
        )
    return _engine


def get_session_factory():
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        _AsyncSessionLocal = sessionmaker(
            get_engine(), class_=AsyncSession, expire_on_commit=False
        )
    return _AsyncSessionLocal


def AsyncSessionLocal():
    return get_session_factory()()


async def get_db():
    factory = get_session_factory()
    async with factory() as session:
        yield session


# Import all models so they're registered with Base
from app.models import Funcionario, Empresa, Contrato, Proceso, Conexion  # noqa: E402, F401

__all__ = ["Base", "get_engine", "AsyncSessionLocal", "get_db"]
