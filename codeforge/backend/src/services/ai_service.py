"""
AI Service for CodeForge
Multi-agent AI system with code completion, chat, and autonomous development
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
import httpx
from anthropic import Anthropic
import openai

from ..config.settings import settings


class AIProvider(str, Enum):
    """AI providers"""
    CLAUDE = "claude"
    OPENAI = "openai"
    QWEN = "qwen"


class TaskType(str, Enum):
    """AI task types"""
    CODE_COMPLETION = "code_completion"
    CODE_EXPLANATION = "code_explanation"
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    FEATURE_IMPLEMENTATION = "feature_implementation"
    CHAT = "chat"


@dataclass
class CodeContext:
    """Code context for AI operations"""
    file_path: str
    content: str
    language: str
    cursor_position: int
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    project_context: Optional[Dict] = None


@dataclass
class AIRequest:
    """AI request structure"""
    task_type: TaskType
    provider: AIProvider
    context: CodeContext
    prompt: str
    user_id: str
    session_id: Optional[str] = None
    temperature: float = 0.1
    max_tokens: int = 1000


@dataclass
class AIResponse:
    """AI response structure"""
    request_id: str
    task_type: TaskType
    provider: AIProvider
    content: str
    suggestions: List[Dict] = None
    confidence: float = 0.0
    processing_time: float = 0.0
    tokens_used: int = 0
    credits_consumed: int = 0


class MultiAgentAI:
    """
    Multi-agent AI system for CodeForge:
    - Code Completion Agent: Real-time completions
    - Code Review Agent: Quality analysis and suggestions
    - Bug Fix Agent: Error detection and fixes
    - Refactoring Agent: Code improvement suggestions
    - Testing Agent: Test generation and validation
    - Documentation Agent: Auto-documentation
    - Feature Agent: Autonomous feature implementation
    """
    
    def __init__(self):
        # Initialize AI clients
        self.claude_client = None
        self.openai_client = None
        
        if settings.CLAUDE_API_KEY:
            self.claude_client = Anthropic(api_key=settings.CLAUDE_API_KEY)
            
        if settings.OPENAI_API_KEY:
            openai.api_key = settings.OPENAI_API_KEY
            self.openai_client = openai
            
        # Agent specializations
        self.agents = {
            TaskType.CODE_COMPLETION: {
                "name": "CodeCompletion",
                "provider": AIProvider.CLAUDE,
                "temperature": 0.1,
                "max_tokens": 500
            },
            TaskType.CODE_EXPLANATION: {
                "name": "CodeExplainer", 
                "provider": AIProvider.CLAUDE,
                "temperature": 0.3,
                "max_tokens": 1000
            },
            TaskType.CODE_REVIEW: {
                "name": "CodeReviewer",
                "provider": AIProvider.CLAUDE,
                "temperature": 0.2,
                "max_tokens": 1500
            },
            TaskType.BUG_FIX: {
                "name": "BugFixer",
                "provider": AIProvider.CLAUDE,
                "temperature": 0.1,
                "max_tokens": 1000
            },
            TaskType.REFACTORING: {
                "name": "Refactorer",
                "provider": AIProvider.CLAUDE,
                "temperature": 0.2,
                "max_tokens": 1500
            },
            TaskType.TESTING: {
                "name": "TestGenerator",
                "provider": AIProvider.OPENAI,
                "temperature": 0.3,
                "max_tokens": 1000
            },
            TaskType.DOCUMENTATION: {
                "name": "Documenter",
                "provider": AIProvider.CLAUDE,
                "temperature": 0.4,
                "max_tokens": 1200
            },
            TaskType.FEATURE_IMPLEMENTATION: {
                "name": "FeatureDeveloper",
                "provider": AIProvider.CLAUDE,
                "temperature": 0.2,
                "max_tokens": 2000
            },
            TaskType.CHAT: {
                "name": "Assistant",
                "provider": AIProvider.CLAUDE,
                "temperature": 0.7,
                "max_tokens": 1500
            }
        }
        
    async def process_request(self, request: AIRequest) -> AIResponse:
        """Process AI request with appropriate agent"""
        start_time = datetime.now(timezone.utc)
        request_id = str(uuid.uuid4())
        
        # Get agent configuration
        agent_config = self.agents.get(request.task_type)
        if not agent_config:
            raise ValueError(f"No agent configured for task type: {request.task_type}")
            
        # Override provider if specified in request
        provider = request.provider if request.provider else agent_config["provider"]
        
        # Build prompt based on task type
        system_prompt = self._get_system_prompt(request.task_type, request.context)
        user_prompt = self._build_user_prompt(request)
        
        try:
            # Route to appropriate provider
            if provider == AIProvider.CLAUDE:
                response_content = await self._call_claude(
                    system_prompt,
                    user_prompt,
                    temperature=request.temperature or agent_config["temperature"],
                    max_tokens=request.max_tokens or agent_config["max_tokens"]
                )
            elif provider == AIProvider.OPENAI:
                response_content = await self._call_openai(
                    system_prompt,
                    user_prompt,
                    temperature=request.temperature or agent_config["temperature"],
                    max_tokens=request.max_tokens or agent_config["max_tokens"]
                )
            elif provider == AIProvider.QWEN:
                response_content = await self._call_qwen(
                    system_prompt,
                    user_prompt,
                    temperature=request.temperature or agent_config["temperature"],
                    max_tokens=request.max_tokens or agent_config["max_tokens"]
                )
            else:
                raise ValueError(f"Unsupported AI provider: {provider}")
                
            # Calculate processing time
            processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
            
            # Parse response for suggestions
            suggestions = self._parse_suggestions(request.task_type, response_content)
            
            # Calculate credits consumed (simplified)
            credits_consumed = self._calculate_credits(
                provider,
                len(user_prompt),
                len(response_content)
            )
            
            return AIResponse(
                request_id=request_id,
                task_type=request.task_type,
                provider=provider,
                content=response_content,
                suggestions=suggestions,
                confidence=0.85,  # TODO: Calculate actual confidence
                processing_time=processing_time,
                tokens_used=len(response_content.split()),
                credits_consumed=credits_consumed
            )
            
        except Exception as e:
            # Return error response
            return AIResponse(
                request_id=request_id,
                task_type=request.task_type,
                provider=provider,
                content=f"Error: {str(e)}",
                suggestions=[],
                confidence=0.0,
                processing_time=(datetime.now(timezone.utc) - start_time).total_seconds(),
                tokens_used=0,
                credits_consumed=0
            )
            
    async def _call_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> str:
        """Call Claude API"""
        if not self.claude_client:
            raise ValueError("Claude API key not configured")
            
        try:
            response = await asyncio.to_thread(
                self.claude_client.messages.create,
                model="claude-3-sonnet-20240229",
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            raise Exception(f"Claude API error: {str(e)}")
            
    async def _call_openai(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> str:
        """Call OpenAI API"""
        if not self.openai_client:
            raise ValueError("OpenAI API key not configured")
            
        try:
            response = await asyncio.to_thread(
                self.openai_client.ChatCompletion.create,
                model="gpt-4",
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
            
    async def _call_qwen(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 1000
    ) -> str:
        """Call local Qwen model"""
        try:
            # This would interface with a local Qwen model
            # For now, return a mock response
            return f"Mock Qwen response for: {user_prompt[:100]}..."
            
        except Exception as e:
            raise Exception(f"Qwen model error: {str(e)}")
            
    def _get_system_prompt(self, task_type: TaskType, context: CodeContext) -> str:
        """Get system prompt for task type"""
        base_prompt = f"""You are a {self.agents[task_type]['name']} agent in CodeForge, an advanced AI-powered development platform.

