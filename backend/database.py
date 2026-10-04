import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

DATABASE_URL = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL must be set in the root .env file")

engine: AsyncEngine = create_async_engine(
    DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1),
    pool_pre_ping=True,
)
