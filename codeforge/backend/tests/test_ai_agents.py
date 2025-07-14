"""
Unit tests for AI agent services
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.services.ai.orchestrator import AgentOrchestrator, Constraint, Workflow
from src.services.ai.agents.base_agent import BaseAgent
from src.services.ai.agents.feature_builder import FeatureBuilderAgent
from src.services.ai.sandbox import CodeSandbox, SandboxConfig, SecurityViolation
from src.services.ai.git_integration import GitIntegration, AgentGitWorkflow
from src.services.ai.metrics import MetricsCalculator, AgentAnalytics
from src.models.ai_agent import (
    AgentTask, AgentWorkflow, AgentArtifact, CodeContext,
    TaskStatus, AgentType, WorkflowType, TaskPriority
)


class TestAgentOrchestrator:
    """Test AgentOrchestrator functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def orchestrator(self, mock_db):
        return AgentOrchestrator(mock_db)
    
    @pytest.mark.asyncio
    async def test_execute_task_success(self, orchestrator, mock_db):
        """Test successful task execution"""
        # Setup
        mock_context = Mock()
        mock_context.file_paths = ["test.py"]
        mock_context.scope = "file"
        
        mock_agent = AsyncMock()
        mock_result = Mock()
        mock_result.success = True
        mock_result.__dict__ = {"success": True, "output": "test output"}
        mock_result.metrics = {"confidence": 0.8}
        
        mock_agent.execute.return_value = mock_result
        orchestrator.agents[AgentType.FEATURE_BUILDER] = mock_agent
        
        mock_task = Mock()
        mock_task.id = "test-task-id"
        mock_task.started_at = datetime.utcnow()
        mock_task.completed_at = datetime.utcnow()
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.ai_agent.AgentTask', return_value=mock_task):
            result = await orchestrator.execute_task(
                task_type=AgentType.FEATURE_BUILDER,
                context=mock_context,
                requirements="Build a test feature",
                constraints=[],
                user_id="test-user",
                project_id="test-project"
            )
        
        # Assert
        assert result.success is True
        mock_agent.execute.assert_called_once()
        assert mock_task.id in orchestrator.active_tasks
    
    @pytest.mark.asyncio
    async def test_execute_task_failure(self, orchestrator, mock_db):
        """Test task execution failure handling"""
        # Setup
        mock_context = Mock()
        mock_agent = AsyncMock()
        mock_agent.execute.side_effect = Exception("Agent execution failed")
        
        orchestrator.agents[AgentType.FEATURE_BUILDER] = mock_agent
        
        mock_task = Mock()
        mock_task.id = "test-task-id"
        mock_task.started_at = datetime.utcnow()
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.ai_agent.AgentTask', return_value=mock_task):
            result = await orchestrator.execute_task(
                task_type=AgentType.FEATURE_BUILDER,
                context=mock_context,
                requirements="Build a test feature",
                constraints=[],
                user_id="test-user",
                project_id="test-project"
            )
        
        # Assert
        assert result.success is False
        assert "Agent execution failed" in str(result.metrics.get("error", ""))
    
    @pytest.mark.asyncio
    async def test_coordinate_agents_workflow(self, orchestrator, mock_db):
        """Test multi-agent workflow coordination"""
        # Setup
        workflow = Mock()
        workflow.workflow_type = WorkflowType.FEATURE_DEVELOPMENT
        workflow.steps = [
            {"agent": AgentType.FEATURE_BUILDER, "action": "plan_and_implement"},
            {"agent": AgentType.TEST_WRITER, "action": "generate_tests"}
        ]
        
        mock_context = Mock()
        
        # Mock agents
        mock_feature_agent = AsyncMock()
        mock_test_agent = AsyncMock()
        mock_result = Mock()
        mock_result.__dict__ = {"success": True}
        
        mock_feature_agent.execute_action.return_value = mock_result
        mock_test_agent.execute_action.return_value = mock_result
        
        orchestrator.agents[AgentType.FEATURE_BUILDER] = mock_feature_agent
        orchestrator.agents[AgentType.TEST_WRITER] = mock_test_agent
        
        mock_workflow_record = Mock()
        mock_workflow_record.id = "test-workflow-id"
        mock_subtask = Mock()
        mock_subtask.id = "test-subtask-id"
        
        mock_db.add.return_value = None
        mock_db.commit.return_value = None
        
        # Execute
        with patch('src.models.ai_agent.AgentWorkflow', return_value=mock_workflow_record), \
             patch('src.models.ai_agent.AgentSubtask', return_value=mock_subtask):
            result = await orchestrator.coordinate_agents(
                workflow=workflow,
                context=mock_context,
                requirements="Test workflow",
                user_id="test-user",
                project_id="test-project"
            )
        
        # Assert
        assert result.success is True
        assert result.steps_completed == 2
        mock_feature_agent.execute_action.assert_called_once()
        mock_test_agent.execute_action.assert_called_once()
    
    def test_add_progress_update(self, orchestrator):
        """Test progress update functionality"""
        task_id = "test-task-id"
        
        # Execute
        orchestrator.add_progress_update(task_id, 0.5, "Half complete", {"details": "test"})
        
        # Assert
        assert task_id in orchestrator.progress_streams
        assert len(orchestrator.progress_streams[task_id]) == 1
        update = orchestrator.progress_streams[task_id][0]
        assert update["progress"] == 0.5
        assert update["message"] == "Half complete"
    
    def test_add_log_entry(self, orchestrator):
        """Test log entry functionality"""
        task_id = "test-task-id"
        
        # Execute
        orchestrator.add_log_entry(task_id, "Test log message")
        
        # Assert
        assert task_id in orchestrator.task_logs
        assert len(orchestrator.task_logs[task_id]) == 1
        assert "Test log message" in orchestrator.task_logs[task_id][0]


