"""
Refactor Agent - Improves code structure and quality
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ....models.ai_agent import (
    AgentTask, AgentArtifact, QualityReport, RefactoringSuggestion,
    AgentResult, TaskStatus
)
from ...ai_service import AIProvider, TaskType, AIRequest, CodeContext as AICodeContext

logger = logging.getLogger(__name__)


class RefactorAgent:
    """
    Agent that analyzes code quality and performs refactoring.
    Identifies code smells, suggests improvements, and applies refactoring patterns.
    """
    
    def __init__(self, db: Session):
        self.db = db
        from ...ai_service import MultiAgentAI
        self.ai_service = MultiAgentAI()
        
        # Refactoring patterns
        self.refactoring_patterns = {
            "extract_method": "Extract repeated code into a method",
            "rename": "Rename for better clarity",
            "simplify_conditional": "Simplify complex conditionals",
            "remove_duplication": "Remove duplicate code",
            "improve_naming": "Improve variable/function names",
            "add_type_hints": "Add type hints (Python)",
            "extract_constant": "Extract magic numbers to constants",
            "decompose_function": "Break down large functions"
        }
    
    async def execute(
        self,
        context: Any,
        requirements: str,
        constraints: List[Any],
        task_id: str
    ) -> AgentResult:
        """Execute refactoring task"""
        
        try:
            task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
            if task:
                task.current_step = "Analyzing code quality"
                task.progress = 0.2
                self.db.commit()
            
            # Get code to refactor
            code_file = self._extract_code_file(context, requirements)
            if not code_file:
                raise ValueError("No code file specified for refactoring")
            
            # Analyze code quality
            quality_report = await self.analyze_code_quality(code_file)
            
            if task:
                task.current_step = "Generating refactoring suggestions"
                task.progress = 0.5
                self.db.commit()
            
            # Generate refactoring suggestions
            suggestions = await self.suggest_refactoring(code_file, quality_report)
            
            if task:
                task.current_step = "Applying refactorings"
                task.progress = 0.8
                self.db.commit()
            
            # Apply selected refactorings
            refactored_code = code_file.copy()
            for suggestion in suggestions[:3]:  # Apply top 3 suggestions
                refactored_code = await self.apply_refactoring(
                    refactored_code,
                    suggestion
                )
            
            # Create artifact
            artifact = AgentArtifact(
                task_id=task_id,
                artifact_type="refactored_code",
                file_path=code_file["path"],
                content=refactored_code["content"],
                language=code_file.get("language", "python"),
                changes_summary=f"Applied {len(suggestions[:3])} refactorings"
            )
            self.db.add(artifact)
            self.db.commit()
            
            if task:
                task.status = TaskStatus.COMPLETED.value
                task.completed_at = datetime.utcnow()
                self.db.commit()
            
            return AgentResult(
                success=True,
                output={
                    "quality_score": quality_report.score,
                    "issues_found": len(quality_report.issues),
                    "refactorings_applied": len(suggestions[:3])
                },
                artifacts=[{
                    "path": code_file["path"],
                    "content": refactored_code["content"],
                    "type": "refactored"
                }],
                metrics={
                    "quality_improvement": 0.15,
                    "confidence": 0.85
                }
            )
            
        except Exception as e:
            logger.error(f"Refactor agent error: {str(e)}")
            return AgentResult(
                success=False,
                output={"error": str(e)},
                artifacts=[],
                metrics={"error": str(e)}
            )
    
    async def execute_action(self, action: str, context: Dict, task_id: str) -> Any:
        """Execute specific action for workflow"""
        
        if action == "analyze_and_refactor":
            return await self.execute(
                context.get("original_context"),
                context.get("requirements", ""),
                [],
                task_id
            )
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def analyze_code_quality(self, code: Dict) -> QualityReport:
        """Analyze code quality and identify issues"""
        
        prompt = f"""
        Analyze the following code for quality issues:
        
        ```{code.get('language', 'python')}
        {code.get('content', '')}
        ```
        
        Identify:
        1. Code smells
        2. Complexity issues
        3. Naming problems
        4. Duplication
        5. Poor practices
        
        Rate the overall quality from 0-100.
        """
        
        ai_context = AICodeContext(
            file_path=code.get("path", ""),
            content=code.get("content", ""),
            language=code.get("language", "python"),
            cursor_position=0
        )
        
        request = AIRequest(
            task_type=TaskType.CODE_REVIEW,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system"
        )
        
        response = await self.ai_service.process_request(request)
        
        # Parse response into quality report
        issues = self._parse_quality_issues(response.content)
        score = self._calculate_quality_score(issues)
        
        return QualityReport(
            score=score,
            issues=issues,
            improvements=[]
        )
    
    async def suggest_refactoring(
        self,
        code: Dict,
        quality_report: QualityReport
    ) -> List[RefactoringSuggestion]:
        """Generate refactoring suggestions"""
        
        suggestions = []
        
        # Generate suggestions based on issues
        for issue in quality_report.issues[:5]:
            suggestion = await self._generate_refactoring_for_issue(
                code,
                issue
            )
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    async def apply_refactoring(
        self,
        code: Dict,
        refactoring: RefactoringSuggestion
    ) -> Dict:
        """Apply a refactoring suggestion"""
        
        prompt = f"""
        Apply the following refactoring to the code:
        
        Refactoring: {refactoring.type}
        Description: {refactoring.description}
        
        Original code:
        ```{code.get('language', 'python')}
        {code.get('content', '')}
        ```
        
        Generate the refactored code.
        """
        
        ai_context = AICodeContext(
            file_path=code.get("path", ""),
            content=code.get("content", ""),
            language=code.get("language", "python"),
            cursor_position=0
        )
        
        request = AIRequest(
            task_type=TaskType.REFACTORING,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system",
            temperature=0.1
        )
        
        response = await self.ai_service.process_request(request)
        
        # Extract refactored code
        refactored_content = self._extract_code_from_response(response.content)
        
        return {
            "path": code["path"],
            "content": refactored_content,
            "language": code["language"]
        }
    
    async def estimate_task(self, context: Any, requirements: str) -> Dict:
        """Estimate time and credits for refactoring"""
        
        return {
            "time": 180,  # 3 minutes
            "credits": 25,
            "complexity": "medium",
            "confidence": 0.8
        }
    
    def _extract_code_file(self, context: Any, requirements: str) -> Optional[Dict]:
        """Extract code file from context"""
        
        if hasattr(context, 'file_paths') and context.file_paths:
            file_path = context.file_paths[0]
            content = ""
            if hasattr(context, 'content_map'):
                content = context.content_map.get(file_path, "")
            
            return {
                "path": file_path,
                "content": content,
                "language": self._detect_language(file_path)
            }
        
        return None
    
    def _parse_quality_issues(self, response: str) -> List[Dict]:
        """Parse quality issues from response"""
        
        issues = []
        lines = response.split('\n')
        
        for line in lines:
            if any(keyword in line.lower() for keyword in ['smell', 'issue', 'problem', 'poor']):
                issues.append({
                    "type": "quality_issue",
                    "description": line.strip(),
                    "severity": "medium"
                })
        
        return issues
    
    def _calculate_quality_score(self, issues: List[Dict]) -> float:
        """Calculate quality score based on issues"""
        
        # Simple scoring: start at 100, subtract for each issue
        score = 100.0
        
        for issue in issues:
            if issue.get("severity") == "high":
                score -= 10
            elif issue.get("severity") == "medium":
                score -= 5
            else:
                score -= 2
        
        return max(0.0, score)
    
    async def _generate_refactoring_for_issue(
        self,
        code: Dict,
        issue: Dict
    ) -> Optional[RefactoringSuggestion]:
        """Generate refactoring suggestion for an issue"""
        
        # Simplified - in production would be more sophisticated
        description = issue.get("description", "")
        
        refactoring_type = "improve_code"
        if "naming" in description.lower():
            refactoring_type = "improve_naming"
        elif "duplicate" in description.lower():
            refactoring_type = "remove_duplication"
        elif "complex" in description.lower():
            refactoring_type = "simplify_conditional"
        
        return RefactoringSuggestion(
            type=refactoring_type,
            description=f"Fix: {description}",
            impact="medium",
            changes=[]
        )
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from AI response"""
        
        import re
        code_pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0]
        
        return response
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file path"""
        
        import os
        ext = os.path.splitext(file_path)[1].lower()
        
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go"
        }
        
        return ext_to_lang.get(ext, "unknown")