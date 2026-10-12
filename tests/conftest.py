"""
Pytest configuration and fixtures for testing Secure Online Code Execution Platform.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.job_manager import job_manager

@pytest.fixture(scope="session")
def client():
    """Test client for FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture(autouse=True)
def ensure_worker_ready():
    """Ensure worker readiness is restored after every test."""
    job_manager.set_worker_readiness(True)
    yield
    job_manager.set_worker_readiness(True)
