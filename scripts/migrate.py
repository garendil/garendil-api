import asyncio
import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://dev:dev@localhost:5432/garendil_db")

async def run_migrations():
    print("Running database migrations...")

    db_url = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(db_url, echo=False)

    try:
        async with engine.begin() as conn:
            migrations_dir = Path(__file__).parent.parent / "db" / "migrations"

            if not migrations_dir.exists():
                print(f"No migrations dir found at {migrations_dir}")
                return

            sql_files = sorted(migrations_dir.glob("*.sql"))

            if not sql_files:
                print("No SQL files found")
                return

            for sql_file in sql_files:
                print(f"Executing {sql_file.name}...")
                with open(sql_file) as f:
                    sql_content = f.read()
                await conn.execute(text(sql_content))
                print(f"  Done: {sql_file.name}")

        print("Migrations complete")

    except Exception as e:
        print(f"Error in migrations: {e}")
        raise

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migrations())
