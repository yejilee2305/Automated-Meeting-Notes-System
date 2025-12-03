import os
import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    """Reset rate limiter storage between tests to avoid rate limit errors."""
    from app.rate_limit import limiter

    # clear the limiter storage before each test
    if hasattr(limiter, '_storage') and limiter._storage:
        limiter._storage.reset()

    yield


@pytest.fixture
def client():
    """
    Create a test client for our API.
    The lifespan context creates the tables automatically.
    """
    # use temp database for tests
    original_url = settings.database_url
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    settings.database_url = f"sqlite+aiosqlite:///{temp_db.name}"

    # recreate engine with new url
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    from app import database

    database.engine = create_async_engine(settings.database_url, echo=False)
    database.async_session = sessionmaker(
        database.engine, class_=AsyncSession, expire_on_commit=False
    )

    # TestClient uses lifespan context which calls init_db()
    with TestClient(app) as c:
        yield c

    # cleanup
    settings.database_url = original_url
    try:
        os.unlink(temp_db.name)
    except OSError:
        pass


@pytest.fixture
def temp_upload_dir():
    """
    Create a temp directory for uploads during tests.
    This keeps test files separate from real uploads.
    """
    original_dir = settings.upload_dir
    temp_dir = tempfile.mkdtemp()
    settings.upload_dir = temp_dir

    yield temp_dir

    # cleanup after test
    settings.upload_dir = original_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def sample_audio_content():
    """
    Fake audio file content for testing.
    In real life this would be actual audio bytes,
    but for upload tests we just need some data.
    """
    return b"fake audio content " * 100