class TestBaseAgent:
    """Test BaseAgent functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def base_agent(self, mock_db):
        # Create a concrete implementation for testing
        class TestAgent(BaseAgent):
            async def _execute_impl(self, context, requirements, constraints, task_id):
                return self.create_result(True, "Test output")
            
            async def _execute_action_impl(self, action, context, task_id):
                return self.create_result(True, "Test action output")
        
        return TestAgent(mock_db)
    
    @pytest.mark.asyncio
    async def test_execute_code_safely(self, base_agent):
        """Test safe code execution"""
        # Setup
        base_agent.sandbox = Mock()
        base_agent.sandbox.execute_code = AsyncMock(return_value={
            "success": True,
            "output": "Hello, World!",
            "error": "",
            "return_code": 0
        })
        
        # Execute
        result = await base_agent.execute_code_safely(
            code="print('Hello, World!')",
            language="python"
        )
        
        # Assert
        assert result["success"] is True
        assert result["output"] == "Hello, World!"
        base_agent.sandbox.execute_code.assert_called_once()
    
    def test_analyze_code_structure_python(self, base_agent):
        """Test Python code structure analysis"""
        python_code = """
import os
import sys

class TestClass:
    def __init__(self):
        pass
    
    def test_method(self):
        return "test"

def test_function():
    return 42
"""
        
        # Execute
        result = base_agent.analyze_code_structure(python_code, "python")
        
        # Assert
        assert len(result["functions"]) == 1
        assert len(result["classes"]) == 1
        assert "os" in result["imports"]
        assert "sys" in result["imports"]
        assert result["functions"][0]["name"] == "test_function"
        assert result["classes"][0]["name"] == "TestClass"
    
    def test_estimate_complexity(self, base_agent):
        """Test task complexity estimation"""
        # Test low complexity
        low_req = "Simple function to add two numbers"
        assert base_agent._estimate_complexity(low_req) == "low"
        
        # Test high complexity
        high_req = "Complex enterprise-grade scalable performance-optimized architecture system with advanced security"
        assert base_agent._estimate_complexity(high_req) == "high"
    
    @pytest.mark.asyncio
    async def test_commit_changes(self, base_agent):
        """Test Git commit functionality"""
        # Setup
        base_agent.git_workflow = Mock()
        base_agent.git_workflow.execute_agent_workflow = AsyncMock(return_value={
            "success": True,
            "files_committed": ["test.py", "test2.py"],
            "commit_hash": "abc123"
        })
        
        artifacts = [
            {"path": "test.py", "content": "print('test')"},
            {"path": "test2.py", "content": "print('test2')"}
        ]
        
        # Execute
        result = await base_agent.commit_changes(
            task_id="test-task",
            artifacts=artifacts,
            commit_message="Test commit"
        )
        
        # Assert
        assert result["success"] is True
        assert len(result["files_committed"]) == 2
        base_agent.git_workflow.execute_agent_workflow.assert_called_once()


class TestCodeSandbox:
    """Test CodeSandbox functionality"""
    
    @pytest.fixture
    def sandbox_config(self):
        return SandboxConfig(
            max_execution_time=10,
            max_memory_mb=256,
            allowed_imports=["os", "sys", "json"]
        )
    
    @pytest.fixture
    def sandbox(self, sandbox_config):
        return CodeSandbox(sandbox_config)
    
    @pytest.mark.asyncio
    async def test_validate_python_security_safe(self, sandbox):
        """Test Python security validation for safe code"""
        safe_code = """
