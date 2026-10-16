import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env", override=True)

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in the root .env file")

engine: AsyncEngine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1),
    pool_pre_ping=True,
)
