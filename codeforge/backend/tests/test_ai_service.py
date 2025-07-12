"""
Tests for AI Service
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from src.services.ai_service import (
    MultiAgentAI, AIRequest, AIResponse, CodeContext, 
    TaskType, AIProvider
)


class TestMultiAgentAI:
    """Test suite for MultiAgentAI service"""

    @pytest.fixture
    def ai_service(self):
        """Create AI service instance"""
        return MultiAgentAI()

    @pytest.fixture
    def sample_code_context(self):
        """Sample code context"""
        return CodeContext(
            file_path="test.py",
            content="def hello():\n    print('Hello, world!')",
            language="python",
            cursor_position=25,
            selection_start=0,
            selection_end=44
        )

    @pytest.fixture
    def sample_ai_request(self, sample_code_context):
        """Sample AI request"""
        return AIRequest(
            task_type=TaskType.CODE_COMPLETION,
            provider=AIProvider.CLAUDE,
            context=sample_code_context,
            prompt="Complete this function",
            user_id="test-user-123"
        )

    @pytest.mark.asyncio
    async def test_process_request_code_completion(self, ai_service, sample_ai_request):
        """Test processing code completion request"""
        with patch.object(ai_service, '_call_claude', new_callable=AsyncMock) as mock_claude:
            mock_claude.return_value = "def hello():\n    print('Hello, world!')\n    return 'Hello'"
            
            response = await ai_service.process_request(sample_ai_request)
            
            assert isinstance(response, AIResponse)
            assert response.task_type == TaskType.CODE_COMPLETION
            assert response.provider == AIProvider.CLAUDE
            assert "Hello" in response.content
            assert response.credits_consumed > 0

    @pytest.mark.asyncio
    async def test_process_request_code_explanation(self, ai_service, sample_code_context):
        """Test processing code explanation request"""
        request = AIRequest(
            task_type=TaskType.CODE_EXPLANATION,
            provider=AIProvider.CLAUDE,
            context=sample_code_context,
            prompt="Explain this code",
            user_id="test-user-123"
        )
        
        with patch.object(ai_service, '_call_claude', new_callable=AsyncMock) as mock_claude:
            mock_claude.return_value = "This function prints a greeting message to the console."
            
            response = await ai_service.process_request(request)
            
            assert response.task_type == TaskType.CODE_EXPLANATION
            assert "greeting" in response.content.lower()

    @pytest.mark.asyncio
    async def test_process_request_with_openai(self, ai_service, sample_code_context):
        """Test processing request with OpenAI provider"""
        request = AIRequest(
            task_type=TaskType.TESTING,
            provider=AIProvider.OPENAI,
            context=sample_code_context,
            prompt="Generate tests",
            user_id="test-user-123"
        )
        
        with patch.object(ai_service, '_call_openai', new_callable=AsyncMock) as mock_openai:
            mock_openai.return_value = "def test_hello():\n    assert hello() == 'Hello'"
            
            response = await ai_service.process_request(request)
            
            assert response.task_type == TaskType.TESTING
            assert response.provider == AIProvider.OPENAI
            assert "test_hello" in response.content

    @pytest.mark.asyncio
    async def test_process_request_error_handling(self, ai_service, sample_ai_request):
        """Test error handling in process_request"""
        with patch.object(ai_service, '_call_claude', new_callable=AsyncMock) as mock_claude:
            mock_claude.side_effect = Exception("API Error")
            
            response = await ai_service.process_request(sample_ai_request)
            
            assert "Error" in response.content
            assert response.confidence == 0.0
            assert response.credits_consumed == 0

    @pytest.mark.asyncio
    async def test_generate_code_completion(self, ai_service, sample_code_context):
        """Test generating code completions"""
        with patch.object(ai_service, 'process_request', new_callable=AsyncMock) as mock_process:
            mock_response = Mock()
            mock_response.suggestions = [
                {"type": "completion", "code": "return 'Hello'", "confidence": 0.9},
                {"type": "completion", "code": "pass", "confidence": 0.5}
            ]
            mock_process.return_value = mock_response
            
            suggestions = await ai_service.generate_code_completion(
                context=sample_code_context,
                user_id="test-user-123",
                max_suggestions=2
            )
            
            assert len(suggestions) == 2
            assert suggestions[0]["confidence"] > suggestions[1]["confidence"]

    @pytest.mark.asyncio
    async def test_chat_stream(self, ai_service):
        """Test chat streaming functionality"""
        messages = [
            {"role": "user", "content": "How do I write a function in Python?"}
        ]
        
        with patch.object(ai_service, 'process_request', new_callable=AsyncMock) as mock_process:
            mock_response = Mock()
            mock_response.content = "To write a function in Python, use the 'def' keyword"
            mock_process.return_value = mock_response
            
            chunks = []
            async for chunk in ai_service.chat_stream(
                messages=messages,
                user_id="test-user-123"
            ):
                chunks.append(chunk)
                
            full_response = "".join(chunks).strip()
            assert "def" in full_response
            assert len(chunks) > 1  # Should be streaming

    @pytest.mark.asyncio
    async def test_implement_feature(self, ai_service):
        """Test autonomous feature implementation"""
        project_context = {
            "language": "python",
            "framework": "fastapi",
            "existing_files": ["main.py", "models.py"]
        }
        
        with patch.object(ai_service, 'process_request', new_callable=AsyncMock) as mock_process:
            mock_response = Mock()
            mock_response.content = "# User authentication feature\nclass UserAuth:\n    def login(self):\n        pass"
            mock_response.suggestions = [{"type": "file", "name": "auth.py", "content": "..."}]
            mock_response.credits_consumed = 10
            mock_response.confidence = 0.85
            mock_process.return_value = mock_response
            
            result = await ai_service.implement_feature(
                feature_description="Add user authentication",
                project_context=project_context,
                user_id="test-user-123"
            )
            
            assert result["implementation"] == mock_response.content
            assert result["confidence"] == 0.85
            assert result["credits_consumed"] == 10

    def test_get_system_prompt_code_completion(self, ai_service, sample_code_context):
        """Test system prompt generation for code completion"""
        prompt = ai_service._get_system_prompt(TaskType.CODE_COMPLETION, sample_code_context)
        
        assert "CodeCompletion" in prompt
        assert "python" in prompt
        assert "test.py" in prompt
        assert "accurate" in prompt

    def test_get_system_prompt_code_review(self, ai_service, sample_code_context):
        """Test system prompt generation for code review"""
        prompt = ai_service._get_system_prompt(TaskType.CODE_REVIEW, sample_code_context)
        
        assert "CodeReviewer" in prompt
        assert "bugs" in prompt
        assert "security" in prompt
        assert "performance" in prompt

    def test_build_user_prompt(self, ai_service, sample_ai_request):
        """Test user prompt building"""
        prompt = ai_service._build_user_prompt(sample_ai_request)
        
        assert "Current file content:" in prompt
        assert "```python" in prompt
        assert sample_ai_request.context.content in prompt
        assert "Cursor position:" in prompt
        assert sample_ai_request.prompt in prompt

    def test_build_user_prompt_with_selection(self, ai_service, sample_code_context):
        """Test user prompt building with text selection"""
        request = AIRequest(
            task_type=TaskType.CODE_EXPLANATION,
            provider=AIProvider.CLAUDE,
            context=sample_code_context,
            prompt="Explain selected code",
            user_id="test-user-123"
        )
        
        prompt = ai_service._build_user_prompt(request)
        
        assert "Selected text:" in prompt
        assert "def hello():" in prompt

    def test_parse_suggestions_code_completion(self, ai_service):
        """Test parsing suggestions for code completion"""
        content = """Here are some completions:
        