import os
import json

def hello_world():
    return "Hello, World!"

result = hello_world()
print(result)
"""
        
        # Execute
        result = await sandbox.validate_code_security(safe_code, "python")
        
        # Assert
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_python_security_unsafe(self, sandbox):
        """Test Python security validation for unsafe code"""
        unsafe_code = """
import subprocess
eval("print('dangerous')")
exec("import os; os.system('rm -rf /')")
"""
        
        # Execute & Assert
        with pytest.raises(SecurityViolation):
            await sandbox.validate_code_security(unsafe_code, "python")
    
    @pytest.mark.asyncio
    async def test_validate_javascript_security(self, sandbox):
        """Test JavaScript security validation"""
        # Safe code
        safe_js = """
function calculateSum(a, b) {
    return a + b;
}
console.log(calculateSum(2, 3));
"""
        result = await sandbox.validate_code_security(safe_js, "javascript")
        assert result is True
        
        # Unsafe code
        unsafe_js = """
require('child_process').exec('rm -rf /');
eval('dangerous code');
"""
        with pytest.raises(SecurityViolation):
            await sandbox.validate_code_security(unsafe_js, "javascript")
    
    @pytest.mark.asyncio
    async def test_execute_code_success(self, sandbox):
        """Test successful code execution"""
        # Mock Docker execution
        with patch.object(sandbox, 'docker_client', None):  # Force process execution
            with patch('asyncio.create_subprocess_exec') as mock_subprocess:
                mock_process = Mock()
                mock_process.communicate.return_value = (b"Hello, World!\n", b"")
                mock_process.returncode = 0
                mock_subprocess.return_value = mock_process
                
                # Execute
                result = await sandbox.execute_code(
                    code="print('Hello, World!')",
                    language="python"
                )
                
                # Assert
                assert result["success"] is True
                assert "Hello, World!" in result["output"]
                assert result["return_code"] == 0


class TestGitIntegration:
    """Test Git integration functionality"""
    
    @pytest.fixture
    def git_integration(self, tmp_path):
        # Create a mock git repository
        git_dir = tmp_path / ".git"
        git_dir.mkdir()
        return GitIntegration(str(tmp_path))
    
    @pytest.mark.asyncio
    async def test_create_agent_branch(self, git_integration):
        """Test agent branch creation"""
        # Mock git commands
        with patch.object(git_integration, '_run_git_command') as mock_git:
            mock_git.return_value = ""
            
            # Execute
            branch_name = await git_integration.create_agent_branch(
                agent_type="feature_builder",
                task_id="test-task-123"
            )
            
            # Assert
            assert "ai/feature_builder" in branch_name
            assert "test-task" in branch_name
            assert mock_git.call_count >= 3  # checkout, pull, checkout -b
    
    @pytest.mark.asyncio
    async def test_stage_files(self, git_integration):
        """Test file staging"""
        # Mock git commands
        with patch.object(git_integration, '_run_git_command') as mock_git:
            mock_git.return_value = ""
            
            # Execute
            result = await git_integration.stage_files(["file1.py", "file2.py"])
            
            # Assert
            assert result is True
            assert mock_git.call_count == 2  # One add command per file
    
    @pytest.mark.asyncio
    async def test_create_commit(self, git_integration):
        """Test commit creation"""
        # Mock git commands
        with patch.object(git_integration, '_run_git_command') as mock_git, \
             patch.object(git_integration, '_get_current_commit_hash') as mock_hash:
            mock_git.return_value = ""
            mock_hash.return_value = "abc123def456"
            
            # Execute
            commit_hash = await git_integration.create_commit(
                message="Test commit",
                agent_type="feature_builder",
                task_id="test-task"
            )
            
            # Assert
            assert commit_hash == "abc123def456"
            # Should call config commands and commit command
            assert mock_git.call_count >= 3
    
    @pytest.mark.asyncio
    async def test_validate_commit_readiness(self, git_integration):
        """Test commit validation"""
        # Mock file system
        with patch('pathlib.Path.exists') as mock_exists, \
             patch('pathlib.Path.stat') as mock_stat:
            mock_exists.return_value = True
            mock_stat.return_value = Mock(st_size=1024)  # 1KB file
            
            # Execute
            result = await git_integration.validate_commit_readiness(["test.py"])
            
            # Assert
            assert result["ready"] is True
            assert result["file_count"] == 1
            assert len(result["issues"]) == 0


class TestMetricsCalculator:
    """Test metrics calculation functionality"""
    
    def test_calculate_success_rate(self):
        """Test success rate calculation"""
        # Setup
        tasks = [
            Mock(status=TaskStatus.COMPLETED.value),
            Mock(status=TaskStatus.COMPLETED.value),
            Mock(status=TaskStatus.FAILED.value),
            Mock(status=TaskStatus.RUNNING.value)  # Should be ignored
        ]
        
        # Execute
        success_rate = MetricsCalculator.calculate_success_rate(tasks)
        
        # Assert
        assert success_rate == 2/3  # 2 successful out of 3 completed
    
    def test_calculate_average_execution_time(self):
        """Test execution time calculation"""
        # Setup
        base_time = datetime.utcnow()
        tasks = [
            Mock(
                status=TaskStatus.COMPLETED.value,
                started_at=base_time,
                completed_at=base_time + timedelta(seconds=60)
            ),
            Mock(
                status=TaskStatus.COMPLETED.value,
                started_at=base_time,
                completed_at=base_time + timedelta(seconds=120)
            ),
            Mock(status=TaskStatus.RUNNING.value)  # Should be ignored
        ]
        
        # Execute
        avg_time = MetricsCalculator.calculate_average_execution_time(tasks)
        
        # Assert
        assert avg_time == 90.0  # (60 + 120) / 2
    
    def test_calculate_code_quality_score(self):
        """Test code quality score calculation"""
        # Setup
        artifacts = [
            Mock(
                artifact_type="code",
                language="python",
                content='def test():\n    """Test function"""\n    try:\n        return 42\n    except:\n        pass'
            ),
            Mock(
                artifact_type="config",
                content="config data"
            )
        ]
        
        # Execute
        score = MetricsCalculator.calculate_code_quality_score(artifacts)
        
        # Assert
        assert score > 1.0  # Should have bonus points for docstring, error handling
        assert score <= 2.0  # Maximum possible score
    
    def test_calculate_user_satisfaction_proxy(self):
        """Test user satisfaction calculation"""
        # Setup - high quality tasks
        tasks = [
            Mock(
                status=TaskStatus.COMPLETED.value,
                confidence_score=0.9
            ),
            Mock(
                status=TaskStatus.COMPLETED.value,
                confidence_score=0.8
            ),
            Mock(
                status=TaskStatus.CANCELLED.value,
                confidence_score=None
            )
        ]
        
        # Execute
        satisfaction = MetricsCalculator.calculate_user_satisfaction_proxy(tasks)
        
        # Assert
        assert satisfaction > 0.5  # Should be relatively high
        assert satisfaction <= 1.0


class TestAgentAnalytics:
    """Test agent analytics functionality"""
    
    @pytest.fixture
    def mock_db(self):
        return Mock(spec=Session)
    
    @pytest.fixture
    def analytics(self, mock_db):
        return AgentAnalytics(mock_db)
    
    @pytest.mark.asyncio
    async def test_get_agent_performance_summary(self, analytics, mock_db):
        """Test performance summary generation"""
        # Setup
        mock_tasks = [
            Mock(
                status=TaskStatus.COMPLETED.value,
                estimated_credits=25,
                started_at=datetime.utcnow() - timedelta(seconds=120),
                completed_at=datetime.utcnow(),
                confidence_score=0.8
            ),
            Mock(
                status=TaskStatus.FAILED.value,
                estimated_credits=50,
                started_at=datetime.utcnow() - timedelta(seconds=60),
                completed_at=datetime.utcnow(),
                confidence_score=None
            )
        ]
        
        mock_artifacts = [
            Mock(artifact_type="code", language="python", line_count=50),
            Mock(artifact_type="code", language="javascript", line_count=30)
        ]
        
        mock_db.query.return_value.all.return_value = mock_tasks
        mock_db.query.return_value.filter.return_value.all.return_value = mock_artifacts
        
        # Execute
        result = await analytics.get_agent_performance_summary(
            agent_type=AgentType.FEATURE_BUILDER,
            time_range_days=30
        )
        
        # Assert
        assert "summary" in result
        assert result["summary"]["total_tasks"] == 2
        assert result["summary"]["success_rate"] == 0.5
        assert "artifacts" in result
        assert result["artifacts"]["total_files_generated"] == 2


if __name__ == "__main__":
    pytest.main([__file__])