"""
AI API endpoints for CodeForge
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json

from ...services.ai_service import MultiAgentAI, AIRequest, CodeContext, TaskType, AIProvider
from ...auth.dependencies import get_current_user
from ...models.user import User


router = APIRouter(prefix="/ai", tags=["ai"])

# Shared AI service instance
ai_service = MultiAgentAI()


class CodeCompletionRequest(BaseModel):
    file_path: str
    content: str
    language: str
    cursor_position: int
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    max_suggestions: int = 3


class CodeExplanationRequest(BaseModel):
    file_path: str
    content: str
    language: str
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None


class CodeReviewRequest(BaseModel):
    file_path: str
    content: str
    language: str
    focus_areas: List[str] = ["bugs", "performance", "security", "style"]


class BugFixRequest(BaseModel):
    file_path: str
    content: str
    language: str
    error_message: Optional[str] = None
    description: str


class RefactorRequest(BaseModel):
    file_path: str
    content: str
    language: str
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    refactor_type: str = "improve"  # improve, extract_method, rename, etc.


class ChatMessage(BaseModel):
    role: str  # user, assistant
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    project_context: Optional[Dict] = None
    stream: bool = True


class FeatureImplementationRequest(BaseModel):
    description: str
    requirements: List[str] = []
    project_context: Dict
    language: str = "python"
    framework: Optional[str] = None


class AIResponse(BaseModel):
    success: bool
    content: str
    suggestions: List[Dict] = []
    confidence: float = 0.0
    processing_time: float = 0.0
    credits_consumed: int = 0


@router.post("/complete", response_model=AIResponse)
async def code_completion(
    request: CodeCompletionRequest,
    current_user: User = Depends(get_current_user)
):
    """Get AI code completions"""
    try:
        context = CodeContext(
            file_path=request.file_path,
            content=request.content,
            language=request.language,
            cursor_position=request.cursor_position,
            selection_start=request.selection_start,
            selection_end=request.selection_end
        )
        
        suggestions = await ai_service.generate_code_completion(
            context=context,
            user_id=current_user.id,
            max_suggestions=request.max_suggestions
        )
        
        return AIResponse(
            success=True,
            content="Code completions generated successfully",
            suggestions=suggestions,
            confidence=0.9,
            processing_time=0.5,
            credits_consumed=2
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code completion failed: {str(e)}"
        )


@router.post("/explain", response_model=AIResponse)
async def explain_code(
    request: CodeExplanationRequest,
    current_user: User = Depends(get_current_user)
):
    """Get AI code explanation"""
    try:
        context = CodeContext(
            file_path=request.file_path,
            content=request.content,
            language=request.language,
            cursor_position=0,
            selection_start=request.selection_start,
            selection_end=request.selection_end
        )
        
        ai_request = AIRequest(
            task_type=TaskType.CODE_EXPLANATION,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt="Explain this code clearly and comprehensively.",
            user_id=current_user.id
        )
        
        response = await ai_service.process_request(ai_request)
        
        return AIResponse(
            success=True,
            content=response.content,
            suggestions=response.suggestions,
            confidence=response.confidence,
            processing_time=response.processing_time,
            credits_consumed=response.credits_consumed
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code explanation failed: {str(e)}"
        )


@router.post("/review", response_model=AIResponse)
async def review_code(
    request: CodeReviewRequest,
    current_user: User = Depends(get_current_user)
):
    """Get AI code review"""
    try:
        context = CodeContext(
            file_path=request.file_path,
            content=request.content,
            language=request.language,
            cursor_position=0
        )
        
        focus_text = ", ".join(request.focus_areas)
        
        ai_request = AIRequest(
            task_type=TaskType.CODE_REVIEW,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt=f"Perform a thorough code review focusing on: {focus_text}. Provide specific, actionable feedback.",
            user_id=current_user.id
        )
        
        response = await ai_service.process_request(ai_request)
        
        return AIResponse(
            success=True,
            content=response.content,
            suggestions=response.suggestions,
            confidence=response.confidence,
            processing_time=response.processing_time,
            credits_consumed=response.credits_consumed
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Code review failed: {str(e)}"
        )


@router.post("/fix", response_model=AIResponse)
async def fix_bug(
    request: BugFixRequest,
    current_user: User = Depends(get_current_user)
):
    """Get AI bug fix suggestions"""
    try:
        context = CodeContext(
            file_path=request.file_path,
            content=request.content,
            language=request.language,
            cursor_position=0
        )
        
        prompt = f"Fix the bug in this code. Description: {request.description}"
        if request.error_message:
            prompt += f"\nError message: {request.error_message}"
            
        ai_request = AIRequest(
            task_type=TaskType.BUG_FIX,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt=prompt,
            user_id=current_user.id
        )
        
        response = await ai_service.process_request(ai_request)
        
        return AIResponse(
            success=True,
            content=response.content,
            suggestions=response.suggestions,
            confidence=response.confidence,
            processing_time=response.processing_time,
            credits_consumed=response.credits_consumed
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Bug fix failed: {str(e)}"
        )


@router.post("/refactor", response_model=AIResponse)
async def refactor_code(
    request: RefactorRequest,
    current_user: User = Depends(get_current_user)
):
    """Get AI refactoring suggestions"""
    try:
        context = CodeContext(
            file_path=request.file_path,
            content=request.content,
            language=request.language,
            cursor_position=0,
            selection_start=request.selection_start,
            selection_end=request.selection_end
        )
        
        ai_request = AIRequest(
            task_type=TaskType.REFACTORING,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt=f"Refactor this code to {request.refactor_type}. Improve structure, readability, and maintainability.",
            user_id=current_user.id
        )
        
        response = await ai_service.process_request(ai_request)
        
        return AIResponse(
            success=True,
            content=response.content,
            suggestions=response.suggestions,
            confidence=response.confidence,
            processing_time=response.processing_time,
            credits_consumed=response.credits_consumed
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Refactoring failed: {str(e)}"
        )


@router.post("/chat")
async def chat_with_ai(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """Chat with AI assistant"""
    try:
        # Convert Pydantic models to dicts
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        if request.stream:
            # Return streaming response
            async def generate():
                async for chunk in ai_service.chat_stream(
                    messages=messages,
                    user_id=current_user.id,
                    project_context=request.project_context
                ):
                    yield f"data: {json.dumps({'content': chunk})}\n\n"
                yield "data: [DONE]\n\n"
                
            return StreamingResponse(
                generate(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            # Return complete response
            full_response = ""
            async for chunk in ai_service.chat_stream(
                messages=messages,
                user_id=current_user.id,
                project_context=request.project_context
            ):
                full_response += chunk
                
            return AIResponse(
                success=True,
                content=full_response.strip(),
                confidence=0.8,
                credits_consumed=3
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.post("/implement-feature", response_model=Dict[str, Any])
async def implement_feature(
    request: FeatureImplementationRequest,
    current_user: User = Depends(get_current_user)
):
    """Implement a feature autonomously with AI"""
    try:
        result = await ai_service.implement_feature(
            feature_description=request.description,
            project_context=request.project_context,
            user_id=current_user.id
        )
        
        return {
            "success": True,
            "feature_description": request.description,
            "implementation": result["implementation"],
            "suggestions": result["suggestions"],
            "confidence": result["confidence"],
            "credits_consumed": result["credits_consumed"],
            "next_steps": [
                "Review the generated code",
                "Test the implementation",
                "Integrate with existing codebase",
                "Update documentation"
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Feature implementation failed: {str(e)}"
        )


@router.post("/generate-tests", response_model=AIResponse)
async def generate_tests(
    request: CodeExplanationRequest,  # Reuse same request structure
    current_user: User = Depends(get_current_user)
):
    """Generate tests for code"""
    try:
        context = CodeContext(
            file_path=request.file_path,
            content=request.content,
            language=request.language,
            cursor_position=0,
            selection_start=request.selection_start,
            selection_end=request.selection_end
        )
        
        ai_request = AIRequest(
            task_type=TaskType.TESTING,
            provider=AIProvider.OPENAI,
            context=context,
            prompt="Generate comprehensive unit tests for this code. Include edge cases and error scenarios.",
            user_id=current_user.id
        )
        
        response = await ai_service.process_request(ai_request)
        
        return AIResponse(
            success=True,
            content=response.content,
            suggestions=response.suggestions,
            confidence=response.confidence,
            processing_time=response.processing_time,
            credits_consumed=response.credits_consumed
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Test generation failed: {str(e)}"
        )


@router.post("/generate-docs", response_model=AIResponse)
async def generate_documentation(
    request: CodeExplanationRequest,  # Reuse same request structure
    current_user: User = Depends(get_current_user)
):
    """Generate documentation for code"""
    try:
        context = CodeContext(
            file_path=request.file_path,
            content=request.content,
            language=request.language,
            cursor_position=0,
            selection_start=request.selection_start,
            selection_end=request.selection_end
        )
        
        ai_request = AIRequest(
            task_type=TaskType.DOCUMENTATION,
            provider=AIProvider.CLAUDE,
            context=context,
            prompt="Generate comprehensive documentation for this code including docstrings, comments, and usage examples.",
            user_id=current_user.id
        )
        
        response = await ai_service.process_request(ai_request)
        
        return AIResponse(
            success=True,
            content=response.content,
            suggestions=response.suggestions,
            confidence=response.confidence,
            processing_time=response.processing_time,
            credits_consumed=response.credits_consumed
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Documentation generation failed: {str(e)}"
        )


@router.get("/providers")
async def get_ai_providers(current_user: User = Depends(get_current_user)):
    """Get available AI providers and their capabilities"""
    return {
        "providers": [
            {
                "name": "Claude",
                "id": "claude",
                "available": ai_service.claude_client is not None,
                "capabilities": ["completion", "explanation", "review", "fix", "refactor", "documentation", "chat"],
                "cost_per_request": 2
            },
            {
                "name": "OpenAI GPT-4",
                "id": "openai", 
                "available": ai_service.openai_client is not None,
                "capabilities": ["completion", "explanation", "review", "testing", "chat"],
                "cost_per_request": 3
            },
            {
                "name": "Qwen 2.5 Coder",
                "id": "qwen",
                "available": True,  # Local model
                "capabilities": ["completion", "explanation"],
                "cost_per_request": 1
            }
        ],
        "default_assignments": ai_service.agents
    }