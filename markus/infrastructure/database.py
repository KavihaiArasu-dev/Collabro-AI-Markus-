"""
Markus AI — Infrastructure Database Engine & Session Factory (§6, §7)
"""

from __future__ import annotations

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base

from config.settings import settings

logger = logging.getLogger(__name__)

Base = declarative_base()

# Determine database url
# Fallback to local SQLite if MySQL driver isn't configured for async
_db_url = settings.database.url
if _db_url.startswith("mysql+pymysql"):
    _async_db_url = _db_url.replace("mysql+pymysql", "mysql+aiomysql")
elif _db_url.startswith("sqlite"):
    _async_db_url = _db_url.replace("sqlite://", "sqlite+aiosqlite://")
else:
    _async_db_url = "sqlite+aiosqlite:///./data/markus_app.db"

try:
    engine = create_async_engine(
        _async_db_url,
        echo=settings.database.echo,
        future=True,
    )
    async_session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    logger.info(f"Database engine initialized for {_async_db_url.split('@')[-1] if '@' in _async_db_url else _async_db_url}")
except Exception as e:
    logger.warning(f"Could not initialize primary database ({e}). Falling back to local SQLite.")
    fallback_url = "sqlite+aiosqlite:///./data/markus_app.db"
    engine = create_async_engine(fallback_url, echo=False)
    async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions."""
    async with async_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
