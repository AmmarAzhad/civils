from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings 
from typing import AsyncGenerator
from app.models.base import Base

DATABASE_URL = settings.DATABASE_URL 

engine = create_async_engine(DATABASE_URL, pool_pre_ping=True)

AsyncSessionFactory = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False, 
    autocommit=False 
)

async def init_db():
    """Placeholder for any initial DB setup (like creating tables with metadata)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("--- Database Initialized (or connection pool ready) ---")

async def close_db():
    """Closes the database connection pool."""
    await engine.dispose()
    print("--- Database Connection Pool Closed ---")

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that provides a database session per request.
    Yields:
        AsyncSession: The database session.
    """
    async_session: AsyncSession = AsyncSessionFactory()
    try:
        yield async_session 
        await async_session.commit()
    except Exception as e:
        await async_session.rollback()
        raise e
    finally:
        await async_session.close()