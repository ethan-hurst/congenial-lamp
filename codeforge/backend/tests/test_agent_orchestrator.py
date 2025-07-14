"""
Tests for Agent Orchestrator
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
import uuid

from src.services.ai.orchestrator import AgentOrchestrator, Workflow, WorkflowStep
from src.services.ai.base import CodeContext, AgentType, WorkflowType, TaskStatus, TaskPriority
from src.services.ai.context_builder import FileContext, ProjectContext
from src.models.ai_agent import AgentTask, AgentWorkflow


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = MagicMock()
    db.query = MagicMock()
    return db


@pytest.fixture
def orchestrator(mock_db):
    """Create orchestrator instance"""
    return AgentOrchestrator(mock_db)


@pytest.fixture
def sample_context():
    """Create sample code context"""
    return CodeContext(
        project_id="test-project",
        files=[
            FileContext(
                path="src/main.py",
                content="def main():\n    print('Hello')",
                language="python",
                size=30,
                last_modified=datetime.now()
            )
        ],
        project_structure=ProjectContext(
            root_path="/test/project",
            directories=["src", "tests"],
            total_files=10,
            languages={"python": 8, "yaml": 2}
        ),
        dependencies={"flask": "2.0.0", "pytest": "7.0.0"},
        test_coverage={"overall": 75.0, "files": {}}
    )


class TestAgentOrchestrator:
    """Test Agent Orchestrator functionality"""
    
    @pytest.mark.asyncio
    async def test_create_workflow_feature_development(self, orchestrator):
        """Test creating feature development workflow"""
        workflow = await orchestrator.create_workflow(WorkflowType.FEATURE_DEVELOPMENT)
        
        assert workflow.type == WorkflowType.FEATURE_DEVELOPMENT
        assert len(workflow.steps) == 5
        assert workflow.steps[0].agent_type == AgentType.FEATURE_BUILDER
        assert workflow.steps[1].agent_type == AgentType.TEST_WRITER
        assert workflow.steps[2].agent_type == AgentType.CODE_REVIEWER
        assert workflow.steps[3].agent_type == AgentType.REFACTOR
        assert workflow.steps[4].agent_type == AgentType.DOCUMENTATION
    
    @pytest.mark.asyncio
    async def test_create_workflow_test_generation(self, orchestrator):
        """Test creating test generation workflow"""
        workflow = await orchestrator.create_workflow(WorkflowType.TEST_GENERATION)
        
        assert workflow.type == WorkflowType.TEST_GENERATION
        assert len(workflow.steps) == 3
        assert workflow.steps[0].agent_type == AgentType.TEST_WRITER
        assert workflow.steps[1].agent_type == AgentType.CODE_REVIEWER
        assert workflow.steps[2].agent_type == AgentType.DOCUMENTATION
    
    @pytest.mark.asyncio
    async def test_create_workflow_with_customizations(self, orchestrator):
        """Test creating workflow with customizations"""
        customizations = {
            "skip_tests": True,
            "skip_docs": True
        }
        
        workflow = await orchestrator.create_workflow(
            WorkflowType.FEATURE_DEVELOPMENT,
            customizations
        )
        
        # Should skip test writer and documentation steps
        agent_types = [step.agent_type for step in workflow.steps]
        assert AgentType.TEST_WRITER not in agent_types
        assert AgentType.DOCUMENTATION not in agent_types
    
    @pytest.mark.asyncio
    async def test_estimate_task(self, orchestrator, sample_context):
        """Test task estimation"""
        with patch.object(orchestrator.feature_builder, 'estimate_task') as mock_estimate:
            mock_estimate.return_value = {
                "estimated_time": 300,
                "estimated_credits": 50,
                "complexity": "medium"
            }
            
            estimate = await orchestrator.estimate_task(
                AgentType.FEATURE_BUILDER,
                sample_context,
                "Build a REST API"
            )
            
            assert estimate["estimated_time"] == 300
            assert estimate["estimated_credits"] == 50
            assert estimate["complexity"] == "medium"
            mock_estimate.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_task_feature_builder(self, orchestrator, sample_context, mock_db):
        """Test executing feature builder task"""
        mock_task = MagicMock(id="task-123")
        mock_db.query().filter().first.return_value = mock_task
        
        with patch.object(orchestrator.feature_builder, 'execute') as mock_execute:
            mock_execute.return_value = {
                "status": "completed",
                "files_modified": ["src/api.py"],
                "tests_added": ["tests/test_api.py"]
            }
            
            result = await orchestrator.execute_task(
                AgentType.FEATURE_BUILDER,
                sample_context,
                "Build a REST API",
                [],
                "user-123",
                "project-123"
            )
            
            assert result["status"] == "completed"
            assert "files_modified" in result
            mock_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_task_error_handling(self, orchestrator, sample_context, mock_db):
        """Test task execution error handling"""
        mock_task = MagicMock(id="task-123")
        mock_db.query().filter().first.return_value = mock_task
        
        with patch.object(orchestrator.feature_builder, 'execute') as mock_execute:
            mock_execute.side_effect = Exception("Test error")
            
            result = await orchestrator.execute_task(
                AgentType.FEATURE_BUILDER,
                sample_context,
                "Build a REST API",
                [],
                "user-123",
                "project-123"
            )
            
            assert result["status"] == "failed"
            assert "error" in result
            assert result["error"] == "Test error"
    
    @pytest.mark.asyncio
    async def test_coordinate_agents_workflow(self, orchestrator, sample_context, mock_db):
        """Test coordinating agents in a workflow"""
        workflow = Workflow(
            type=WorkflowType.TEST_GENERATION,
            steps=[
                WorkflowStep(
                    agent_type=AgentType.TEST_WRITER,
                    name="Generate Tests",
                    requirements="Generate unit tests"
                ),
                WorkflowStep(
                    agent_type=AgentType.CODE_REVIEWER,
                    name="Review Tests",
                    requirements="Review generated tests"
                )
            ]
        )
        
        mock_workflow_task = MagicMock(id="workflow-123")
        mock_db.query().filter().first.return_value = mock_workflow_task
        
        with patch.object(orchestrator.test_writer, 'execute') as mock_test_execute, \
             patch.object(orchestrator.code_reviewer, 'execute') as mock_review_execute:
            
            mock_test_execute.return_value = {
                "status": "completed",
                "tests_generated": 5
            }
            mock_review_execute.return_value = {
                "status": "completed",
                "issues_found": 0
            }
            
            results = await orchestrator.coordinate_agents(
                workflow,
                sample_context,
                "Generate tests for main.py",
                "user-123",
                "project-123"
            )
            
            assert len(results) == 2
            assert results[0]["status"] == "completed"
            assert results[1]["status"] == "completed"
            mock_test_execute.assert_called_once()
            mock_review_execute.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_get_task_status_not_found(self, orchestrator, mock_db):
        """Test getting status of non-existent task"""
        mock_db.query().filter().first.return_value = None
        
        status = await orchestrator.get_task_status("invalid-task-id")
        
        assert "error" in status
        assert status["error"] == "Task not found"
    
    @pytest.mark.asyncio
    async def test_get_task_status_agent_task(self, orchestrator, mock_db):
        """Test getting status of agent task"""
        mock_task = MagicMock(
            id="task-123",
            status=TaskStatus.RUNNING.value,
            progress=0.5,
            current_step="Processing files"
        )
        mock_db.query().filter().first.side_effect = [mock_task, None]
        
        status = await orchestrator.get_task_status("task-123")
        
        assert status["type"] == "task"
        assert status["status"] == TaskStatus.RUNNING.value
        assert status["progress"] == 0.5
        assert status["current_step"] == "Processing files"
    
    @pytest.mark.asyncio
    async def test_cancel_task_running(self, orchestrator, mock_db):
        """Test cancelling a running task"""
        mock_task = MagicMock(
            id="task-123",
            status=TaskStatus.RUNNING.value
        )
        mock_db.query().filter().first.return_value = mock_task
        
        success = await orchestrator.cancel_task("task-123")
        
        assert success is True
        assert mock_task.status == TaskStatus.CANCELLED.value
        mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_cancel_task_completed(self, orchestrator, mock_db):
        """Test cancelling a completed task"""
        mock_task = MagicMock(
            id="task-123",
            status=TaskStatus.COMPLETED.value
        )
        mock_db.query().filter().first.return_value = mock_task
        
        success = await orchestrator.cancel_task("task-123")
        
        assert success is False
        assert mock_task.status == TaskStatus.COMPLETED.value
    
    @pytest.mark.asyncio
    async def test_get_task_logs(self, orchestrator):
        """Test getting task logs"""
        task_id = "task-123"
        
        # Add some logs
        orchestrator._task_logs[task_id] = [
            {"timestamp": "2024-01-01T10:00:00", "message": "Task started"},
            {"timestamp": "2024-01-01T10:01:00", "message": "Processing files"},
            {"timestamp": "2024-01-01T10:02:00", "message": "Task completed"}
        ]
        
        logs = await orchestrator.get_task_logs(task_id)
        
        assert len(logs) == 3
        assert logs[0]["message"] == "Task started"
        assert logs[2]["message"] == "Task completed"
    
    @pytest.mark.asyncio
    async def test_get_task_logs_empty(self, orchestrator):
        """Test getting logs for task with no logs"""
        logs = await orchestrator.get_task_logs("no-logs-task")
        
        assert logs == []