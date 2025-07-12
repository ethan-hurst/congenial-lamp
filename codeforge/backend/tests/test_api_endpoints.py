"""
Tests for API endpoints
"""
import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

from src.main import app


class TestAuthEndpoints:
    """Test authentication endpoints"""

    def test_health_check(self):
        """Test health check endpoint"""
        with TestClient(app) as client:
            response = client.get("/health")
            
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
            assert "version" in response.json()

    @patch('src.auth.auth_service.AuthService.login')
    def test_login_success(self, mock_login):
        """Test successful login"""
        mock_login.return_value = {
            "access_token": "test-token",
            "token_type": "bearer",
            "user": {"id": "123", "email": "test@example.com"}
        }
        
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "password123"
            })
            
            assert response.status_code == 200
            assert "access_token" in response.json()

    @patch('src.auth.auth_service.AuthService.login')
    def test_login_invalid_credentials(self, mock_login):
        """Test login with invalid credentials"""
        mock_login.side_effect = Exception("Invalid credentials")
        
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", json={
                "email": "test@example.com",
                "password": "wrongpassword"
            })
            
            assert response.status_code == 500

    def test_login_missing_fields(self):
        """Test login with missing fields"""
        with TestClient(app) as client:
            response = client.post("/api/v1/auth/login", json={
                "email": "test@example.com"
                # missing password
            })
            
            assert response.status_code == 422  # Validation error


