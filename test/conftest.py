import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app  
from app.db.session import get_session 
from app.models.base import Base  
from app.core.config import settings

@pytest.fixture(scope='session')
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Creates an instance of the default event loop for session scope."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

test_engine = create_async_engine(
    str(settings.TEST_DATABASE_URL), 
    pool_pre_ping=True,

)

TestSessionFactory = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

@pytest_asyncio.fixture(scope="function", autouse=True)
async def clean_db_per_function():
    """
    Drops and recreates all tables for EACH test function, ensuring a clean state.
    Relies on pytest-asyncio for event loop management.
    """
    async with test_engine.begin() as conn:
        
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    yield


@pytest_asyncio.fixture(scope="session", autouse=True)
async def engine_lifecycle():
    """
    Manages the disposal of the test engine once after the entire test session.
    """
    yield
    await test_engine.dispose()


@pytest_asyncio.fixture(scope="function", autouse=True)
async def session_override(clean_db_per_function): 
    """
    Provides a session for each test function, overriding the `get_session` dependency.
    Ensures operations within a single test occur within a transaction that gets rolled back.
    Runs *after* clean_db_per_function due to dependency.
    """
    async with TestSessionFactory() as session:
        await session.begin_nested()

        async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
             yield session

        original_override = app.dependency_overrides.get(get_session)
        app.dependency_overrides[get_session] = override_get_session

        yield

        if original_override:
             app.dependency_overrides[get_session] = original_override
        else:
             if get_session in app.dependency_overrides:
                 del app.dependency_overrides[get_session]

        if session.is_active:
            await session.rollback()


@pytest_asyncio.fixture(scope="function")
async def client() -> AsyncGenerator[AsyncClient, None]:
    """
    Provides an HTTPX AsyncClient for making requests to the test app.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac
