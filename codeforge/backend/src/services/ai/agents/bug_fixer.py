"""
Bug Fixer Agent - Identifies and fixes bugs autonomously
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ....models.ai_agent import AgentTask, AgentArtifact, AgentResult, TaskStatus
from ...ai_service import AIProvider, TaskType, AIRequest, CodeContext as AICodeContext

logger = logging.getLogger(__name__)


class BugFixerAgent:
    """
    Agent that identifies and fixes bugs in code.
    Analyzes error messages, traces issues, and provides fixes.
    """
    
    def __init__(self, db: Session):
        self.db = db
        from ...ai_service import MultiAgentAI
        self.ai_service = MultiAgentAI()
    
    async def execute(
        self,
        context: Any,
        requirements: str,
        constraints: List[Any],
        task_id: str
    ) -> AgentResult:
        """Execute bug fixing task"""
        
        try:
            # Extract bug information
            bug_info = self._extract_bug_info(requirements)
            code_file = self._extract_code_file(context, requirements)
            
            if not code_file:
                raise ValueError("No code file specified for bug fixing")
            
            # Analyze the bug
            prompt = f"""
            Fix the following bug:
            
            Error: {bug_info.get('error', 'Unknown error')}
            
            Code with bug:
            ```{code_file.get('language', 'python')}
            {code_file.get('content', '')}
            ```
            
            Provide:
            1. Root cause analysis
            2. Fixed code
            3. Explanation of the fix
            """
            
            ai_context = AICodeContext(
                file_path=code_file.get("path", ""),
                content=code_file.get("content", ""),
                language=code_file.get("language", "python"),
                cursor_position=0
            )
            
            request = AIRequest(
                task_type=TaskType.BUG_FIX,
                provider=AIProvider.CLAUDE,
                context=ai_context,
                prompt=prompt,
                user_id="system",
                temperature=0.1
            )
            
            response = await self.ai_service.process_request(request)
            
            # Extract fixed code
            fixed_code = self._extract_code_from_response(response.content)
            
            # Create artifact
            artifact = AgentArtifact(
                task_id=task_id,
                artifact_type="bug_fix",
                file_path=code_file["path"],
                content=fixed_code,
                language=code_file.get("language", "python"),
                changes_summary="Bug fix applied"
            )
            self.db.add(artifact)
            self.db.commit()
            
            return AgentResult(
                success=True,
                output={
                    "bug_fixed": True,
                    "explanation": response.content
                },
                artifacts=[{
                    "path": code_file["path"],
                    "content": fixed_code,
                    "type": "fixed"
                }],
                metrics={"confidence": 0.9}
            )
            
        except Exception as e:
            logger.error(f"Bug fixer error: {str(e)}")
            return AgentResult(
                success=False,
                output={"error": str(e)},
                artifacts=[],
                metrics={"error": str(e)}
            )
    
    async def execute_action(self, action: str, context: Dict, task_id: str) -> Any:
        """Execute specific action for workflow"""
        
        if action == "analyze_and_fix":
            return await self.execute(
                context.get("original_context"),
                context.get("requirements", ""),
                [],
                task_id
            )
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def estimate_task(self, context: Any, requirements: str) -> Dict:
        """Estimate time and credits for bug fixing"""
        
        return {
            "time": 120,  # 2 minutes
            "credits": 20,
            "complexity": "medium",
            "confidence": 0.85
        }
    
    def _extract_bug_info(self, requirements: str) -> Dict:
        """Extract bug information from requirements"""
        
        return {
            "error": requirements,
            "type": "general"
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
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from AI response"""
        
        import re
        code_pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            # Return the last code block (likely the fixed code)
            return matches[-1]
        
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