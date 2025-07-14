"""
AI Agents API endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import json
import asyncio

from ...database.connection import get_database_session
from ...auth.dependencies import get_current_user
from ...models.user import User
from ...models.ai_agent import (
    AgentType, TaskStatus, TaskPriority, WorkflowType,
    AgentTask, AgentWorkflow
)
from ...services.ai import AgentOrchestrator, Constraint, Workflow
from ...services.ai.context_builder import ContextBuilder, ContextScope
from ...services.ai.metrics import get_agent_analytics, get_realtime_metrics


router = APIRouter(prefix="/ai/agents", tags=["ai-agents"])


# Request/Response Models
class ConstraintModel(BaseModel):
    """Constraint for agent operations"""
    type: str
    value: Any
    description: Optional[str] = ""


class FeatureBuildRequest(BaseModel):
    """Request to build a feature"""
    requirements: str = Field(..., min_length=10, max_length=5000)
    constraints: List[ConstraintModel] = []
    tech_stack: Optional[Dict[str, Any]] = None
    context_scope: str = "project"
    priority: TaskPriority = TaskPriority.MEDIUM


class TestGenerationRequest(BaseModel):
    """Request to generate tests"""
    file_path: str
    coverage_target: float = Field(0.8, ge=0.0, le=1.0)
    test_types: List[str] = ["unit", "integration"]
    test_framework: Optional[str] = None


class RefactorRequest(BaseModel):
    """Request to refactor code"""
    file_path: str
    refactor_type: Optional[str] = None
    preserve_behavior: bool = True
    max_changes: int = 10


class BugFixRequest(BaseModel):
    """Request to fix a bug"""
    file_path: str
    error_description: str
    stack_trace: Optional[str] = None
    expected_behavior: Optional[str] = None


class WorkflowRequest(BaseModel):
    """Request to execute a workflow"""
    workflow_type: WorkflowType
    requirements: str
    customizations: Optional[Dict[str, Any]] = None
    context_scope: str = "project"


class TaskResponse(BaseModel):
    """Response for task creation"""
    task_id: str
    estimated_time: int
    estimated_credits: int
    status: str


class TaskStatusResponse(BaseModel):
    """Response for task status"""
    id: str
    type: str
    status: str
    progress: float
    current_step: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]
    results: Optional[Dict]


# Initialize services
def get_orchestrator(db: Session = Depends(get_database_session)) -> AgentOrchestrator:
    """Get agent orchestrator instance"""
    return AgentOrchestrator(db)


def get_context_builder(db: Session = Depends(get_database_session)) -> ContextBuilder:
    """Get context builder instance"""
    return ContextBuilder(db)


# Feature building endpoints
@router.post("/feature", response_model=TaskResponse)
async def build_feature(
    project_id: str,
    request: FeatureBuildRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    context_builder: ContextBuilder = Depends(get_context_builder),
    db: Session = Depends(get_database_session)
):
    """
    Build a new feature using AI agents
    """
    try:
        # Build code context
        context = await context_builder.build_context(
            project_id=project_id,
            scope=request.context_scope
        )
        
        # Convert constraints
        constraints = [
            Constraint(c.type, c.value, c.description)
            for c in request.constraints
        ]
        
        # Add tech stack constraint if provided
        if request.tech_stack:
            constraints.append(
                Constraint("tech_stack", request.tech_stack, "Technology stack")
            )
        
        # Estimate task
        estimate = await orchestrator.estimate_task(
            AgentType.FEATURE_BUILDER,
            context,
            request.requirements
        )
        
        # Create task
        task = AgentTask(
            project_id=project_id,
            user_id=current_user.id,
            agent_type=AgentType.FEATURE_BUILDER.value,
            task_type="feature_implementation",
            status=TaskStatus.PENDING.value,
            priority=request.priority.value,
            title="Build Feature",
            description=request.requirements[:200],
            requirements=request.requirements,
            constraints=[c.__dict__ for c in constraints],
            estimated_credits=estimate["estimated_credits"]
        )
        
        db.add(task)
        db.commit()
        
        # Execute task in background
        background_tasks.add_task(
            orchestrator.execute_task,
            AgentType.FEATURE_BUILDER,
            context,
            request.requirements,
            constraints,
            current_user.id,
            project_id,
            request.priority
        )
        
        return TaskResponse(
            task_id=task.id,
            estimated_time=estimate["estimated_time"],
            estimated_credits=estimate["estimated_credits"],
            status=task.status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Test generation endpoints
@router.post("/test", response_model=TaskResponse)
async def generate_tests(
    project_id: str,
    request: TestGenerationRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    context_builder: ContextBuilder = Depends(get_context_builder),
    db: Session = Depends(get_database_session)
):
    """
    Generate tests for code
    """
    try:
        # Build context for specific file
        context = await context_builder.build_context(
            project_id=project_id,
            scope=ContextScope.FILE,
            file_paths=[request.file_path]
        )
        
        # Create constraints
        constraints = [
            Constraint("coverage", request.coverage_target, "Target test coverage"),
            Constraint("test_types", request.test_types, "Types of tests to generate")
        ]
        
        if request.test_framework:
            constraints.append(
                Constraint("test_framework", request.test_framework, "Test framework")
            )
        
        # Estimate task
        estimate = await orchestrator.estimate_task(
            AgentType.TEST_WRITER,
            context,
            f"Generate tests for {request.file_path}"
        )
        
        # Create task
        task = AgentTask(
            project_id=project_id,
            user_id=current_user.id,
            agent_type=AgentType.TEST_WRITER.value,
            task_type="test_generation",
            status=TaskStatus.PENDING.value,
            priority=TaskPriority.HIGH.value,
            title="Generate Tests",
            description=f"Generate tests for {request.file_path}",
            requirements=f"Generate {', '.join(request.test_types)} tests with {request.coverage_target*100}% coverage",
            constraints=[c.__dict__ for c in constraints],
            estimated_credits=estimate["estimated_credits"]
        )
        
        db.add(task)
        db.commit()
        
        # Execute task in background
        background_tasks.add_task(
            orchestrator.execute_task,
            AgentType.TEST_WRITER,
            context,
            task.requirements,
            constraints,
            current_user.id,
            project_id
        )
        
        return TaskResponse(
            task_id=task.id,
            estimated_time=estimate["estimated_time"],
            estimated_credits=estimate["estimated_credits"],
            status=task.status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Refactoring endpoints
@router.post("/refactor", response_model=TaskResponse)
async def refactor_code(
    project_id: str,
    request: RefactorRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    context_builder: ContextBuilder = Depends(get_context_builder),
    db: Session = Depends(get_database_session)
):
    """
    Refactor code to improve quality
    """
    try:
        # Build context
        context = await context_builder.build_context(
            project_id=project_id,
            scope=ContextScope.FILE,
            file_paths=[request.file_path]
        )
        
        # Create constraints
        constraints = [
            Constraint("preserve_behavior", request.preserve_behavior, "Preserve code behavior"),
            Constraint("max_changes", request.max_changes, "Maximum number of changes")
        ]
        
        if request.refactor_type:
            constraints.append(
                Constraint("refactor_type", request.refactor_type, "Type of refactoring")
            )
        
        # Create workflow for code improvement
        workflow = await orchestrator.create_workflow(
            WorkflowType.CODE_IMPROVEMENT
        )
        
        # Create workflow task
        task = AgentWorkflow(
            project_id=project_id,
            user_id=current_user.id,
            workflow_type=WorkflowType.CODE_IMPROVEMENT.value,
            name="Code Refactoring",
            description=f"Refactor {request.file_path}",
            steps=[step for step in workflow.steps],
            status=TaskStatus.PENDING.value
        )
        
        db.add(task)
        db.commit()
        
        # Execute workflow in background
        background_tasks.add_task(
            orchestrator.coordinate_agents,
            workflow,
            context,
            f"Refactor code in {request.file_path}",
            current_user.id,
            project_id
        )
        
        return TaskResponse(
            task_id=task.id,
            estimated_time=300,  # 5 minutes
            estimated_credits=50,
            status=task.status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Bug fixing endpoints
@router.post("/bugfix", response_model=TaskResponse)
async def fix_bug(
    project_id: str,
    request: BugFixRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    context_builder: ContextBuilder = Depends(get_context_builder),
    db: Session = Depends(get_database_session)
):
    """
    Fix a bug in the code
    """
    try:
        # Build context
        context = await context_builder.build_context(
            project_id=project_id,
            scope=ContextScope.FILE,
            file_paths=[request.file_path]
        )
        
        # Create bug fixing workflow
        workflow = await orchestrator.create_workflow(
            WorkflowType.BUG_FIXING
        )
        
        # Prepare bug info
        bug_info = {
            "error": request.error_description,
            "stack_trace": request.stack_trace,
            "expected": request.expected_behavior,
            "file": request.file_path
        }
        
        # Store bug info in context
        context.bug_fix_info = bug_info
        
        # Create workflow task
        task = AgentWorkflow(
            project_id=project_id,
            user_id=current_user.id,
            workflow_type=WorkflowType.BUG_FIXING.value,
            name="Bug Fix",
            description=request.error_description[:200],
            steps=[step for step in workflow.steps],
            status=TaskStatus.PENDING.value
        )
        
        db.add(task)
        db.commit()
        
        # Execute workflow in background
        background_tasks.add_task(
            orchestrator.coordinate_agents,
            workflow,
            context,
            f"Fix bug: {request.error_description}",
            current_user.id,
            project_id
        )
        
        return TaskResponse(
            task_id=task.id,
            estimated_time=240,  # 4 minutes
            estimated_credits=40,
            status=task.status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Workflow endpoints
@router.post("/workflow", response_model=TaskResponse)
async def execute_workflow(
    project_id: str,
    request: WorkflowRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    context_builder: ContextBuilder = Depends(get_context_builder),
    db: Session = Depends(get_database_session)
):
    """
    Execute a complete workflow
    """
    try:
        # Build context
        context = await context_builder.build_context(
            project_id=project_id,
            scope=request.context_scope
        )
        
        # Create workflow with customizations
        workflow = await orchestrator.create_workflow(
            request.workflow_type,
            request.customizations
        )
        
        # Create workflow task
        task = AgentWorkflow(
            project_id=project_id,
            user_id=current_user.id,
            workflow_type=request.workflow_type.value,
            name=f"{request.workflow_type.value} workflow",
            description=request.requirements[:200],
            steps=[step for step in workflow.steps],
            status=TaskStatus.PENDING.value
        )
        
        db.add(task)
        db.commit()
        
        # Execute workflow in background
        background_tasks.add_task(
            orchestrator.coordinate_agents,
            workflow,
            context,
            request.requirements,
            current_user.id,
            project_id
        )
        
        # Estimate based on workflow type
        time_estimates = {
            WorkflowType.FEATURE_DEVELOPMENT: 600,  # 10 minutes
            WorkflowType.TEST_GENERATION: 180,      # 3 minutes
            WorkflowType.CODE_IMPROVEMENT: 300,     # 5 minutes
            WorkflowType.BUG_FIXING: 240           # 4 minutes
        }
        
        credit_estimates = {
            WorkflowType.FEATURE_DEVELOPMENT: 100,
            WorkflowType.TEST_GENERATION: 30,
            WorkflowType.CODE_IMPROVEMENT: 50,
            WorkflowType.BUG_FIXING: 40
        }
        
        return TaskResponse(
            task_id=task.id,
            estimated_time=time_estimates.get(request.workflow_type, 300),
            estimated_credits=credit_estimates.get(request.workflow_type, 50),
            status=task.status
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Task status endpoints
@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    db: Session = Depends(get_database_session)
):
    """
    Get task status and results
    """
    try:
        status = await orchestrator.get_task_status(task_id)
        
        if "error" in status:
            raise HTTPException(status_code=404, detail=status["error"])
        
        # Get full task details
        task = None
        if status["type"] == "task":
            task = db.query(AgentTask).filter(
                AgentTask.id == task_id,
                AgentTask.user_id == current_user.id
            ).first()
        else:
            task = db.query(AgentWorkflow).filter(
                AgentWorkflow.id == task_id,
                AgentWorkflow.user_id == current_user.id
            ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        return TaskStatusResponse(
            id=task.id,
            type=status["type"],
            status=task.status,
            progress=status.get("progress", 0.0),
            current_step=status.get("current_step"),
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error_message=getattr(task, 'error_message', None),
            results=getattr(task, 'result', None) or getattr(task, 'results', None)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}/stream")
async def stream_task_progress(
    task_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    db: Session = Depends(get_database_session)
):
    """
    Stream task progress using Server-Sent Events
    """
    async def event_generator():
        while True:
            try:
                # Get task status
                status = await orchestrator.get_task_status(task_id)
                
                # Get logs
                logs = await orchestrator.get_task_logs(task_id)
                
                # Create event data
                event_data = {
                    "status": status,
                    "logs": logs[-10:] if logs else []  # Last 10 log entries
                }
                
                yield f"data: {json.dumps(event_data)}\n\n"
                
                # Check if task is complete
                if status.get("status") in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value, TaskStatus.CANCELLED.value]:
                    break
                
                # Wait before next update
                await asyncio.sleep(1)
                
            except Exception as e:
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                break
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )


@router.delete("/tasks/{task_id}")
async def cancel_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
    orchestrator: AgentOrchestrator = Depends(get_orchestrator),
    db: Session = Depends(get_database_session)
):
    """
    Cancel a running task
    """
    try:
        # Verify ownership
        task = db.query(AgentTask).filter(
            AgentTask.id == task_id,
            AgentTask.user_id == current_user.id
        ).first()
        
        if not task:
            task = db.query(AgentWorkflow).filter(
                AgentWorkflow.id == task_id,
                AgentWorkflow.user_id == current_user.id
            ).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Cancel task
        success = await orchestrator.cancel_task(task_id)
        
        if success:
            return {"message": "Task cancelled successfully"}
        else:
            return {"message": "Task is not running or already completed"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks")
async def list_tasks(
    project_id: str,
    status: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    List user's tasks
    """
    try:
        query = db.query(AgentTask).filter(
            AgentTask.project_id == project_id,
            AgentTask.user_id == current_user.id
        )
        
        if status:
            query = query.filter(AgentTask.status == status)
        
        # Get total count
        total = query.count()
        
        # Get tasks
        tasks = query.order_by(AgentTask.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "tasks": [
                {
                    "id": task.id,
                    "agent_type": task.agent_type,
                    "title": task.title,
                    "status": task.status,
                    "progress": task.progress,
                    "created_at": task.created_at.isoformat(),
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None
                }
                for task in tasks
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/capabilities")
async def get_agent_capabilities():
    """
    Get capabilities of all agents
    """
    return {
        "agents": {
            "feature_builder": {
                "languages": ["python", "javascript", "typescript", "go", "java"],
                "frameworks": {
                    "python": ["fastapi", "django", "flask"],
                    "javascript": ["react", "vue", "express", "nextjs"],
                    "typescript": ["react", "angular", "nestjs"],
                    "go": ["gin", "echo", "fiber"],
                    "java": ["spring", "springboot"]
                },
                "capabilities": [
                    "Complete feature implementation",
                    "API development",
                    "UI component creation",
                    "Database integration",
                    "Authentication implementation"
                ]
            },
            "test_writer": {
                "frameworks": {
                    "python": ["pytest", "unittest"],
                    "javascript": ["jest", "mocha", "jasmine"],
                    "typescript": ["jest", "jasmine"],
                    "go": ["testing"],
                    "java": ["junit", "testng"]
                },
                "test_types": ["unit", "integration", "e2e", "performance"],
                "capabilities": [
                    "Generate comprehensive test suites",
                    "Edge case identification",
                    "Mock creation",
                    "Coverage analysis"
                ]
            },
            "refactor": {
                "refactorings": [
                    "extract_method",
                    "rename",
                    "simplify_conditional",
                    "remove_duplication",
                    "improve_naming",
                    "add_type_hints",
                    "extract_constant",
                    "decompose_function"
                ],
                "capabilities": [
                    "Code quality improvement",
                    "Performance optimization",
                    "Readability enhancement",
                    "Technical debt reduction"
                ]
            },
            "bug_fixer": {
                "capabilities": [
                    "Root cause analysis",
                    "Error trace analysis",
                    "Fix generation",
                    "Regression prevention"
                ]
            },
            "code_reviewer": {
                "review_categories": [
                    "bugs",
                    "security",
                    "performance",
                    "readability",
                    "best_practices",
                    "documentation"
                ],
                "capabilities": [
                    "Comprehensive code review",
                    "Security vulnerability detection",
                    "Performance issue identification",
                    "Best practice enforcement"
                ]
            },
            "documentation": {
                "doc_types": [
                    "api",
                    "readme",
                    "comments",
                    "architecture",
                    "tutorial"
                ],
                "capabilities": [
                    "API documentation generation",
                    "README creation",
                    "Code commenting",
                    "Architecture documentation"
                ]
            }
        },
        "workflows": {
            "feature_development": {
                "description": "Complete feature development workflow",
                "steps": ["plan", "implement", "test", "review", "document"]
            },
            "test_generation": {
                "description": "Comprehensive test generation",
                "steps": ["analyze", "generate", "review"]
            },
            "code_improvement": {
                "description": "Code quality improvement workflow",
                "steps": ["analyze", "refactor", "test", "review"]
            },
            "bug_fixing": {
                "description": "Bug identification and fixing",
                "steps": ["analyze", "fix", "test", "review"]
            }
        }
    }


# Analytics and Metrics Endpoints

@router.get("/metrics/performance")
async def get_performance_metrics(
    agent_type: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get agent performance metrics"""
    try:
        analytics = get_agent_analytics(db)
        
        agent_type_enum = None
        if agent_type:
            try:
                agent_type_enum = AgentType(agent_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid agent type: {agent_type}")
        
        metrics = await analytics.get_agent_performance_summary(
            agent_type=agent_type_enum,
            time_range_days=days,
            user_id=current_user.id
        )
        
        return metrics
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/usage")
async def get_user_usage_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get user's agent usage metrics"""
    try:
        analytics = get_agent_analytics(db)
        usage = await analytics.get_user_agent_usage(current_user.id, days)
        return usage
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/live")
async def get_live_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get real-time agent metrics"""
    try:
        metrics = get_realtime_metrics(db)
        live_status = await metrics.get_live_agent_status()
        return live_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/tasks/{task_id}/progress")
async def get_task_progress_metrics(
    task_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get detailed progress metrics for a task"""
    try:
        metrics = get_realtime_metrics(db)
        progress = await metrics.get_task_progress_metrics(task_id)
        return progress
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/report")
async def generate_performance_report(
    days: int = Query(30, ge=1, le=365),
    include_insights: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Generate comprehensive performance report"""
    try:
        analytics = get_agent_analytics(db)
        report = await analytics.generate_performance_report(
            user_id=current_user.id,
            days=days
        )
        
        if not include_insights:
            report.pop("insights", None)
        
        return report
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/system")
async def get_system_metrics(
    days: int = Query(7, ge=1, le=30),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get system-wide metrics (admin only)"""
    try:
        # Check if user has admin privileges (simplified check)
        if not current_user.email.endswith("@codeforge.dev"):
            raise HTTPException(status_code=403, detail="Admin access required")
        
        analytics = get_agent_analytics(db)
        metrics = await analytics.get_system_wide_metrics(days)
        return metrics
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))