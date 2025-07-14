"""
Base Agent class for all AI development agents
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
from sqlalchemy.orm import Session
import logging

from ....models.ai_agent import CodeContext, AgentResult
from ..sandbox import CodeSandbox, get_sandbox
from ..git_integration import get_agent_git_workflow, AgentGitWorkflow

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Base class for all AI development agents
    
    Provides common functionality like progress tracking, logging,
    sandbox execution, and result management.
    """
    
    def __init__(self, db: Session, project_root: str = "/tmp/codeforge_projects"):
        self.db = db
        self.sandbox = get_sandbox()
        self.project_root = project_root
        self.git_workflow: Optional[AgentGitWorkflow] = None
        self.progress_callback: Optional[Callable[[float, str], None]] = None
        self.log_callback: Optional[Callable[[str], None]] = None
        
        # Initialize Git workflow if project root exists
        try:
            self.git_workflow = get_agent_git_workflow(project_root)
        except Exception as e:
            logger.warning(f"Git integration not available: {e}")
            self.git_workflow = None
    
    def set_callbacks(
        self,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ):
        """Set progress and logging callbacks"""
        self.progress_callback = progress_callback
        self.log_callback = log_callback
    
    def log(self, message: str):
        """Log a message"""
        logger.info(message)
        if self.log_callback:
            self.log_callback(message)
    
    def update_progress(self, progress: float, message: str):
        """Update progress"""
        if self.progress_callback:
            self.progress_callback(progress, message)
    
    async def execute(
        self,
        context: CodeContext,
        requirements: str,
        constraints: List[Any],
        task_id: str,
        progress_callback: Optional[Callable[[float, str], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> AgentResult:
        """
        Execute the agent's main task
        
        Args:
            context: Code context and environment
            requirements: Task requirements
            constraints: Execution constraints
            task_id: Unique task identifier
            progress_callback: Progress update callback
            log_callback: Log message callback
        
        Returns:
            Agent execution result
        """
        self.set_callbacks(progress_callback, log_callback)
        
        try:
            self.log(f"Starting {self.__class__.__name__} execution")
            self.update_progress(0.1, "Initializing agent")
            
            result = await self._execute_impl(context, requirements, constraints, task_id)
            
            self.update_progress(1.0, "Agent execution completed")
            self.log("Agent execution completed successfully")
            
            return result
            
        except Exception as e:
            self.log(f"Agent execution failed: {str(e)}")
            raise
    
    @abstractmethod
    async def _execute_impl(
        self,
        context: CodeContext,
        requirements: str,
        constraints: List[Any],
        task_id: str
    ) -> AgentResult:
        """
        Implement the agent's specific execution logic
        
        This method must be implemented by each agent
        """
        pass
    
    async def execute_action(
        self,
        action: str,
        context: Dict[str, Any],
        task_id: str
    ) -> AgentResult:
        """
        Execute a specific action within a workflow
        
        Args:
            action: Action to execute
            context: Execution context
            task_id: Task identifier
        
        Returns:
            Action execution result
        """
        try:
            self.log(f"Executing action: {action}")
            result = await self._execute_action_impl(action, context, task_id)
            self.log(f"Action {action} completed")
            return result
            
        except Exception as e:
            self.log(f"Action {action} failed: {str(e)}")
            raise
    
    @abstractmethod
    async def _execute_action_impl(
        self,
        action: str,
        context: Dict[str, Any],
        task_id: str
    ) -> AgentResult:
        """
        Implement action-specific execution logic
        
        This method must be implemented by each agent
        """
        pass
    
    async def estimate_task(
        self,
        context: CodeContext,
        requirements: str
    ) -> Dict[str, Any]:
        """
        Estimate task complexity, time, and resource requirements
        
        Args:
            context: Code context
            requirements: Task requirements
        
        Returns:
            Estimation metrics
        """
        # Default estimation logic - agents can override
        complexity = self._estimate_complexity(requirements)
        
        base_time = {
            "low": 60,      # 1 minute
            "medium": 180,  # 3 minutes
            "high": 300     # 5 minutes
        }.get(complexity, 180)
        
        base_credits = {
            "low": 10,
            "medium": 25,
            "high": 50
        }.get(complexity, 25)
        
        return {
            "time": base_time,
            "credits": base_credits,
            "complexity": complexity,
            "confidence": 0.7
        }
    
    def _estimate_complexity(self, requirements: str) -> str:
        """Estimate task complexity based on requirements"""
        req_lower = requirements.lower()
        
        # High complexity indicators
        high_keywords = [
            "complex", "advanced", "multiple", "integrate", "architecture",
            "performance", "security", "scalable", "enterprise"
        ]
        
        # Low complexity indicators
        low_keywords = [
            "simple", "basic", "single", "small", "quick", "minor"
        ]
        
        high_count = sum(1 for keyword in high_keywords if keyword in req_lower)
        low_count = sum(1 for keyword in low_keywords if keyword in req_lower)
        
        if high_count > low_count:
            return "high"
        elif low_count > high_count:
            return "low"
        else:
            return "medium"
    
    async def execute_code_safely(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
        files: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute code in sandboxed environment
        
        Args:
            code: Code to execute
            language: Programming language
            input_data: Optional input data
            files: Optional additional files
        
        Returns:
            Execution result
        """
        self.log(f"Executing {language} code in sandbox")
        
        try:
            result = await self.sandbox.execute_code(
                code=code,
                language=language,
                input_data=input_data,
                files=files
            )
            
            if result["success"]:
                self.log("Code executed successfully")
            else:
                self.log(f"Code execution failed: {result['error']}")
            
            return result
            
        except Exception as e:
            self.log(f"Sandbox execution error: {str(e)}")
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "return_code": -1,
                "execution_time": 0,
                "language": language,
                "sandbox_type": "error"
            }
    
    def analyze_code_structure(self, file_content: str, language: str = "python") -> Dict[str, Any]:
        """
        Analyze code structure to understand existing patterns
        
        Args:
            file_content: Content of the file to analyze
            language: Programming language
        
        Returns:
            Code analysis results
        """
        if language == "python":
            return self._analyze_python_structure(file_content)
        elif language in ["javascript", "typescript"]:
            return self._analyze_js_structure(file_content)
        else:
            return {"functions": [], "classes": [], "imports": [], "complexity": "unknown"}
    
    def _analyze_python_structure(self, content: str) -> Dict[str, Any]:
        """Analyze Python code structure"""
        import ast
        
        try:
            tree = ast.parse(content)
            functions = []
            classes = []
            imports = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    })
                elif isinstance(node, ast.ClassDef):
                    classes.append({
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                    })
                elif isinstance(node, ast.Import):
                    imports.extend([alias.name for alias in node.names])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            return {
                "functions": functions,
                "classes": classes,
                "imports": imports,
                "complexity": "medium" if len(functions) + len(classes) > 5 else "low"
            }
            
        except SyntaxError:
            return {"functions": [], "classes": [], "imports": [], "complexity": "unknown"}
    
    def _analyze_js_structure(self, content: str) -> Dict[str, Any]:
        """Analyze JavaScript/TypeScript code structure"""
        # Simple regex-based analysis for JS/TS
        import re
        
        functions = re.findall(r'function\s+(\w+)\s*\(', content)
        classes = re.findall(r'class\s+(\w+)', content)
        imports = re.findall(r'import.*from\s+[\'"]([^\'"]+)[\'"]', content)
        
        return {
            "functions": [{"name": f, "line": 0, "args": []} for f in functions],
            "classes": [{"name": c, "line": 0, "methods": []} for c in classes],
            "imports": imports,
            "complexity": "medium" if len(functions) + len(classes) > 5 else "low"
        }
    
    async def commit_changes(
        self,
        task_id: str,
        artifacts: List[Dict],
        commit_message: str,
        auto_pr: bool = False
    ) -> Dict[str, Any]:
        """
        Commit generated code changes to Git
        
        Args:
            task_id: Task identifier
            artifacts: Generated artifacts to commit
            commit_message: Commit message
            auto_pr: Whether to prepare for PR
            
        Returns:
            Git workflow results
        """
        if not self.git_workflow:
            self.log("Git integration not available - skipping commit")
            return {"success": False, "error": "Git not available"}
        
        try:
            self.log("Committing changes to Git")
            self.update_progress(0.9, "Committing to Git")
            
            # Convert artifacts to file format
            files_to_commit = []
            for artifact in artifacts:
                if isinstance(artifact, dict) and "path" in artifact and "content" in artifact:
                    files_to_commit.append({
                        "path": artifact["path"],
                        "content": artifact["content"]
                    })
            
            if not files_to_commit:
                self.log("No files to commit")
                return {"success": True, "files_committed": 0}
            
            # Execute Git workflow
            result = await self.git_workflow.execute_agent_workflow(
                agent_type=self.__class__.__name__.replace("Agent", "").lower(),
                task_id=task_id,
                files_created=files_to_commit,
                commit_message=commit_message,
                auto_pr=auto_pr
            )
            
            if result["success"]:
                self.log(f"Successfully committed {len(result['files_committed'])} files")
                if result.get("pr_ready"):
                    self.log("Branch ready for pull request")
            else:
                self.log(f"Git commit failed: {'; '.join(result['errors'])}")
            
            return result
            
        except Exception as e:
            error_msg = f"Git commit error: {str(e)}"
            self.log(error_msg)
            return {"success": False, "error": error_msg}
    
    def create_result(
        self,
        success: bool,
        output: Any,
        artifacts: Optional[List[Dict]] = None,
        metrics: Optional[Dict] = None,
        suggestions: Optional[List[str]] = None
    ) -> AgentResult:
        """
        Create a standardized agent result
        
        Args:
            success: Whether the operation was successful
            output: Primary output of the operation
            artifacts: Generated artifacts (files, code, etc.)
            metrics: Performance and quality metrics
            suggestions: Improvement suggestions
        
        Returns:
            Standardized agent result
        """
        return AgentResult(
            success=success,
            output=output,
            artifacts=artifacts or [],
            metrics=metrics or {},
            suggestions=suggestions or [],
            agent_type=self.__class__.__name__
        )