class TestAIEndpoints:
    """Test AI endpoints"""

    @patch('src.services.ai_service.MultiAgentAI.generate_code_completion')
    @patch('src.auth.dependencies.get_current_user')
    def test_code_completion(self, mock_user, mock_completion):
        """Test code completion endpoint"""
        mock_user.return_value = Mock(id="user123")
        mock_completion.return_value = [
            {"type": "completion", "code": "print('hello')", "confidence": 0.9}
        ]
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/complete",
                json={
                    "file_path": "test.py",
                    "content": "def hello():",
                    "language": "python",
                    "cursor_position": 12,
                    "max_suggestions": 3
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert "suggestions" in response.json()

    @patch('src.services.ai_service.MultiAgentAI.process_request')
    @patch('src.auth.dependencies.get_current_user')
    def test_explain_code(self, mock_user, mock_process):
        """Test code explanation endpoint"""
        mock_user.return_value = Mock(id="user123")
        mock_process.return_value = Mock(
            content="This function prints a greeting",
            suggestions=[],
            confidence=0.9,
            processing_time=0.5,
            credits_consumed=2
        )
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/explain",
                json={
                    "file_path": "test.py",
                    "content": "def hello():\n    print('Hello')",
                    "language": "python"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert "greeting" in response.json()["content"]

    @patch('src.services.ai_service.MultiAgentAI.chat_stream')
    @patch('src.auth.dependencies.get_current_user')
    def test_chat_with_ai(self, mock_user, mock_chat):
        """Test AI chat endpoint"""
        mock_user.return_value = Mock(id="user123")
        
        async def mock_stream():
            yield "Hello, "
            yield "how can "
            yield "I help you?"
            
        mock_chat.return_value = mock_stream()
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/chat",
                json={
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ],
                    "stream": False
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True

    @patch('src.auth.dependencies.get_current_user')
    def test_get_ai_providers(self, mock_user):
        """Test getting AI providers"""
        mock_user.return_value = Mock(id="user123")
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/ai/providers",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert "providers" in response.json()
            assert len(response.json()["providers"]) > 0


class TestCloneEndpoints:
    """Test clone endpoints"""

    @patch('src.services.clone_service.InstantCloneService.clone_project')
    @patch('src.auth.dependencies.get_current_user')
    def test_start_clone(self, mock_user, mock_clone):
        """Test starting project clone"""
        mock_user.return_value = Mock(id="user123")
        mock_clone.return_value = Mock(
            success=True,
            clone_id="clone123",
            new_project_id="project456",
            cloned_files=25,
            total_time_seconds=0.8,
            performance_metrics={"files_per_second": 31.25}
        )
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clone/start",
                json={
                    "project_id": "source123",
                    "clone_name": "My Clone",
                    "include_dependencies": True,
                    "include_containers": True
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["new_project_id"] == "project456"

    @patch('src.services.clone_service.InstantCloneService.clone_project')
    @patch('src.auth.dependencies.get_current_user')
    def test_quick_clone(self, mock_user, mock_clone):
        """Test quick clone endpoint"""
        mock_user.return_value = Mock(id="user123")
        mock_clone.return_value = Mock(
            success=True,
            clone_id="clone123",
            new_project_id="project456",
            cloned_files=15,
            total_time_seconds=0.4,
            performance_metrics={"files_per_second": 37.5}
        )
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/clone/quick/source123",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["success"] is True
            assert response.json()["performance"]["time_seconds"] == 0.4

    @patch('src.services.clone_service.InstantCloneService.get_clone_status')
    @patch('src.auth.dependencies.get_current_user')
    def test_get_clone_status(self, mock_user, mock_get_status):
        """Test getting clone status"""
        mock_user.return_value = Mock(id="user123")
        mock_metadata = Mock(
            clone_id="clone123",
            user_id="user123",
            status="completed",
            progress=1.0,
            files_copied=25,
            total_files=25,
            bytes_copied=50000,
            total_bytes=50000,
            start_time=Mock(isoformat=Mock(return_value="2024-01-01T00:00:00Z")),
            end_time=Mock(isoformat=Mock(return_value="2024-01-01T00:00:01Z")),
            error_message=None
        )
        mock_get_status.return_value = mock_metadata
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/clone/status/clone123",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["clone_id"] == "clone123"
            assert response.json()["status"] == "completed"

    @patch('src.auth.dependencies.get_current_user')
    def test_get_clone_templates(self, mock_user):
        """Test getting clone templates"""
        mock_user.return_value = Mock(id="user123")
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/clone/templates",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert "templates" in response.json()
            templates = response.json()["templates"]
            assert len(templates) > 0
            assert all("clone_time_estimate" in t for t in templates)


class TestContainerEndpoints:
    """Test container endpoints"""

    @patch('src.services.container_orchestrator.ContainerOrchestrator.create_container')
    @patch('src.auth.dependencies.get_current_user')
    def test_create_container(self, mock_user, mock_create):
        """Test creating container"""
        mock_user.return_value = Mock(id="user123")
        mock_create.return_value = {
            "container_id": "container123",
            "status": "running",
            "ports": {"8000": 8000}
        }
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/containers/create",
                json={
                    "project_id": "project123",
                    "language": "python",
                    "memory_limit": "512m"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["container_id"] == "container123"

    @patch('src.services.container_orchestrator.ContainerOrchestrator.get_container_stats')
    @patch('src.auth.dependencies.get_current_user')
    def test_get_container_stats(self, mock_user, mock_stats):
        """Test getting container stats"""
        mock_user.return_value = Mock(id="user123")
        mock_stats.return_value = {
            "cpu_usage": 15.5,
            "memory_usage": 256,
            "network_io": {"rx": 1024, "tx": 512}
        }
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/containers/container123/stats",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 200
            assert response.json()["cpu_usage"] == 15.5


class TestErrorHandling:
    """Test error handling"""

    def test_404_endpoint(self):
        """Test non-existent endpoint"""
        with TestClient(app) as client:
            response = client.get("/api/v1/nonexistent")
            
            assert response.status_code == 404

    @patch('src.auth.dependencies.get_current_user')
    def test_unauthorized_request(self, mock_user):
        """Test request without authorization"""
        with TestClient(app) as client:
            response = client.get("/api/v1/ai/providers")
            
            assert response.status_code == 401

    @patch('src.services.ai_service.MultiAgentAI.process_request')
    @patch('src.auth.dependencies.get_current_user')
    def test_internal_server_error(self, mock_user, mock_process):
        """Test internal server error handling"""
        mock_user.return_value = Mock(id="user123")
        mock_process.side_effect = Exception("Internal error")
        
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/explain",
                json={
                    "file_path": "test.py",
                    "content": "def hello(): pass",
                    "language": "python"
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 500
            assert "failed" in response.json()["detail"]

    def test_validation_error(self):
        """Test request validation error"""
        with TestClient(app) as client:
            response = client.post(
                "/api/v1/ai/complete",
                json={
                    "file_path": "test.py",
                    # missing required fields
                },
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 422

    @patch('src.services.clone_service.InstantCloneService.get_clone_status')
    @patch('src.auth.dependencies.get_current_user')
    def test_access_denied(self, mock_user, mock_get_status):
        """Test access denied for other user's resources"""
        mock_user.return_value = Mock(id="user123")
        mock_metadata = Mock(user_id="otheruser")
        mock_get_status.return_value = mock_metadata
        
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/clone/status/clone123",
                headers={"Authorization": "Bearer test-token"}
            )
            
            assert response.status_code == 403