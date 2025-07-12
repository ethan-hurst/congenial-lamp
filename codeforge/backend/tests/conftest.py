"""
Test configuration and fixtures
"""
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

from src.main import app
from src.models.base import Base
from src.services.credits_service import CreditsService
from src.services.ai_service import MultiAgentAI
from src.services.clone_service import InstantCloneService
from src.services.container_orchestrator import ContainerOrchestrator


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db():
    """Create a test database"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def client():
    """Create a test client"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_credits_service():
    """Mock credits service"""
    service = Mock(spec=CreditsService)
    service.get_user_balance = AsyncMock(return_value={"balance": 1000, "tier": "premium"})
    service.consume_credits = AsyncMock(return_value=True)
    service.add_credits = AsyncMock(return_value={"new_balance": 1100})
    return service


@pytest.fixture
def mock_ai_service():
    """Mock AI service"""
    service = Mock(spec=MultiAgentAI)
    service.process_request = AsyncMock(return_value=Mock(
        content="Mock AI response",
        suggestions=[{"type": "completion", "code": "print('hello')", "confidence": 0.9}],
        confidence=0.9,
        processing_time=0.5,
        credits_consumed=2
    ))
    service.generate_code_completion = AsyncMock(return_value=[
        {"type": "completion", "code": "print('hello')", "confidence": 0.9}
    ])
    service.chat_stream = AsyncMock()
    return service


@pytest.fixture
def mock_clone_service():
    """Mock clone service"""
    service = Mock(spec=InstantCloneService)
    service.clone_project = AsyncMock(return_value=Mock(
        success=True,
        clone_id="test-clone-123",
        new_project_id="test-project-456",
        cloned_files=25,
        total_time_seconds=0.8,
        performance_metrics={"files_per_second": 31.25}
    ))
    return service


@pytest.fixture
def mock_container_service():
    """Mock container orchestrator"""
    service = Mock(spec=ContainerOrchestrator)
    service.create_container = AsyncMock(return_value={
        "container_id": "test-container-123",
        "status": "running",
        "ports": {"8000": 8000}
    })
    service.get_container_stats = AsyncMock(return_value={
        "cpu_usage": 15.5,
        "memory_usage": 256,
        "network_io": {"rx": 1024, "tx": 512}
    })
    return service


@pytest.fixture
def sample_user():
    """Sample user data"""
    return {
        "id": "test-user-123",
        "email": "test@example.com",
        "username": "testuser",
        "credits_balance": 1000,
        "tier": "premium"
    }


@pytest.fixture
def sample_project():
    """Sample project data"""
    return {
        "id": "test-project-123",
        "name": "Test Project",
        "description": "A test project",
        "language": "python",
        "template": "fastapi",
        "user_id": "test-user-123",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def auth_headers():
    """Authentication headers"""
    return {"Authorization": "Bearer test-token-123"}


@pytest.fixture
def sample_code_context():
    """Sample code context for AI operations"""
    return {
        "file_path": "test.py",
        "content": "def hello():\n    print('Hello, world!')",
        "language": "python",
        "cursor_position": 25,
        "selection_start": 0,
        "selection_end": 44
    }