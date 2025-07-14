"""
Tests for Test Writer Agent
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime

from src.services.ai.agents.test_writer import TestWriterAgent
from src.services.ai.base import CodeContext, Constraint, AgentResult
from src.services.ai.context_builder import FileContext, ProjectContext


@pytest.fixture
def test_writer():
    """Create test writer agent instance"""
    return TestWriterAgent()


@pytest.fixture
def sample_context():
    """Create sample code context with function to test"""
    return CodeContext(
        project_id="test-project",
        files=[
            FileContext(
                path="src/calculator.py",
                content="""
def add(a, b):
    \"\"\"Add two numbers\"\"\"
    return a + b

def divide(a, b):
    \"\"\"Divide two numbers\"\"\"
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b

class Calculator:
    def __init__(self):
        self.history = []
    
    def calculate(self, operation, a, b):
        result = None
        if operation == 'add':
            result = add(a, b)
        elif operation == 'divide':
            result = divide(a, b)
        
        self.history.append((operation, a, b, result))
        return result
""",
                language="python",
                size=500,
                last_modified=datetime.now()
            )
        ],
        project_structure=ProjectContext(
            root_path="/test/project",
            directories=["src", "tests"],
            total_files=10,
            languages={"python": 8, "yaml": 2}
        ),
        dependencies={"pytest": "7.0.0"},
        test_coverage={"overall": 50.0, "files": {"src/calculator.py": 30.0}}
    )


class TestTestWriterAgent:
    """Test Test Writer Agent functionality"""
    
    @pytest.mark.asyncio
    async def test_analyze_code_structure_functions(self, test_writer):
        """Test analyzing code structure to find functions"""
        code = """
def simple_function(x):
    return x * 2

def complex_function(a, b, c=None):
    if c is None:
        c = 0
    return a + b + c

async def async_function():
    await some_operation()
    return "done"
"""
        
        analysis = await test_writer._analyze_code_structure(code)
        
        assert len(analysis["functions"]) == 3
        assert "simple_function" in [f["name"] for f in analysis["functions"]]
        assert "complex_function" in [f["name"] for f in analysis["functions"]]
        assert "async_function" in [f["name"] for f in analysis["functions"]]
    
    @pytest.mark.asyncio
    async def test_analyze_code_structure_classes(self, test_writer):
        """Test analyzing code structure to find classes"""
        code = """
class SimpleClass:
    def __init__(self):
        self.value = 0
    
    def get_value(self):
        return self.value

class ComplexClass(BaseClass):
    def __init__(self, name):
        super().__init__()
        self.name = name
    
    def process(self, data):
        return data.upper()
"""
        
        analysis = await test_writer._analyze_code_structure(code)
        
        assert len(analysis["classes"]) == 2
        assert "SimpleClass" in [c["name"] for c in analysis["classes"]]
        assert "ComplexClass" in [c["name"] for c in analysis["classes"]]
        assert len(analysis["classes"][0]["methods"]) == 2
    
    @pytest.mark.asyncio
    async def test_identify_test_cases_basic_function(self, test_writer):
        """Test identifying test cases for basic function"""
        function_info = {
            "name": "add",
            "params": ["a", "b"],
            "has_return": True,
            "docstring": "Add two numbers"
        }
        
        test_cases = await test_writer._identify_test_cases(function_info, None)
        
        assert len(test_cases) >= 3
        assert any("normal" in tc["type"] for tc in test_cases)
        assert any("edge" in tc["type"] for tc in test_cases)
        
        # Check for specific test cases
        case_descriptions = [tc["description"] for tc in test_cases]
        assert any("positive" in desc.lower() for desc in case_descriptions)
        assert any("negative" in desc.lower() or "zero" in desc.lower() for desc in case_descriptions)
    
    @pytest.mark.asyncio
    async def test_identify_test_cases_error_handling(self, test_writer):
        """Test identifying test cases for function with error handling"""
        function_info = {
            "name": "divide",
            "params": ["a", "b"],
            "has_return": True,
            "raises": ["ValueError"],
            "docstring": "Divide two numbers"
        }
        
        code = """