Language: {context.language}
File: {context.file_path}

Core principles:
1. Provide accurate, production-ready code
2. Follow best practices and conventions
3. Be concise but thorough
4. Prioritize security and performance
5. Consider the broader project context"""

        task_specific = {
            TaskType.CODE_COMPLETION: """
Your role: Provide intelligent code completions based on context.
- Complete the code at the cursor position
- Suggest multiple alternatives when applicable
- Consider variable names, function signatures, and patterns
- Provide short, focused completions (1-10 lines typically)""",

            TaskType.CODE_EXPLANATION: """
Your role: Explain code clearly and comprehensively.
- Break down complex logic into understandable parts
- Explain the purpose and functionality
- Identify patterns and architectural decisions
- Suggest improvements when relevant""",

            TaskType.CODE_REVIEW: """
Your role: Perform thorough code review with constructive feedback.
- Identify bugs, security issues, and performance problems
- Suggest improvements for readability and maintainability
- Check adherence to best practices
- Provide specific, actionable recommendations""",

            TaskType.BUG_FIX: """
Your role: Identify and fix bugs in the code.
- Analyze the error or unexpected behavior
- Identify the root cause
- Provide a corrected version of the code
- Explain the fix and prevent similar issues""",

            TaskType.REFACTORING: """
Your role: Improve code structure and quality.
- Suggest better organization and patterns
- Improve readability and maintainability
- Eliminate code smells and technical debt
- Preserve functionality while improving design""",

            TaskType.TESTING: """
Your role: Generate comprehensive tests.
- Create unit tests with good coverage
- Include edge cases and error scenarios
- Follow testing best practices for the framework
- Ensure tests are maintainable and reliable""",

            TaskType.DOCUMENTATION: """
Your role: Generate clear, helpful documentation.
- Write comprehensive docstrings and comments
- Create README files and API documentation
- Explain usage patterns and examples
- Keep documentation up-to-date with code""",

            TaskType.FEATURE_IMPLEMENTATION: """
Your role: Implement features autonomously.
- Break down requirements into implementation steps
- Write complete, production-ready code
- Include error handling and edge cases
- Consider integration with existing codebase""",

            TaskType.CHAT: """
