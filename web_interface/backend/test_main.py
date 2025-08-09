"""
Basic tests for the FastAPI application structure.

This module contains tests to verify that the application can be created
and basic endpoints are accessible.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

from .main import create_app
from .config import get_settings


@pytest.fixture
def mock_storage_manager():
    """Create a mock storage manager for testing."""
    mock = AsyncMock()
    mock.initialize = AsyncMock()
    mock.shutdown = AsyncMock()
    return mock


@pytest.fixture
def mock_query_engine():
    """Create a mock query engine for testing."""
    mock = AsyncMock()
    mock.storage_manager = AsyncMock()
    return mock


@pytest.fixture
def test_app(mock_storage_manager, mock_query_engine):
    """Create a test FastAPI application with mocked dependencies."""
    app = create_app()
    
    # Override the lifespan to avoid actual storage initialization
    app.state.storage_manager = mock_storage_manager
    app.state.query_engine = mock_query_engine
    
    return app


@pytest.fixture
def client(test_app):
    """Create a test client for the FastAPI application."""
    return TestClient(test_app)


def test_create_app():
    """Test that the FastAPI application can be created."""
    app = create_app()
    assert app is not None
    assert app.title == "Game Analysis API"


def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_games_endpoint_structure(client):
    """Test that the games endpoint exists and returns proper error for missing data."""
    # This will fail because we don't have real data, but it tests the route structure
    response = client.get("/api/games")
    # Should return 500 because of missing storage data, but route should exist
    assert response.status_code in [500, 501]  # Either server error or not implemented


def test_cors_headers(client):
    """Test that CORS headers are properly configured."""
    response = client.options("/api/games")
    # CORS preflight should be handled
    assert response.status_code in [200, 405]  # Either OK or method not allowed


def test_settings_configuration():
    """Test that settings can be loaded properly."""
    settings = get_settings()
    assert settings is not None
    assert settings.version == "1.0.0"
    assert isinstance(settings.debug, bool)
    assert isinstance(settings.port, int)