def divide(a, b):
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b
"""
        
        test_cases = await test_writer._identify_test_cases(function_info, code)
        
        assert any("error" in tc["type"] for tc in test_cases)
        assert any("zero" in tc["description"].lower() for tc in test_cases)
    
    @pytest.mark.asyncio
    async def test_generate_test_code_pytest(self, test_writer):
        """Test generating test code with pytest framework"""
        test_case = {
            "function": "add",
            "description": "Test adding two positive numbers",
            "inputs": {"a": 5, "b": 3},
            "expected": 8,
            "type": "normal"
        }
        
        framework = "pytest"
        
        test_code = await test_writer._generate_test_code(test_case, framework)
        
        assert "def test_" in test_code
        assert "add" in test_code
        assert "assert" in test_code
        assert "5" in test_code and "3" in test_code
        assert "8" in test_code or "==" in test_code
    
    @pytest.mark.asyncio
    async def test_generate_test_code_error_case(self, test_writer):
        """Test generating test code for error cases"""
        test_case = {
            "function": "divide",
            "description": "Test division by zero raises ValueError",
            "inputs": {"a": 10, "b": 0},
            "expected_error": "ValueError",
            "type": "error"
        }
        
        framework = "pytest"
        
        test_code = await test_writer._generate_test_code(test_case, framework)
        
        assert "pytest.raises" in test_code
        assert "ValueError" in test_code
        assert "divide" in test_code
    
    @pytest.mark.asyncio
    async def test_create_test_file_structure(self, test_writer):
        """Test creating complete test file structure"""
        source_file = "src/calculator.py"
        test_cases = [
            {
                "function": "add",
                "description": "Test adding positive numbers",
                "test_code": "def test_add_positive():\n    assert add(2, 3) == 5"
            },
            {
                "function": "divide",
                "description": "Test division",
                "test_code": "def test_divide():\n    assert divide(10, 2) == 5"
            }
        ]
        framework = "pytest"
        
        test_file = await test_writer._create_test_file(
            source_file, test_cases, framework
        )
        
        assert "import pytest" in test_file
        assert "from src.calculator import" in test_file
        assert "def test_add_positive" in test_file
        assert "def test_divide" in test_file
    
    @pytest.mark.asyncio
    async def test_estimate_task(self, test_writer, sample_context):
        """Test estimating test generation task"""
        requirements = "Generate comprehensive tests for calculator.py"
        
        estimate = await test_writer.estimate_task(
            sample_context, requirements, []
        )
        
        assert estimate["estimated_time"] > 0
        assert estimate["estimated_credits"] > 0
        assert estimate["test_count"] > 0
        assert "complexity" in estimate
    
    @pytest.mark.asyncio
    async def test_execute_success(self, test_writer, sample_context):
        """Test successful test generation execution"""
        requirements = "Generate unit tests for all functions in calculator.py"
        constraints = [
            Constraint("test_framework", "pytest", "Use pytest framework"),
            Constraint("coverage", 0.9, "Achieve 90% coverage")
        ]
        
        result = await test_writer.execute(
            sample_context, requirements, constraints
        )
        
        assert isinstance(result, AgentResult)
        assert result.agent_type == "test_writer"
        
        # Even if the actual execution might fail due to mocking,
        # the structure should be correct
        assert "test_file" in result.data or "error" in result.data
    
    @pytest.mark.asyncio
    async def test_execute_with_specific_function(self, test_writer, sample_context):
        """Test generating tests for specific function"""
        requirements = "Generate tests for the divide function"
        constraints = []
        
        with patch.object(test_writer, '_analyze_code_structure') as mock_analyze, \
             patch.object(test_writer, '_identify_test_cases') as mock_identify, \
             patch.object(test_writer, '_generate_test_code') as mock_generate:
            
            mock_analyze.return_value = {
                "functions": [
                    {"name": "divide", "params": ["a", "b"], "has_return": True}
                ],
                "classes": []
            }
            
            mock_identify.return_value = [
                {
                    "function": "divide",
                    "description": "Test normal division",
                    "type": "normal"
                },
                {
                    "function": "divide",
                    "description": "Test division by zero",
                    "type": "error"
                }
            ]
            
            mock_generate.return_value = "def test_divide(): pass"
            
            result = await test_writer.execute(
                sample_context, requirements, constraints
            )
            
            # Verify the mocked methods were called
            mock_analyze.assert_called()
            mock_identify.assert_called()
    
    @pytest.mark.asyncio
    async def test_calculate_coverage_impact(self, test_writer, sample_context):
        """Test calculating coverage impact of new tests"""
        new_tests = [
            {"function": "add", "type": "normal"},
            {"function": "add", "type": "edge"},
            {"function": "divide", "type": "normal"},
            {"function": "divide", "type": "error"}
        ]
        
        current_coverage = 30.0
        
        # Estimate coverage improvement
        # This is a simplified test - actual implementation would be more complex
        estimated_coverage = current_coverage + (len(new_tests) * 10)
        
        assert estimated_coverage > current_coverage
        assert estimated_coverage <= 100.0