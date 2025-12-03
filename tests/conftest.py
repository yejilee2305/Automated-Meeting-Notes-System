import shutil
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.main import app


@pytest.fixture
def client():
    """Create a test client for our API."""
    return TestClient(app)


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