Your role: Provide helpful development assistance.
- Answer questions about code and development
- Provide guidance on best practices
- Help with debugging and problem-solving
- Be friendly and educational"""
        }
        
        return f"{base_prompt}\n\n{task_specific.get(task_type, '')}"
        
    def _build_user_prompt(self, request: AIRequest) -> str:
        """Build user prompt from request"""
        context = request.context
        
        prompt_parts = []
        
        # Add file content
        if context.content:
            prompt_parts.append(f"Current file content:\n```{context.language}\n{context.content}\n```")
            
        # Add cursor position info
        if context.cursor_position is not None:
            lines = context.content.split('\n')
            line_num = context.content[:context.cursor_position].count('\n')
            col_num = context.cursor_position - context.content.rfind('\n', 0, context.cursor_position) - 1
            prompt_parts.append(f"Cursor position: Line {line_num + 1}, Column {col_num + 1}")
            
        # Add selection info
        if context.selection_start is not None and context.selection_end is not None:
            selected_text = context.content[context.selection_start:context.selection_end]
            prompt_parts.append(f"Selected text:\n```{context.language}\n{selected_text}\n```")
            
        # Add project context
        if context.project_context:
            prompt_parts.append(f"Project context: {json.dumps(context.project_context, indent=2)}")
            
        # Add user request
        prompt_parts.append(f"Request: {request.prompt}")
        
        return "\n\n".join(prompt_parts)
        
    def _parse_suggestions(self, task_type: TaskType, content: str) -> List[Dict]:
        """Parse AI response for structured suggestions"""
        suggestions = []
        
        if task_type == TaskType.CODE_COMPLETION:
            # Extract code blocks
            import re
            code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', content, re.DOTALL)
            for i, code in enumerate(code_blocks):
                suggestions.append({
                    "type": "completion",
                    "code": code.strip(),
                    "description": f"Completion option {i + 1}",
                    "confidence": 0.9 - (i * 0.1)
                })
                
        elif task_type == TaskType.CODE_REVIEW:
            # Extract review points
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith('-') or line.strip().startswith('•'):
                    suggestions.append({
                        "type": "review_point",
                        "description": line.strip()[1:].strip(),
                        "severity": "medium"
                    })
                    
        elif task_type == TaskType.BUG_FIX:
            # Extract fix suggestions
            if "```" in content:
                import re
                code_blocks = re.findall(r'```(?:\w+)?\n(.*?)\n```', content, re.DOTALL)
                for code in code_blocks:
                    suggestions.append({
                        "type": "fix",
                        "code": code.strip(),
                        "description": "Bug fix suggestion"
                    })
                    
        return suggestions
        
    def _calculate_credits(self, provider: AIProvider, input_length: int, output_length: int) -> int:
        """Calculate credits consumed for AI request"""
        # Base credits per request
        base_credits = {
            AIProvider.CLAUDE: 2,
            AIProvider.OPENAI: 3,
            AIProvider.QWEN: 1
        }
        
        # Additional credits based on content length
        token_estimate = (input_length + output_length) / 4  # Rough token estimate
        length_credits = max(1, int(token_estimate / 1000))
        
        return base_credits.get(provider, 2) + length_credits
        
    async def generate_code_completion(
        self,
        context: CodeContext,
        user_id: str,
        max_suggestions: int = 3
    ) -> List[Dict]:
        """Generate code completions for cursor position"""
        request = AIRequest(
            task_type=TaskType.CODE_COMPLETION,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt="Provide intelligent code completion at the cursor position. Suggest multiple alternatives if applicable.",
            user_id=user_id,
            temperature=0.1,
            max_tokens=500
        )
        
        response = await self.process_request(request)
        return response.suggestions[:max_suggestions]
        
    async def chat_stream(
        self,
        messages: List[Dict],
        user_id: str,
        project_context: Optional[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """Stream chat responses"""
        # Build context from messages
        context = CodeContext(
            file_path="chat",
            content="",
            language="text",
            cursor_position=0,
            project_context=project_context
        )
        
        # Create chat request
        conversation = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
        
        request = AIRequest(
            task_type=TaskType.CHAT,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt=conversation,
            user_id=user_id,
            temperature=0.7,
            max_tokens=1500
        )
        
        # For now, return the full response
        # In production, this would stream tokens
        response = await self.process_request(request)
        
        # Simulate streaming by yielding chunks
        words = response.content.split()
        for i in range(0, len(words), 3):
            chunk = " ".join(words[i:i+3]) + " "
            yield chunk
            await asyncio.sleep(0.1)  # Simulate streaming delay
            
    async def implement_feature(
        self,
        feature_description: str,
        project_context: Dict,
        user_id: str
    ) -> Dict:
        """Autonomously implement a feature"""
        context = CodeContext(
            file_path="feature_implementation",
            content="",
            language="python",  # Default, would be determined from project
            cursor_position=0,
            project_context=project_context
        )
        
        request = AIRequest(
            task_type=TaskType.FEATURE_IMPLEMENTATION,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt=f"Implement the following feature: {feature_description}. Provide complete, production-ready code with proper error handling, tests, and documentation.",
            user_id=user_id,
            temperature=0.2,
            max_tokens=2000
        )
        
        response = await self.process_request(request)
        
        return {
            "implementation": response.content,
            "suggestions": response.suggestions,
            "credits_consumed": response.credits_consumed,
            "confidence": response.confidence
        }