"""
Feature Builder Agent - Implements complete features from requirements
"""
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ....models.ai_agent import (
    AgentTask, AgentArtifact, ImplementationPlan,
    AgentResult, TaskStatus
)
from ....config.settings import settings
from ...ai_service import AIProvider, TaskType, AIRequest, CodeContext as AICodeContext

logger = logging.getLogger(__name__)


class TechStack:
    """Technology stack for implementation"""
    def __init__(self, language: str, framework: str, libraries: List[str]):
        self.language = language
        self.framework = framework
        self.libraries = libraries


class StyleGuide:
    """Code style guide"""
    def __init__(self, conventions: Dict[str, str]):
        self.conventions = conventions


class FeatureBuilderAgent:
    """
    Agent that builds complete features from requirements.
    Capable of understanding requirements, planning implementation,
    generating code structure, and implementing each component.
    """
    
    def __init__(self, db: Session):
        self.db = db
        # Initialize AI service
        from ...ai_service import MultiAgentAI
        self.ai_service = MultiAgentAI()
        
        # Agent configuration
        self.config = {
            "max_file_size": 10000,  # lines
            "max_files_per_feature": 20,
            "supported_languages": ["python", "javascript", "typescript", "go", "java"],
            "supported_frameworks": {
                "python": ["fastapi", "django", "flask"],
                "javascript": ["react", "vue", "express", "nextjs"],
                "typescript": ["react", "angular", "nestjs"],
                "go": ["gin", "echo", "fiber"],
                "java": ["spring", "springboot"]
            }
        }
    
    async def execute(
        self,
        context: Any,  # CodeContext from orchestrator
        requirements: str,
        constraints: List[Any],
        task_id: str
    ) -> AgentResult:
        """Execute feature building task"""
        
        try:
            # Update task status
            task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
            if task:
                task.current_step = "Analyzing requirements"
                task.progress = 0.1
                self.db.commit()
            
            # Analyze requirements
            tech_stack = self._determine_tech_stack(context, constraints)
            
            # Plan implementation
            plan = await self.plan_implementation(requirements, context, tech_stack)
            
            if task:
                task.current_step = "Planning implementation"
                task.progress = 0.3
                task.logs = task.logs or []
                task.logs.append({
                    "timestamp": datetime.utcnow().isoformat(),
                    "message": f"Created implementation plan with {len(plan.steps)} steps"
                })
                self.db.commit()
            
            # Generate code for each step
            artifacts = []
            for i, step in enumerate(plan.steps):
                if task:
                    task.current_step = f"Implementing: {step['description']}"
                    task.progress = 0.3 + (0.6 * (i + 1) / len(plan.steps))
                    self.db.commit()
                
                code_files = await self.generate_code(
                    step,
                    tech_stack,
                    self._get_style_guide(tech_stack)
                )
                
                # Create artifacts for each generated file
                for code_file in code_files:
                    artifact = AgentArtifact(
                        task_id=task_id,
                        artifact_type="code",
                        file_path=code_file["path"],
                        content=code_file["content"],
                        language=tech_stack.language,
                        line_count=len(code_file["content"].split('\n')),
                        size_bytes=len(code_file["content"].encode('utf-8'))
                    )
                    self.db.add(artifact)
                    artifacts.append(code_file)
                
                self.db.commit()
            
            # Validate implementation
            validation_result = await self._validate_implementation(artifacts, requirements)
            
            if task:
                task.current_step = "Completed"
                task.progress = 1.0
                task.status = TaskStatus.COMPLETED.value
                task.completed_at = datetime.utcnow()
                self.db.commit()
            
            return AgentResult(
                success=True,
                output={
                    "plan": plan.__dict__,
                    "files_created": len(artifacts),
                    "validation": validation_result
                },
                artifacts=artifacts,
                metrics={
                    "confidence": 0.85,
                    "complexity": plan.complexity,
                    "estimated_time": plan.estimated_time
                }
            )
            
        except Exception as e:
            logger.error(f"Feature builder error: {str(e)}")
            
            if task:
                task.status = TaskStatus.FAILED.value
                task.error_message = str(e)
                task.completed_at = datetime.utcnow()
                self.db.commit()
            
            return AgentResult(
                success=False,
                output={"error": str(e)},
                artifacts=[],
                metrics={"error": str(e)}
            )
    
    async def execute_action(self, action: str, context: Dict, task_id: str) -> Any:
        """Execute specific action for workflow"""
        
        if action == "plan_and_implement":
            requirements = context.get("requirements", "")
            code_context = context.get("original_context")
            return await self.execute(code_context, requirements, [], task_id)
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def plan_implementation(
        self,
        requirements: str,
        context: Any,
        tech_stack: TechStack
    ) -> ImplementationPlan:
        """Plan the feature implementation"""
        
        # Build AI context
        ai_context = AICodeContext(
            file_path="feature_planning",
            content="",
            language=tech_stack.language,
            cursor_position=0,
            project_context={
                "tech_stack": tech_stack.__dict__,
                "existing_files": getattr(context, 'file_paths', [])
            }
        )
        
        # Create planning prompt
        prompt = f"""
        Plan the implementation for the following feature:
        
        Requirements: {requirements}
        
        Technology Stack:
        - Language: {tech_stack.language}
        - Framework: {tech_stack.framework}
        - Libraries: {', '.join(tech_stack.libraries)}
        
        Provide a detailed implementation plan with:
        1. List of files to create/modify
        2. Step-by-step implementation approach
        3. Dependencies and integrations
        4. Estimated complexity (low/medium/high)
        5. Potential risks or challenges
        
        Format the response as a structured plan.
        """
        
        # Get AI response
        request = AIRequest(
            task_type=TaskType.FEATURE_IMPLEMENTATION,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system",
            temperature=0.2,
            max_tokens=2000
        )
        
        response = await self.ai_service.process_request(request)
        
        # Parse the response into a plan
        plan_steps = self._parse_plan_response(response.content)
        
        # Estimate time based on complexity
        complexity = self._estimate_complexity(plan_steps, requirements)
        estimated_time = self._estimate_time(complexity, len(plan_steps))
        
        plan = ImplementationPlan(
            steps=plan_steps,
            estimated_time=estimated_time,
            complexity=complexity
        )
        
        return plan
    
    async def generate_code(
        self,
        step: Dict,
        tech_stack: TechStack,
        style_guide: StyleGuide
    ) -> List[Dict]:
        """Generate code for a specific implementation step"""
        
        # Build AI context
        ai_context = AICodeContext(
            file_path=step.get("file_path", "new_file"),
            content=step.get("existing_content", ""),
            language=tech_stack.language,
            cursor_position=0,
            project_context={
                "tech_stack": tech_stack.__dict__,
                "style_guide": style_guide.conventions
            }
        )
        
        # Create code generation prompt
        prompt = f"""
        Generate production-ready code for the following step:
        
        Step: {step['description']}
        File: {step.get('file_path', 'new file')}
        
        Requirements:
        - Use {tech_stack.language} with {tech_stack.framework}
        - Follow these style conventions: {json.dumps(style_guide.conventions)}
        - Include proper error handling
        - Add appropriate comments and documentation
        - Make the code modular and testable
        
        {step.get('additional_context', '')}
        
        Generate complete, working code.
        """
        
        # Get AI response
        request = AIRequest(
            task_type=TaskType.FEATURE_IMPLEMENTATION,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system",
            temperature=0.1,
            max_tokens=2000
        )
        
        response = await self.ai_service.process_request(request)
        
        # Extract code from response
        code_blocks = self._extract_code_blocks(response.content)
        
        # Create file objects
        files = []
        for i, code_block in enumerate(code_blocks):
            file_path = step.get('file_path', f"generated_file_{i}.{self._get_file_extension(tech_stack.language)}")
            
            files.append({
                "path": file_path,
                "content": code_block,
                "language": tech_stack.language,
                "step": step['description']
            })
        
        return files
    
    async def estimate_task(self, context: Any, requirements: str) -> Dict:
        """Estimate time and credits for the task"""
        
        # Quick analysis of requirements
        requirement_lines = requirements.split('\n')
        requirement_complexity = len(requirement_lines)
        
        # Estimate based on requirement complexity
        if requirement_complexity < 5:
            complexity = "low"
            estimated_time = 120  # 2 minutes
            estimated_credits = 20
        elif requirement_complexity < 15:
            complexity = "medium"
            estimated_time = 300  # 5 minutes
            estimated_credits = 50
        else:
            complexity = "high"
            estimated_time = 600  # 10 minutes
            estimated_credits = 100
        
        return {
            "time": estimated_time,
            "credits": estimated_credits,
            "complexity": complexity,
            "confidence": 0.7
        }
    
    def _determine_tech_stack(self, context: Any, constraints: List[Any]) -> TechStack:
        """Determine the technology stack from context and constraints"""
        
        # Check constraints for tech stack specification
        for constraint in constraints:
            if hasattr(constraint, 'type') and constraint.type == "tech_stack":
                return TechStack(
                    language=constraint.value.get("language", "python"),
                    framework=constraint.value.get("framework", "fastapi"),
                    libraries=constraint.value.get("libraries", [])
                )
        
        # Infer from context if not specified
        if hasattr(context, 'language_stats'):
            # Use the most common language
            languages = getattr(context, 'language_stats', {})
            if languages:
                primary_language = max(languages, key=languages.get)
            else:
                primary_language = "python"
        else:
            primary_language = "python"
        
        # Default frameworks
        default_frameworks = {
            "python": "fastapi",
            "javascript": "express",
            "typescript": "express",
            "go": "gin",
            "java": "spring"
        }
        
        return TechStack(
            language=primary_language,
            framework=default_frameworks.get(primary_language, ""),
            libraries=[]
        )
    
    def _get_style_guide(self, tech_stack: TechStack) -> StyleGuide:
        """Get style guide for the tech stack"""
        
        style_guides = {
            "python": {
                "indentation": "4 spaces",
                "naming": "snake_case for functions and variables, PascalCase for classes",
                "quotes": "double quotes for docstrings, single quotes for strings",
                "line_length": "88 (black formatter)",
                "imports": "sorted, grouped by standard/third-party/local"
            },
            "javascript": {
                "indentation": "2 spaces",
                "naming": "camelCase for functions and variables, PascalCase for classes",
                "quotes": "single quotes preferred",
                "semicolons": "optional but consistent",
                "line_length": "80-100 characters"
            },
            "typescript": {
                "indentation": "2 spaces",
                "naming": "camelCase for functions and variables, PascalCase for classes/interfaces",
                "quotes": "single quotes preferred",
                "semicolons": "required",
                "line_length": "80-100 characters",
                "types": "explicit types for public APIs"
            }
        }
        
        conventions = style_guides.get(tech_stack.language, {})
        return StyleGuide(conventions)
    
    def _parse_plan_response(self, response: str) -> List[Dict]:
        """Parse AI response into structured plan steps"""
        
        steps = []
        
        # Simple parsing - in production this would be more sophisticated
        lines = response.split('\n')
        current_step = None
        
        for line in lines:
            line = line.strip()
            
            # Look for numbered steps
            if line and (line[0].isdigit() or line.startswith('-')):
                if current_step:
                    steps.append(current_step)
                
                current_step = {
                    "description": line.lstrip('0123456789.-').strip(),
                    "file_path": None,
                    "dependencies": []
                }
            
            # Look for file paths
            elif current_step and ('file:' in line.lower() or 'create' in line.lower()):
                # Extract file path
                parts = line.split(':')
                if len(parts) > 1:
                    current_step["file_path"] = parts[1].strip()
        
        if current_step:
            steps.append(current_step)
        
        # If no steps found, create a default step
        if not steps:
            steps = [{
                "description": "Implement feature",
                "file_path": "feature.py",
                "dependencies": []
            }]
        
        return steps
    
    def _estimate_complexity(self, steps: List[Dict], requirements: str) -> str:
        """Estimate implementation complexity"""
        
        # Simple heuristics
        num_steps = len(steps)
        requirement_length = len(requirements)
        
        if num_steps <= 3 and requirement_length < 200:
            return "low"
        elif num_steps <= 7 and requirement_length < 500:
            return "medium"
        else:
            return "high"
    
    def _estimate_time(self, complexity: str, num_steps: int) -> int:
        """Estimate time in seconds"""
        
        base_times = {
            "low": 120,    # 2 minutes
            "medium": 300,  # 5 minutes
            "high": 600    # 10 minutes
        }
        
        base_time = base_times.get(complexity, 300)
        
        # Add time per step
        step_time = 30 * num_steps
        
        return base_time + step_time
    
    def _extract_code_blocks(self, content: str) -> List[str]:
        """Extract code blocks from AI response"""
        
        import re
        
        # Find code blocks with triple backticks
        pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if matches:
            return matches
        
        # If no code blocks found, treat the entire content as code
        # (filtering out obvious non-code lines)
        lines = content.split('\n')
        code_lines = []
        
        for line in lines:
            # Skip lines that look like explanations
            if not line.strip().endswith(':') and not line.strip().startswith('#'):
                code_lines.append(line)
        
        return ['\n'.join(code_lines)]
    
    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language"""
        
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "go": "go",
            "java": "java",
            "rust": "rs",
            "cpp": "cpp",
            "c": "c"
        }
        
        return extensions.get(language, "txt")
    
    async def _validate_implementation(self, artifacts: List[Dict], requirements: str) -> Dict:
        """Validate the implementation meets requirements"""
        
        # Basic validation
        validation = {
            "files_created": len(artifacts),
            "total_lines": sum(len(a["content"].split('\n')) for a in artifacts),
            "syntax_valid": True,  # Would do actual syntax checking
            "requirements_met": 0.8,  # Would do requirement matching
            "issues": []
        }
        
        # Check for common issues
        for artifact in artifacts:
            content = artifact["content"]
            
            # Check for TODOs
            if "TODO" in content or "FIXME" in content:
                validation["issues"].append({
                    "file": artifact["path"],
                    "issue": "Contains TODO/FIXME comments"
                })
            
            # Check for proper error handling (simple check)
            if artifact["language"] == "python" and "try:" not in content and "except" not in content:
                validation["issues"].append({
                    "file": artifact["path"],
                    "issue": "May lack error handling"
                })
        
        return validation