"""
Data models for Multi-Agent AI System
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from sqlalchemy import Column, String, Float, Integer, Text, JSON, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from ..database.connection import Base
import uuid


class AgentType(str, Enum):
    """Types of AI agents"""
    FEATURE_BUILDER = "feature_builder"
    TEST_WRITER = "test_writer"
    REFACTOR = "refactor"
    BUG_FIXER = "bug_fixer"
    CODE_REVIEWER = "code_reviewer"
    DOCUMENTATION = "documentation"


class TaskStatus(str, Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WorkflowType(str, Enum):
    """Workflow types"""
    FEATURE_DEVELOPMENT = "feature_development"
    TEST_GENERATION = "test_generation"
    CODE_IMPROVEMENT = "code_improvement"
    BUG_FIXING = "bug_fixing"
    DOCUMENTATION_UPDATE = "documentation_update"


class AgentTask(Base):
    """Model for AI agent tasks"""
    __tablename__ = "agent_tasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    agent_type = Column(String, nullable=False)
    task_type = Column(String, nullable=False)
    status = Column(String, default=TaskStatus.PENDING)
    priority = Column(String, default=TaskPriority.MEDIUM)
    
    # Task details
    title = Column(String, nullable=False)
    description = Column(Text)
    requirements = Column(Text)
    constraints = Column(JSON)
    context = Column(JSON)
    
    # Execution details
    assigned_agent_id = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    execution_time_ms = Column(Integer)
    
    # Results
    result = Column(JSON)
    output_files = Column(JSON)
    error_message = Column(Text)
    confidence_score = Column(Float)
    
    # Progress tracking
    progress = Column(Float, default=0.0)
    current_step = Column(String)
    steps_completed = Column(JSON)
    logs = Column(JSON)
    
    # Credits and usage
    estimated_credits = Column(Integer)
    consumed_credits = Column(Integer)
    tokens_used = Column(Integer)
    
    # Relationships
    subtasks = relationship("AgentSubtask", back_populates="parent_task", cascade="all, delete-orphan")
    artifacts = relationship("AgentArtifact", back_populates="task", cascade="all, delete-orphan")
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentSubtask(Base):
    """Model for agent subtasks"""
    __tablename__ = "agent_subtasks"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_task_id = Column(String, ForeignKey("agent_tasks.id"), nullable=False)
    agent_type = Column(String, nullable=False)
    
    title = Column(String, nullable=False)
    description = Column(Text)
    status = Column(String, default=TaskStatus.PENDING)
    progress = Column(Float, default=0.0)
    
    input_data = Column(JSON)
    output_data = Column(JSON)
    error_message = Column(Text)
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    parent_task = relationship("AgentTask", back_populates="subtasks")
    
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentArtifact(Base):
    """Model for agent-generated artifacts"""
    __tablename__ = "agent_artifacts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, ForeignKey("agent_tasks.id"), nullable=False)
    
    artifact_type = Column(String, nullable=False)  # code, test, documentation, etc.
    file_path = Column(String)
    content = Column(Text)
    language = Column(String)
    
    # Metadata
    size_bytes = Column(Integer)
    line_count = Column(Integer)
    complexity_score = Column(Float)
    quality_score = Column(Float)
    
    # Version control
    version = Column(Integer, default=1)
    previous_version_id = Column(String)
    changes_summary = Column(Text)
    
    task = relationship("AgentTask", back_populates="artifacts")
    
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentWorkflow(Base):
    """Model for agent workflows"""
    __tablename__ = "agent_workflows"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False)
    user_id = Column(String, nullable=False)
    
    workflow_type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Workflow definition
    steps = Column(JSON)  # List of workflow steps
    dependencies = Column(JSON)  # Task dependencies
    
    # Execution
    status = Column(String, default=TaskStatus.PENDING)
    current_step = Column(Integer, default=0)
    
    # Results
    results = Column(JSON)
    summary = Column(Text)
    
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CodeContext(Base):
    """Model for code context used by agents"""
    __tablename__ = "code_contexts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String, nullable=False)
    
    # Context scope
    scope = Column(String)  # file, directory, project
    file_paths = Column(JSON)
    
    # Semantic understanding
    symbols = Column(JSON)  # Classes, functions, variables
    dependencies = Column(JSON)  # Imports, requires
    architecture = Column(JSON)  # Patterns, structure
    
    # Code metrics
    total_lines = Column(Integer)
    total_files = Column(Integer)
    languages = Column(JSON)
    frameworks = Column(JSON)
    
    # Indexing
    last_indexed_at = Column(DateTime)
    index_version = Column(Integer, default=1)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentCapability(Base):
    """Model for agent capabilities and configurations"""
    __tablename__ = "agent_capabilities"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type = Column(String, unique=True, nullable=False)
    
    # Capabilities
    supported_languages = Column(JSON)
    supported_frameworks = Column(JSON)
    supported_patterns = Column(JSON)
    max_file_size = Column(Integer)
    max_context_size = Column(Integer)
    
    # Configuration
    default_model = Column(String)
    temperature = Column(Float)
    max_tokens = Column(Integer)
    
    # Performance metrics
    average_completion_time = Column(Float)
    success_rate = Column(Float)
    average_quality_score = Column(Float)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Non-SQLAlchemy models for runtime use

class ImplementationPlan:
    """Plan for feature implementation"""
    def __init__(self, steps: List[Dict], estimated_time: int, complexity: str):
        self.steps = steps
        self.estimated_time = estimated_time
        self.complexity = complexity
        self.dependencies = []
        self.risks = []


class QualityReport:
    """Code quality analysis report"""
    def __init__(self, score: float, issues: List[Dict], improvements: List[Dict]):
        self.score = score
        self.issues = issues
        self.improvements = improvements
        self.metrics = {}


class TestSuite:
    """Generated test suite"""
    def __init__(self, tests: List[Dict], coverage: float, framework: str):
        self.tests = tests
        self.coverage = coverage
        self.framework = framework
        self.test_files = []


class RefactoringSuggestion:
    """Refactoring suggestion"""
    def __init__(self, type: str, description: str, impact: str, changes: List[Dict]):
        self.type = type
        self.description = description
        self.impact = impact
        self.changes = changes
        self.estimated_improvement = 0.0


class AgentResult:
    """Result from agent execution"""
    def __init__(self, success: bool, output: Any, artifacts: List[Dict], metrics: Dict):
        self.success = success
        self.output = output
        self.artifacts = artifacts
        self.metrics = metrics
        self.suggestions = []


class WorkflowResult:
    """Result from workflow execution"""
    def __init__(self, success: bool, steps_completed: int, results: List[AgentResult]):
        self.success = success
        self.steps_completed = steps_completed
        self.results = results
        self.summary = ""