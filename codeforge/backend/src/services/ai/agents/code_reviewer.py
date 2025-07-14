"""
Code Reviewer Agent - Provides detailed code reviews
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ....models.ai_agent import AgentTask, AgentArtifact, AgentResult, TaskStatus
from ...ai_service import AIProvider, TaskType, AIRequest, CodeContext as AICodeContext

logger = logging.getLogger(__name__)


class CodeReviewerAgent:
    """
    Agent that performs thorough code reviews.
    Checks for bugs, security issues, best practices, and provides feedback.
    """
    
    def __init__(self, db: Session):
        self.db = db
        from ...ai_service import MultiAgentAI
        self.ai_service = MultiAgentAI()
        
        self.review_categories = [
            "bugs",
            "security",
            "performance",
            "readability",
            "best_practices",
            "documentation"
        ]
    
    async def execute(
        self,
        context: Any,
        requirements: str,
        constraints: List[Any],
        task_id: str
    ) -> AgentResult:
        """Execute code review task"""
        
        try:
            code_file = self._extract_code_file(context, requirements)
            if not code_file:
                raise ValueError("No code file specified for review")
            
            # Perform code review
            prompt = f"""
            Perform a comprehensive code review for:
            
            ```{code_file.get('language', 'python')}
            {code_file.get('content', '')}
            ```
            
            Review for:
            1. Bugs and potential errors
            2. Security vulnerabilities
            3. Performance issues
            4. Code readability and maintainability
            5. Best practices adherence
            6. Documentation quality
            
            Provide specific, actionable feedback.
            """
            
            ai_context = AICodeContext(
                file_path=code_file.get("path", ""),
                content=code_file.get("content", ""),
                language=code_file.get("language", "python"),
                cursor_position=0
            )
            
            request = AIRequest(
                task_type=TaskType.CODE_REVIEW,
                provider=AIProvider.CLAUDE,
                context=ai_context,
                prompt=prompt,
                user_id="system",
                temperature=0.2
            )
            
            response = await self.ai_service.process_request(request)
            
            # Parse review feedback
            review_feedback = self._parse_review_feedback(response.content)
            
            # Create review artifact
            artifact = AgentArtifact(
                task_id=task_id,
                artifact_type="code_review",
                file_path=f"review_{code_file['path']}",
                content=response.content,
                language="markdown"
            )
            self.db.add(artifact)
            self.db.commit()
            
            return AgentResult(
                success=True,
                output={
                    "review_completed": True,
                    "issues_found": len(review_feedback),
                    "categories": list(set(f["category"] for f in review_feedback))
                },
                artifacts=[{
                    "path": f"review_{code_file['path']}.md",
                    "content": response.content,
                    "type": "review"
                }],
                metrics={
                    "confidence": 0.9,
                    "severity_high": sum(1 for f in review_feedback if f.get("severity") == "high")
                }
            )
            
        except Exception as e:
            logger.error(f"Code reviewer error: {str(e)}")
            return AgentResult(
                success=False,
                output={"error": str(e)},
                artifacts=[],
                metrics={"error": str(e)}
            )
    
    async def execute_action(self, action: str, context: Dict, task_id: str) -> Any:
        """Execute specific action for workflow"""
        
        if action == "review_code":
            return await self.execute(
                context.get("original_context"),
                context.get("requirements", ""),
                [],
                task_id
            )
        elif action == "review_changes":
            # Review changes from previous steps
            return await self._review_changes(context, task_id)
        elif action == "review_tests":
            # Review generated tests
            return await self._review_tests(context, task_id)
        elif action == "review_fix":
            # Review bug fix
            return await self._review_bug_fix(context, task_id)
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def estimate_task(self, context: Any, requirements: str) -> Dict:
        """Estimate time and credits for code review"""
        
        return {
            "time": 90,  # 1.5 minutes
            "credits": 15,
            "complexity": "low",
            "confidence": 0.9
        }
    
    def _extract_code_file(self, context: Any, requirements: str) -> Optional[Dict]:
        """Extract code file from context"""
        
        # Check if previous results have code
        if isinstance(context, dict) and "previous_results" in context:
            previous_results = context.get("previous_results", [])
            if previous_results and previous_results[-1].artifacts:
                artifact = previous_results[-1].artifacts[0]
                return {
                    "path": artifact.get("path", "unknown"),
                    "content": artifact.get("content", ""),
                    "language": artifact.get("language", "python")
                }
        
        # Otherwise extract from context
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
    
    def _parse_review_feedback(self, response: str) -> List[Dict]:
        """Parse review feedback from response"""
        
        feedback = []
        lines = response.split('\n')
        
        current_category = "general"
        for line in lines:
            line = line.strip()
            
            # Check for category headers
            for category in self.review_categories:
                if category.lower() in line.lower():
                    current_category = category
                    break
            
            # Check for feedback items
            if line and (line.startswith('-') or line.startswith('•') or line[0].isdigit()):
                severity = "medium"
                if any(word in line.lower() for word in ["critical", "severe", "dangerous"]):
                    severity = "high"
                elif any(word in line.lower() for word in ["minor", "suggestion", "consider"]):
                    severity = "low"
                
                feedback.append({
                    "category": current_category,
                    "feedback": line.lstrip('-•0123456789. '),
                    "severity": severity
                })
        
        return feedback
    
    async def _review_changes(self, context: Dict, task_id: str) -> AgentResult:
        """Review changes from previous steps"""
        
        # Get original and modified code
        original_context = context.get("original_context")
        previous_results = context.get("previous_results", [])
        
        if not previous_results:
            return AgentResult(
                success=False,
                output={"error": "No changes to review"},
                artifacts=[],
                metrics={}
            )
        
        # Simple implementation - review the latest changes
        return await self.execute(
            original_context,
            "Review the code changes",
            [],
            task_id
        )
    
    async def _review_tests(self, context: Dict, task_id: str) -> AgentResult:
        """Review generated tests"""
        
        # Extract test code from previous results
        previous_results = context.get("previous_results", [])
        
        for result in previous_results:
            if hasattr(result, 'artifacts'):
                for artifact in result.artifacts:
                    if artifact.get("type") == "test" or "test" in artifact.get("path", ""):
                        # Found test code, review it
                        test_context = type('obj', (object,), {
                            'file_paths': [artifact["path"]],
                            'content_map': {artifact["path"]: artifact["content"]}
                        })
                        
                        return await self.execute(
                            test_context,
                            "Review the test code for completeness and correctness",
                            [],
                            task_id
                        )
        
        return AgentResult(
            success=False,
            output={"error": "No test code found to review"},
            artifacts=[],
            metrics={}
        )
    
    async def _review_bug_fix(self, context: Dict, task_id: str) -> AgentResult:
        """Review bug fix"""
        
        # Similar to reviewing changes, but focus on the fix
        return await self._review_changes(context, task_id)
    
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