"""
Documentation Agent - Generates and maintains documentation
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ....models.ai_agent import AgentTask, AgentArtifact, AgentResult, TaskStatus
from ...ai_service import AIProvider, TaskType, AIRequest, CodeContext as AICodeContext

logger = logging.getLogger(__name__)


class DocumentationAgent:
    """
    Agent that generates comprehensive documentation.
    Creates API docs, README files, code comments, and architectural documentation.
    """
    
    def __init__(self, db: Session):
        self.db = db
        from ...ai_service import MultiAgentAI
        self.ai_service = MultiAgentAI()
        
        self.doc_types = {
            "api": "API documentation",
            "readme": "README file",
            "comments": "Code comments",
            "architecture": "Architecture documentation",
            "tutorial": "Tutorial/Guide"
        }
    
    async def execute(
        self,
        context: Any,
        requirements: str,
        constraints: List[Any],
        task_id: str
    ) -> AgentResult:
        """Execute documentation task"""
        
        try:
            # Determine documentation type
            doc_type = self._determine_doc_type(requirements)
            
            # Get code to document
            code_files = self._extract_code_files(context)
            
            if not code_files:
                raise ValueError("No code files found to document")
            
            # Generate documentation
            artifacts = []
            
            for code_file in code_files:
                if doc_type == "comments":
                    # Add comments to code
                    documented_code = await self._add_code_comments(code_file)
                    artifacts.append({
                        "path": code_file["path"],
                        "content": documented_code,
                        "type": "commented_code"
                    })
                else:
                    # Generate separate documentation
                    doc_content = await self._generate_documentation(
                        code_file,
                        doc_type
                    )
                    
                    doc_path = self._get_doc_path(code_file["path"], doc_type)
                    artifacts.append({
                        "path": doc_path,
                        "content": doc_content,
                        "type": doc_type
                    })
            
            # Save artifacts
            for artifact in artifacts:
                db_artifact = AgentArtifact(
                    task_id=task_id,
                    artifact_type="documentation",
                    file_path=artifact["path"],
                    content=artifact["content"],
                    language="markdown" if artifact["type"] != "commented_code" else code_file.get("language", "python")
                )
                self.db.add(db_artifact)
            
            self.db.commit()
            
            return AgentResult(
                success=True,
                output={
                    "documentation_created": True,
                    "files_documented": len(artifacts),
                    "doc_type": doc_type
                },
                artifacts=artifacts,
                metrics={
                    "confidence": 0.95,
                    "completeness": 0.85
                }
            )
            
        except Exception as e:
            logger.error(f"Documentation agent error: {str(e)}")
            return AgentResult(
                success=False,
                output={"error": str(e)},
                artifacts=[],
                metrics={"error": str(e)}
            )
    
    async def execute_action(self, action: str, context: Dict, task_id: str) -> Any:
        """Execute specific action for workflow"""
        
        if action == "generate_docs":
            return await self.execute(
                context.get("original_context"),
                "Generate comprehensive documentation",
                [],
                task_id
            )
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def estimate_task(self, context: Any, requirements: str) -> Dict:
        """Estimate time and credits for documentation"""
        
        return {
            "time": 60,  # 1 minute
            "credits": 10,
            "complexity": "low",
            "confidence": 0.95
        }
    
    async def _add_code_comments(self, code_file: Dict) -> str:
        """Add comments to code"""
        
        prompt = f"""
        Add comprehensive comments to the following code:
        
        ```{code_file.get('language', 'python')}
        {code_file.get('content', '')}
        ```
        
        Add:
        1. File-level docstring
        2. Function/class docstrings
        3. Inline comments for complex logic
        4. Parameter descriptions
        5. Return value descriptions
        
        Maintain the original code functionality.
        """
        
        ai_context = AICodeContext(
            file_path=code_file.get("path", ""),
            content=code_file.get("content", ""),
            language=code_file.get("language", "python"),
            cursor_position=0
        )
        
        request = AIRequest(
            task_type=TaskType.DOCUMENTATION,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system",
            temperature=0.2
        )
        
        response = await self.ai_service.process_request(request)
        
        # Extract commented code
        return self._extract_code_from_response(response.content)
    
    async def _generate_documentation(self, code_file: Dict, doc_type: str) -> str:
        """Generate documentation for code"""
        
        prompts = {
            "api": """
            Generate API documentation for the following code:
            
            Include:
            - Endpoint descriptions
            - Request/response formats
            - Authentication requirements
            - Example usage
            """,
            "readme": """
            Generate a README file for the following code:
            
            Include:
            - Project description
            - Installation instructions
            - Usage examples
            - API reference
            - Contributing guidelines
            """,
            "architecture": """
            Generate architecture documentation for the following code:
            
            Include:
            - System overview
            - Component descriptions
            - Data flow
            - Design decisions
            """
        }
        
        prompt = prompts.get(doc_type, "Generate documentation for the following code:")
        prompt += f"\n\n```{code_file.get('language', 'python')}\n{code_file.get('content', '')}\n```"
        
        ai_context = AICodeContext(
            file_path=code_file.get("path", ""),
            content=code_file.get("content", ""),
            language=code_file.get("language", "python"),
            cursor_position=0
        )
        
        request = AIRequest(
            task_type=TaskType.DOCUMENTATION,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system",
            temperature=0.3
        )
        
        response = await self.ai_service.process_request(request)
        
        return response.content
    
    def _determine_doc_type(self, requirements: str) -> str:
        """Determine documentation type from requirements"""
        
        req_lower = requirements.lower()
        
        if "api" in req_lower:
            return "api"
        elif "readme" in req_lower:
            return "readme"
        elif "comment" in req_lower:
            return "comments"
        elif "architect" in req_lower:
            return "architecture"
        else:
            return "readme"  # Default
    
    def _extract_code_files(self, context: Any) -> List[Dict]:
        """Extract code files from context"""
        
        files = []
        
        # Check previous results first
        if isinstance(context, dict) and "previous_results" in context:
            previous_results = context.get("previous_results", [])
            for result in previous_results:
                if hasattr(result, 'artifacts'):
                    for artifact in result.artifacts:
                        if artifact.get("type") in ["code", "refactored", "fixed"]:
                            files.append({
                                "path": artifact.get("path", "unknown"),
                                "content": artifact.get("content", ""),
                                "language": artifact.get("language", "python")
                            })
        
        # If no files from previous results, check context
        if not files and hasattr(context, 'file_paths'):
            for file_path in context.file_paths[:3]:  # Limit to 3 files
                content = ""
                if hasattr(context, 'content_map'):
                    content = context.content_map.get(file_path, "")
                
                files.append({
                    "path": file_path,
                    "content": content,
                    "language": self._detect_language(file_path)
                })
        
        return files
    
    def _get_doc_path(self, code_path: str, doc_type: str) -> str:
        """Get documentation file path"""
        
        import os
        base_name = os.path.splitext(os.path.basename(code_path))[0]
        
        if doc_type == "api":
            return f"docs/api_{base_name}.md"
        elif doc_type == "readme":
            return "README.md"
        elif doc_type == "architecture":
            return f"docs/architecture_{base_name}.md"
        else:
            return f"docs/{base_name}.md"
    
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