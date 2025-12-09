"""Tests for agent.core.database module."""

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine

from agent.core.config import AgentSettings
from agent.core.database import close_database_engine, create_database_engine


@pytest.mark.asyncio
async def test_create_engine_success():
    """Test successful engine creation with valid settings."""
    settings = AgentSettings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
    )

    engine = await create_database_engine(settings)

    # Verify engine was created
    assert engine is not None
    assert isinstance(engine, AsyncEngine)

    # Verify connection string components
    assert "test_db" in str(engine.url)
    assert "test_user" in str(engine.url)
    assert "localhost" in str(engine.url)

    # Cleanup
    await close_database_engine(engine)


@pytest.mark.asyncio
async def test_engine_pool_configuration():
    """Test that engine has correct pool settings."""
    settings = AgentSettings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
    )

    engine = await create_database_engine(settings)

    # Verify pool configuration
    assert engine.pool is not None
    assert engine.pool.size() == 5
    assert engine.pool._max_overflow == 10

    # Cleanup
    await close_database_engine(engine)


@pytest.mark.asyncio
async def test_close_engine():
    """Test that engine closes without errors."""
    settings = AgentSettings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
    )

    engine = await create_database_engine(settings)
    assert engine is not None

    # Should not raise any exceptions
    await close_database_engine(engine)


@pytest.mark.asyncio
async def test_engine_uses_asyncpg_driver():
    """Test that engine uses postgresql+asyncpg driver."""
    settings = AgentSettings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="test_db",
        postgres_user="test_user",
        postgres_password="test_pass",
    )

    engine = await create_database_engine(settings)

    # Verify asyncpg driver is used
    assert "postgresql+asyncpg" in str(engine.url)

    await close_database_engine(engine)


@pytest.mark.asyncio
async def test_engine_connection_string_format():
    """Test that connection string is correctly formatted."""
    settings = AgentSettings(
        postgres_host="db.example.com",
        postgres_port=5433,
        postgres_db="mydb",
        postgres_user="myuser",
        postgres_password="mypass",
    )

    engine = await create_database_engine(settings)

    url_str = str(engine.url)

    # Verify all components are present (password is masked by SQLAlchemy)
    assert "postgresql+asyncpg" in url_str
    assert "myuser" in url_str
    assert "db.example.com" in url_str
    assert "5433" in url_str
    assert "mydb" in url_str

    # Verify password is NOT exposed (should be masked as ***)
    assert "mypass" not in url_str
    assert "***" in url_str

    await close_database_engine(engine)


@pytest.mark.asyncio
async def test_multiple_engines_independent():
    """Test that multiple engines can be created independently."""
    settings1 = AgentSettings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="db1",
        postgres_user="user1",
        postgres_password="pass1",
    )

    settings2 = AgentSettings(
        postgres_host="localhost",
        postgres_port=5432,
        postgres_db="db2",
        postgres_user="user2",
        postgres_password="pass2",
    )

    engine1 = await create_database_engine(settings1)
    engine2 = await create_database_engine(settings2)

    # Engines should be different objects
    assert engine1 is not engine2

    # URLs should be different
    assert str(engine1.url) != str(engine2.url)

    # Cleanup
    await close_database_engine(engine1)
    await close_database_engine(engine2)