```python
return 'Hello, world!'
```

```python
pass
```
        """
        
        suggestions = ai_service._parse_suggestions(TaskType.CODE_COMPLETION, content)
        
        assert len(suggestions) == 2
        assert suggestions[0]["type"] == "completion"
        assert "Hello, world!" in suggestions[0]["code"]
        assert suggestions[0]["confidence"] > suggestions[1]["confidence"]

    def test_parse_suggestions_code_review(self, ai_service):
        """Test parsing suggestions for code review"""
        content = """Code review findings:
        
- Function lacks error handling
- Variable names could be more descriptive
• Consider adding type hints
        """
        
        suggestions = ai_service._parse_suggestions(TaskType.CODE_REVIEW, content)
        
        assert len(suggestions) == 3
        assert all(s["type"] == "review_point" for s in suggestions)
        assert "error handling" in suggestions[0]["description"]

    def test_parse_suggestions_bug_fix(self, ai_service):
        """Test parsing suggestions for bug fixes"""
        content = """Here's the fix:
        
```python
def hello():
    try:
        print('Hello, world!')
        return 'Hello'
    except Exception as e:
        print(f'Error: {e}')
        return None
```
        """
        
        suggestions = ai_service._parse_suggestions(TaskType.BUG_FIX, content)
        
        assert len(suggestions) == 1
        assert suggestions[0]["type"] == "fix"
        assert "try:" in suggestions[0]["code"]

    def test_calculate_credits_claude(self, ai_service):
        """Test credit calculation for Claude"""
        credits = ai_service._calculate_credits(AIProvider.CLAUDE, 1000, 500)
        
        # Base credits (2) + length credits
        assert credits >= 2
        assert credits == 2 + max(1, int((1000 + 500) / 4 / 1000))

    def test_calculate_credits_openai(self, ai_service):
        """Test credit calculation for OpenAI"""
        credits = ai_service._calculate_credits(AIProvider.OPENAI, 1000, 500)
        
        # Base credits (3) + length credits
        assert credits >= 3

    def test_calculate_credits_qwen(self, ai_service):
        """Test credit calculation for Qwen"""
        credits = ai_service._calculate_credits(AIProvider.QWEN, 1000, 500)
        
        # Base credits (1) + length credits
        assert credits >= 1

    @pytest.mark.asyncio
    async def test_call_claude_success(self, ai_service):
        """Test successful Claude API call"""
        with patch('anthropic.Anthropic') as mock_anthropic:
            mock_client = Mock()
            mock_response = Mock()
            mock_response.content = [Mock(text="Test response")]
            mock_client.messages.create.return_value = mock_response
            ai_service.claude_client = mock_client
            
            result = await ai_service._call_claude(
                "System prompt",
                "User prompt",
                temperature=0.1,
                max_tokens=1000
            )
            
            assert result == "Test response"
            mock_client.messages.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_call_claude_no_client(self, ai_service):
        """Test Claude API call without client"""
        ai_service.claude_client = None
        
        with pytest.raises(ValueError, match="Claude API key not configured"):
            await ai_service._call_claude("System", "User")

    @pytest.mark.asyncio
    async def test_call_openai_success(self, ai_service):
        """Test successful OpenAI API call"""
        with patch('openai.ChatCompletion') as mock_chat:
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="Test response"))]
            mock_chat.create.return_value = mock_response
            ai_service.openai_client = Mock()
            
            result = await ai_service._call_openai(
                "System prompt",
                "User prompt",
                temperature=0.1,
                max_tokens=1000
            )
            
            assert result == "Test response"

    @pytest.mark.asyncio
    async def test_call_qwen_mock_response(self, ai_service):
        """Test Qwen model call (mock implementation)"""
        result = await ai_service._call_qwen(
            "System prompt",
            "User prompt asking about Python",
            temperature=0.1,
            max_tokens=1000
        )
        
        assert "Mock Qwen response" in result
        assert "Python" in result

    def test_agent_configuration(self, ai_service):
        """Test agent configuration"""
        # Test that all task types have agent configurations
        for task_type in TaskType:
            assert task_type in ai_service.agents
            
        # Test specific agent configurations
        completion_agent = ai_service.agents[TaskType.CODE_COMPLETION]
        assert completion_agent["provider"] == AIProvider.CLAUDE
        assert completion_agent["temperature"] == 0.1
        assert completion_agent["max_tokens"] == 500
        
        testing_agent = ai_service.agents[TaskType.TESTING]
        assert testing_agent["provider"] == AIProvider.OPENAI
        assert testing_agent["temperature"] == 0.3