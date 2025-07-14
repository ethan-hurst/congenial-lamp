"""
Agent Orchestrator - Coordinates all AI agents and manages workflows
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import logging

from sqlalchemy.orm import Session

from ...models.ai_agent import (
    AgentType, TaskStatus, TaskPriority, WorkflowType,
    AgentTask, AgentSubtask, AgentWorkflow, CodeContext,
    ImplementationPlan, AgentResult, WorkflowResult
)
from .agents.feature_builder import FeatureBuilderAgent
from .agents.test_writer import TestWriterAgent
from .agents.refactor_agent import RefactorAgent
from .agents.bug_fixer import BugFixerAgent
from .agents.code_reviewer import CodeReviewerAgent
from .agents.documentation_agent import DocumentationAgent
from .context_builder import ContextBuilder

logger = logging.getLogger(__name__)


class Constraint:
    """Constraint for agent operations"""
    def __init__(self, type: str, value: Any, description: str = ""):
        self.type = type
        self.value = value
        self.description = description


class Workflow:
    """Workflow definition"""
    def __init__(self, workflow_type: WorkflowType, steps: List[Dict]):
        self.workflow_type = workflow_type
        self.steps = steps
        self.current_step = 0
        self.results = []


class AgentOrchestrator:
    """
    Orchestrates multiple AI agents to work together on complex tasks.
    Manages task distribution, coordination, and result aggregation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.context_builder = ContextBuilder(db)
        
        # Initialize agents
        self.agents = {
            AgentType.FEATURE_BUILDER: FeatureBuilderAgent(db),
            AgentType.TEST_WRITER: TestWriterAgent(db),
            AgentType.REFACTOR: RefactorAgent(db),
            AgentType.BUG_FIXER: BugFixerAgent(db),
            AgentType.CODE_REVIEWER: CodeReviewerAgent(db),
            AgentType.DOCUMENTATION: DocumentationAgent(db)
        }
        
        # Task queue and execution tracking
        self.task_queue = asyncio.Queue()
        self.active_tasks: Dict[str, AgentTask] = {}
        self.task_results: Dict[str, AgentResult] = {}
        
        # Workflow templates
        self.workflow_templates = {
            WorkflowType.FEATURE_DEVELOPMENT: [
                {"agent": AgentType.FEATURE_BUILDER, "action": "plan_and_implement"},
                {"agent": AgentType.TEST_WRITER, "action": "generate_tests"},
                {"agent": AgentType.CODE_REVIEWER, "action": "review_code"},
                {"agent": AgentType.DOCUMENTATION, "action": "generate_docs"}
            ],
            WorkflowType.TEST_GENERATION: [
                {"agent": AgentType.TEST_WRITER, "action": "analyze_and_generate"},
                {"agent": AgentType.CODE_REVIEWER, "action": "review_tests"}
            ],
            WorkflowType.CODE_IMPROVEMENT: [
                {"agent": AgentType.REFACTOR, "action": "analyze_and_refactor"},
                {"agent": AgentType.TEST_WRITER, "action": "update_tests"},
                {"agent": AgentType.CODE_REVIEWER, "action": "review_changes"}
            ],
            WorkflowType.BUG_FIXING: [
                {"agent": AgentType.BUG_FIXER, "action": "analyze_and_fix"},
                {"agent": AgentType.TEST_WRITER, "action": "generate_regression_tests"},
                {"agent": AgentType.CODE_REVIEWER, "action": "review_fix"}
            ]
        }
    
    async def execute_task(
        self,
        task_type: AgentType,
        context: CodeContext,
        requirements: str,
        constraints: List[Constraint],
        user_id: str,
        project_id: str,
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> AgentResult:
        """Execute a single agent task"""
        
        # Create task record
        task = AgentTask(
            project_id=project_id,
            user_id=user_id,
            agent_type=task_type.value,
            task_type="single_agent",
            status=TaskStatus.PENDING.value,
            priority=priority.value,
            title=f"{task_type.value} task",
            description=requirements[:500],
            requirements=requirements,
            constraints=[c.__dict__ for c in constraints],
            context={
                "file_paths": context.file_paths if hasattr(context, 'file_paths') else [],
                "scope": context.scope if hasattr(context, 'scope') else "file"
            }
        )
        
        self.db.add(task)
        self.db.commit()
        
        # Add to active tasks
        self.active_tasks[task.id] = task
        
        try:
            # Update task status
            task.status = TaskStatus.RUNNING.value
            task.started_at = datetime.utcnow()
            self.db.commit()
            
            # Get the appropriate agent
            agent = self.agents.get(task_type)
            if not agent:
                raise ValueError(f"No agent found for type: {task_type}")
            
            # Execute the task
            result = await agent.execute(
                context=context,
                requirements=requirements,
                constraints=constraints,
                task_id=task.id
            )
            
            # Update task with results
            task.status = TaskStatus.COMPLETED.value
            task.completed_at = datetime.utcnow()
            task.execution_time_ms = int(
                (task.completed_at - task.started_at).total_seconds() * 1000
            )
            task.result = result.__dict__ if hasattr(result, '__dict__') else {"output": str(result)}
            task.confidence_score = result.metrics.get('confidence', 0.0) if hasattr(result, 'metrics') else 0.0
            
            self.db.commit()
            
            return result
            
        except Exception as e:
            # Handle task failure
            task.status = TaskStatus.FAILED.value
            task.error_message = str(e)
            task.completed_at = datetime.utcnow()
            self.db.commit()
            
            logger.error(f"Task {task.id} failed: {str(e)}")
            
            return AgentResult(
                success=False,
                output=None,
                artifacts=[],
                metrics={"error": str(e)}
            )
        
        finally:
            # Remove from active tasks
            self.active_tasks.pop(task.id, None)
    
    async def coordinate_agents(
        self,
        workflow: Workflow,
        context: CodeContext,
        requirements: str,
        user_id: str,
        project_id: str
    ) -> WorkflowResult:
        """Coordinate multiple agents in a workflow"""
        
        # Create workflow record
        workflow_record = AgentWorkflow(
            project_id=project_id,
            user_id=user_id,
            workflow_type=workflow.workflow_type.value,
            name=f"{workflow.workflow_type.value} workflow",
            description=requirements[:500],
            steps=[step for step in workflow.steps],
            status=TaskStatus.PENDING.value
        )
        
        self.db.add(workflow_record)
        self.db.commit()
        
        try:
            # Start workflow
            workflow_record.status = TaskStatus.RUNNING.value
            workflow_record.started_at = datetime.utcnow()
            self.db.commit()
            
            results = []
            
            # Execute each step in the workflow
            for i, step in enumerate(workflow.steps):
                workflow_record.current_step = i
                self.db.commit()
                
                agent_type = step["agent"]
                action = step["action"]
                
                # Create subtask for this step
                subtask = AgentSubtask(
                    parent_task_id=workflow_record.id,
                    agent_type=agent_type.value if isinstance(agent_type, Enum) else agent_type,
                    title=f"{agent_type} - {action}",
                    description=f"Step {i+1} of workflow"
                )
                
                self.db.add(subtask)
                self.db.commit()
                
                # Execute the step
                subtask.status = TaskStatus.RUNNING.value
                subtask.started_at = datetime.utcnow()
                self.db.commit()
                
                try:
                    agent = self.agents.get(agent_type)
                    if not agent:
                        raise ValueError(f"No agent found for type: {agent_type}")
                    
                    # Pass results from previous steps as context
                    step_context = {
                        "original_context": context,
                        "requirements": requirements,
                        "previous_results": results
                    }
                    
                    result = await agent.execute_action(
                        action=action,
                        context=step_context,
                        task_id=subtask.id
                    )
                    
                    results.append(result)
                    
                    # Update subtask
                    subtask.status = TaskStatus.COMPLETED.value
                    subtask.completed_at = datetime.utcnow()
                    subtask.output_data = result.__dict__ if hasattr(result, '__dict__') else {"output": str(result)}
                    self.db.commit()
                    
                except Exception as e:
                    subtask.status = TaskStatus.FAILED.value
                    subtask.error_message = str(e)
                    subtask.completed_at = datetime.utcnow()
                    self.db.commit()
                    
                    logger.error(f"Workflow step {i} failed: {str(e)}")
                    
                    # Decide whether to continue or fail the workflow
                    if step.get("required", True):
                        raise e
            
            # Complete workflow
            workflow_record.status = TaskStatus.COMPLETED.value
            workflow_record.completed_at = datetime.utcnow()
            workflow_record.results = [r.__dict__ if hasattr(r, '__dict__') else {"output": str(r)} for r in results]
            self.db.commit()
            
            return WorkflowResult(
                success=True,
                steps_completed=len(results),
                results=results
            )
            
        except Exception as e:
            workflow_record.status = TaskStatus.FAILED.value
            workflow_record.completed_at = datetime.utcnow()
            self.db.commit()
            
            return WorkflowResult(
                success=False,
                steps_completed=workflow_record.current_step,
                results=[]
            )
    
    async def create_workflow(
        self,
        workflow_type: WorkflowType,
        customizations: Optional[Dict] = None
    ) -> Workflow:
        """Create a workflow from template with optional customizations"""
        
        template = self.workflow_templates.get(workflow_type)
        if not template:
            raise ValueError(f"No template found for workflow type: {workflow_type}")
        
        steps = template.copy()
        
        # Apply customizations if provided
        if customizations:
            # Add/remove/modify steps based on customizations
            if "additional_steps" in customizations:
                steps.extend(customizations["additional_steps"])
            
            if "skip_steps" in customizations:
                steps = [s for s in steps if s["action"] not in customizations["skip_steps"]]
        
        return Workflow(workflow_type, steps)
    
    async def get_task_status(self, task_id: str) -> Dict:
        """Get the current status of a task"""
        
        task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if not task:
            # Check if it's a workflow
            workflow = self.db.query(AgentWorkflow).filter(AgentWorkflow.id == task_id).first()
            if workflow:
                return {
                    "id": workflow.id,
                    "type": "workflow",
                    "workflow_type": workflow.workflow_type,
                    "status": workflow.status,
                    "current_step": workflow.current_step,
                    "total_steps": len(workflow.steps),
                    "started_at": workflow.started_at,
                    "completed_at": workflow.completed_at
                }
            
            return {"error": "Task not found"}
        
        return {
            "id": task.id,
            "type": "task",
            "agent_type": task.agent_type,
            "status": task.status,
            "progress": task.progress,
            "current_step": task.current_step,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "error_message": task.error_message
        }
    
    async def get_task_logs(self, task_id: str) -> List[str]:
        """Get logs for a task"""
        
        task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if task and task.logs:
            return task.logs
        
        return []
    
    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task"""
        
        task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
        if not task:
            workflow = self.db.query(AgentWorkflow).filter(AgentWorkflow.id == task_id).first()
            if workflow and workflow.status == TaskStatus.RUNNING.value:
                workflow.status = TaskStatus.CANCELLED.value
                workflow.completed_at = datetime.utcnow()
                self.db.commit()
                return True
            return False
        
        if task.status == TaskStatus.RUNNING.value:
            task.status = TaskStatus.CANCELLED.value
            task.completed_at = datetime.utcnow()
            self.db.commit()
            
            # Remove from active tasks
            self.active_tasks.pop(task_id, None)
            
            return True
        
        return False
    
    async def estimate_task(
        self,
        task_type: AgentType,
        context: CodeContext,
        requirements: str
    ) -> Dict:
        """Estimate time and credits for a task"""
        
        agent = self.agents.get(task_type)
        if not agent:
            return {"error": "Invalid agent type"}
        
        # Get agent estimate
        estimate = await agent.estimate_task(context, requirements)
        
        return {
            "estimated_time": estimate.get("time", 60),  # seconds
            "estimated_credits": estimate.get("credits", 10),
            "complexity": estimate.get("complexity", "medium"),
            "confidence": estimate.get("confidence", 0.7)
        }