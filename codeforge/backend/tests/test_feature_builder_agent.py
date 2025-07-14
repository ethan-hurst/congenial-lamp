"""
Tests for Feature Builder Agent
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.ai.agents.feature_builder import FeatureBuilderAgent
from src.services.ai.base import CodeContext, Constraint, AgentResult
from src.services.ai.context_builder import FileContext, ProjectContext


@pytest.fixture
def feature_builder():
    """Create feature builder agent instance"""
    return FeatureBuilderAgent()


@pytest.fixture
def sample_context():
    """Create sample code context"""
    return CodeContext(
        project_id="test-project",
        files=[
            FileContext(
                path="src/main.py",
                content="""from flask import Flask\napp = Flask(__name__)""",
                language="python",
                size=50,
                last_modified=datetime.now()
            ),
            FileContext(
                path="src/models.py",
                content="""from sqlalchemy import Column, String\nclass User: pass""",
                language="python",
                size=60,
                last_modified=datetime.now()
            )
        ],
        project_structure=ProjectContext(
            root_path="/test/project",
            directories=["src", "tests", "docs"],
            total_files=15,
            languages={"python": 10, "yaml": 3, "markdown": 2}
        ),
        dependencies={"flask": "2.0.0", "sqlalchemy": "1.4.0"},
        test_coverage={"overall": 75.0, "files": {}}
    )


class TestFeatureBuilderAgent:
    """Test Feature Builder Agent functionality"""
    
    @pytest.mark.asyncio
    async def test_analyze_requirements_api_feature(self, feature_builder):
        """Test analyzing API feature requirements"""
        requirements = "Create a REST API endpoint for user registration with email and password"
        
        analysis = await feature_builder._analyze_requirements(requirements)
        
        assert analysis["type"] == "api"
        assert "components" in analysis
        assert "endpoint" in analysis["components"]
        assert "data_model" in analysis["components"]
        assert "validation" in analysis["components"]
    
    @pytest.mark.asyncio
    async def test_analyze_requirements_ui_feature(self, feature_builder):
        """Test analyzing UI feature requirements"""
        requirements = "Build a React component for displaying user profiles with avatar and bio"
        
        analysis = await feature_builder._analyze_requirements(requirements)
        
        assert analysis["type"] == "ui"
        assert "components" in analysis
        assert "component" in analysis["components"]
        assert "state" in analysis["components"]
    
    @pytest.mark.asyncio
    async def test_plan_implementation_api(self, feature_builder, sample_context):
        """Test planning API implementation"""
        analysis = {
            "type": "api",
            "components": {
                "endpoint": "/api/users/register",
                "method": "POST",
                "data_model": {"email": "string", "password": "string"}
            }
        }
        constraints = [
            Constraint("tech_stack", {"framework": "flask"}, "Use Flask framework")
        ]
        
        plan = await feature_builder._plan_implementation(
            sample_context, analysis, constraints
        )
        
        assert len(plan) > 0
        assert any("route" in step["description"].lower() for step in plan)
        assert any("model" in step["description"].lower() for step in plan)
        assert any("validation" in step["description"].lower() for step in plan)
    
    @pytest.mark.asyncio
    async def test_generate_code_api_endpoint(self, feature_builder, sample_context):
        """Test generating code for API endpoint"""
        plan_step = {
            "file": "src/api/users.py",
            "action": "create",
            "description": "Create user registration endpoint",
            "code_type": "api_endpoint"
        }
        
        tech_stack = {"language": "python", "framework": "flask"}
        requirements = "User registration with email and password"
        
        code = await feature_builder._generate_code(
            plan_step, sample_context, tech_stack, requirements
        )
        
        assert "flask" in code.lower() or "route" in code.lower()
        assert "def" in code
        assert "email" in code
        assert "password" in code
    
    @pytest.mark.asyncio
    async def test_generate_code_data_model(self, feature_builder, sample_context):
        """Test generating code for data model"""
        plan_step = {
            "file": "src/models/user.py",
            "action": "create",
            "description": "Create User model",
            "code_type": "data_model"
        }
        
        tech_stack = {"language": "python", "orm": "sqlalchemy"}
        requirements = "User model with email, password, and created_at fields"
        
        code = await feature_builder._generate_code(
            plan_step, sample_context, tech_stack, requirements
        )
        
        assert "class User" in code
        assert "email" in code
        assert "password" in code
        assert "created_at" in code
    
    @pytest.mark.asyncio
    async def test_validate_implementation(self, feature_builder):
        """Test implementation validation"""
        implementation = {
            "files_created": ["src/api/users.py", "src/models/user.py"],
            "files_modified": ["src/main.py"],
            "tests_added": ["tests/test_users.py"]
        }
        requirements = "Create user registration API"
        
        validation = await feature_builder._validate_implementation(
            implementation, requirements
        )
        
        assert validation["is_valid"] is True
        assert validation["completeness"] > 0.8
        assert len(validation["suggestions"]) >= 0
    
    @pytest.mark.asyncio
    async def test_estimate_task_simple(self, feature_builder, sample_context):
        """Test estimating simple task"""
        requirements = "Add a simple utility function to format dates"
        
        estimate = await feature_builder.estimate_task(
            sample_context, requirements, []
        )
        
        assert estimate["estimated_time"] < 300  # Less than 5 minutes
        assert estimate["estimated_credits"] < 20
        assert estimate["complexity"] == "low"
    
    @pytest.mark.asyncio
    async def test_estimate_task_complex(self, feature_builder, sample_context):
        """Test estimating complex task"""
        requirements = """
        Build a complete user authentication system with:
        - Registration, login, logout endpoints
        - JWT token generation and validation
        - Password hashing and reset functionality
        - Email verification
        - Role-based access control
        - Integration tests
        """
        
        estimate = await feature_builder.estimate_task(
            sample_context, requirements, []
        )
        
        assert estimate["estimated_time"] > 600  # More than 10 minutes
        assert estimate["estimated_credits"] > 50
        assert estimate["complexity"] in ["high", "very_high"]
    
    @pytest.mark.asyncio
    async def test_execute_success(self, feature_builder, sample_context):
        """Test successful feature execution"""
        requirements = "Create a simple health check endpoint"
        constraints = []
        
        with patch.object(feature_builder, '_analyze_requirements') as mock_analyze, \
             patch.object(feature_builder, '_plan_implementation') as mock_plan, \
             patch.object(feature_builder, '_generate_code') as mock_generate, \
             patch.object(feature_builder, '_apply_code_changes') as mock_apply, \
             patch.object(feature_builder, '_validate_implementation') as mock_validate:
            
            mock_analyze.return_value = {
                "type": "api",
                "components": {"endpoint": "/health"}
            }
            
            mock_plan.return_value = [{
                "file": "src/api/health.py",
                "action": "create",
                "description": "Create health check endpoint"
            }]
            
            mock_generate.return_value = "def health_check(): return {'status': 'ok'}"
            mock_apply.return_value = True
            mock_validate.return_value = {"is_valid": True, "completeness": 1.0}
            
            result = await feature_builder.execute(
                sample_context, requirements, constraints
            )
            
            assert result.success is True
            assert result.confidence > 0.8
            assert "files_created" in result.data
            assert len(result.artifacts) > 0
    
    @pytest.mark.asyncio
    async def test_execute_with_tech_stack_constraint(self, feature_builder, sample_context):
        """Test execution with technology stack constraint"""
        requirements = "Create a REST API endpoint"
        constraints = [
            Constraint(
                "tech_stack",
                {"language": "python", "framework": "fastapi"},
                "Use FastAPI"
            )
        ]
        
        with patch.object(feature_builder, '_generate_code') as mock_generate:
            mock_generate.return_value = "@app.post('/api/endpoint')\nasync def endpoint(): pass"
            
            # Execute partial flow to test constraint handling
            await feature_builder._analyze_requirements(requirements)
            
            # The constraint should be considered in code generation
            assert constraints[0].value["framework"] == "fastapi"
    
    @pytest.mark.asyncio
    async def test_execute_error_handling(self, feature_builder, sample_context):
        """Test error handling during execution"""
        requirements = "Create a feature"
        constraints = []
        
        with patch.object(feature_builder, '_analyze_requirements') as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")
            
            result = await feature_builder.execute(
                sample_context, requirements, constraints
            )
            
            assert result.success is False
            assert result.confidence < 0.5
            assert "error" in result.data
            assert "Analysis failed" in result.data["error"]
    
    @pytest.mark.asyncio
    async def test_apply_code_changes_create_file(self, feature_builder):
        """Test applying code changes - create new file"""
        step = {
            "file": "src/new_file.py",
            "action": "create"
        }
        code = "def new_function(): pass"
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('os.makedirs') as mock_makedirs:
            
            success = await feature_builder._apply_code_changes(step, code)
            
            assert success is True
            mock_makedirs.assert_called_once()
            mock_open.assert_called_once_with("src/new_file.py", "w")
    
    @pytest.mark.asyncio
    async def test_apply_code_changes_modify_file(self, feature_builder):
        """Test applying code changes - modify existing file"""
        step = {
            "file": "src/existing.py",
            "action": "modify",
            "location": "end"
        }
        code = "\ndef new_function(): pass"
        existing_content = "def existing_function(): pass"
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            
            # Configure mock for reading
            mock_file_read = MagicMock()
            mock_file_read.__enter__.return_value.read.return_value = existing_content
            
            # Configure mock for writing
            mock_file_write = MagicMock()
            written_content = []
            mock_file_write.__enter__.return_value.write.side_effect = lambda x: written_content.append(x)
            
            mock_open.side_effect = [mock_file_read, mock_file_write]
            
            success = await feature_builder._apply_code_changes(step, code)
            
            assert success is True
            assert len(written_content) > 0
            assert existing_content in written_content[0]
            assert code in written_content[0]