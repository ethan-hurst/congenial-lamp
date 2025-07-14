"""
Test Writer Agent - Generates comprehensive test suites
"""
import re
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from sqlalchemy.orm import Session

from ....models.ai_agent import (
    AgentTask, AgentArtifact, TestSuite,
    AgentResult, TaskStatus
)
from ....config.settings import settings
from ...ai_service import AIProvider, TaskType, AIRequest, CodeContext as AICodeContext

logger = logging.getLogger(__name__)


class TestFramework:
    """Test framework configuration"""
    def __init__(self, name: str, language: str, patterns: Dict):
        self.name = name
        self.language = language
        self.patterns = patterns  # Test patterns and conventions


class DataSchema:
    """Data schema for test data generation"""
    def __init__(self, fields: Dict[str, str], constraints: Dict):
        self.fields = fields
        self.constraints = constraints


class TestData:
    """Generated test data"""
    def __init__(self, examples: List[Dict], edge_cases: List[Dict]):
        self.examples = examples
        self.edge_cases = edge_cases


class TestWriterAgent:
    """
    Agent that generates comprehensive test suites for code.
    Analyzes code structure, identifies test scenarios,
    and generates unit, integration, and edge case tests.
    """
    
    def __init__(self, db: Session):
        self.db = db
        # Initialize AI service
        from ...ai_service import MultiAgentAI
        self.ai_service = MultiAgentAI()
        
        # Test framework configurations
        self.test_frameworks = {
            "python": {
                "pytest": TestFramework(
                    "pytest",
                    "python",
                    {
                        "test_file": "test_{}.py",
                        "test_function": "test_{}",
                        "assertion": "assert",
                        "setup": "def setup_method(self):",
                        "teardown": "def teardown_method(self):"
                    }
                ),
                "unittest": TestFramework(
                    "unittest",
                    "python",
                    {
                        "test_file": "test_{}.py",
                        "test_class": "Test{}",
                        "test_function": "test_{}",
                        "assertion": "self.assertEqual",
                        "setup": "def setUp(self):",
                        "teardown": "def tearDown(self):"
                    }
                )
            },
            "javascript": {
                "jest": TestFramework(
                    "jest",
                    "javascript",
                    {
                        "test_file": "{}.test.js",
                        "test_function": "test('{}', () => {{",
                        "assertion": "expect",
                        "setup": "beforeEach(() => {",
                        "teardown": "afterEach(() => {"
                    }
                ),
                "mocha": TestFramework(
                    "mocha",
                    "javascript",
                    {
                        "test_file": "{}.spec.js",
                        "test_function": "it('{}', () => {{",
                        "assertion": "expect",
                        "setup": "beforeEach(() => {",
                        "teardown": "afterEach(() => {"
                    }
                )
            }
        }
    
    async def execute(
        self,
        context: Any,
        requirements: str,
        constraints: List[Any],
        task_id: str
    ) -> AgentResult:
        """Execute test generation task"""
        
        try:
            # Update task status
            task = self.db.query(AgentTask).filter(AgentTask.id == task_id).first()
            if task:
                task.current_step = "Analyzing code structure"
                task.progress = 0.1
                self.db.commit()
            
            # Extract code to test
            code_file = self._extract_code_file(context, requirements)
            if not code_file:
                raise ValueError("No code file specified for testing")
            
            # Determine test framework
            test_framework = self._determine_test_framework(code_file, constraints)
            
            # Set coverage target
            coverage_target = 0.8
            for constraint in constraints:
                if hasattr(constraint, 'type') and constraint.type == "coverage":
                    coverage_target = constraint.value
            
            if task:
                task.current_step = "Generating test scenarios"
                task.progress = 0.3
                self.db.commit()
            
            # Generate tests
            test_suite = await self.generate_tests(
                code_file,
                test_framework,
                coverage_target
            )
            
            if task:
                task.current_step = "Creating test files"
                task.progress = 0.7
                self.db.commit()
            
            # Create test artifacts
            artifacts = []
            for test_file in test_suite.test_files:
                artifact = AgentArtifact(
                    task_id=task_id,
                    artifact_type="test",
                    file_path=test_file["path"],
                    content=test_file["content"],
                    language=test_framework.language,
                    line_count=len(test_file["content"].split('\n')),
                    size_bytes=len(test_file["content"].encode('utf-8'))
                )
                self.db.add(artifact)
                artifacts.append(test_file)
            
            self.db.commit()
            
            if task:
                task.current_step = "Completed"
                task.progress = 1.0
                task.status = TaskStatus.COMPLETED.value
                task.completed_at = datetime.utcnow()
                self.db.commit()
            
            return AgentResult(
                success=True,
                output={
                    "test_suite": {
                        "framework": test_framework.name,
                        "coverage": test_suite.coverage,
                        "total_tests": len(test_suite.tests),
                        "test_files": len(test_suite.test_files)
                    }
                },
                artifacts=artifacts,
                metrics={
                    "confidence": 0.9,
                    "coverage": test_suite.coverage,
                    "test_count": len(test_suite.tests)
                }
            )
            
        except Exception as e:
            logger.error(f"Test writer error: {str(e)}")
            
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
        
        if action == "generate_tests":
            # Get code from previous step
            previous_results = context.get("previous_results", [])
            if previous_results and previous_results[0].artifacts:
                # Test the generated code
                code_file = {
                    "path": previous_results[0].artifacts[0]["path"],
                    "content": previous_results[0].artifacts[0]["content"],
                    "language": previous_results[0].artifacts[0].get("language", "python")
                }
                
                test_framework = self._get_default_test_framework(code_file["language"])
                test_suite = await self.generate_tests(code_file, test_framework, 0.8)
                
                return AgentResult(
                    success=True,
                    output={"tests_generated": len(test_suite.tests)},
                    artifacts=test_suite.test_files,
                    metrics={"coverage": test_suite.coverage}
                )
        
        elif action == "analyze_and_generate":
            # Standalone test generation
            return await self.execute(
                context.get("original_context"),
                context.get("requirements", ""),
                [],
                task_id
            )
        
        elif action == "update_tests":
            # Update tests after refactoring
            return await self._update_tests_after_changes(context, task_id)
        
        elif action == "generate_regression_tests":
            # Generate regression tests for bug fixes
            return await self._generate_regression_tests(context, task_id)
        
        else:
            raise ValueError(f"Unknown action: {action}")
    
    async def generate_tests(
        self,
        code_file: Dict,
        test_framework: TestFramework,
        coverage_target: float = 0.8
    ) -> TestSuite:
        """Generate comprehensive test suite for code"""
        
        # Analyze code structure
        code_analysis = self._analyze_code_structure(code_file)
        
        # Identify test scenarios
        test_scenarios = await self._identify_test_scenarios(
            code_file,
            code_analysis,
            coverage_target
        )
        
        # Generate test data
        test_data = await self._generate_test_data(code_analysis)
        
        # Generate individual tests
        tests = []
        for scenario in test_scenarios:
            test_code = await self._generate_test_code(
                scenario,
                code_file,
                test_framework,
                test_data
            )
            tests.append(test_code)
        
        # Organize into test files
        test_files = self._organize_test_files(tests, code_file, test_framework)
        
        # Calculate coverage
        coverage = self._calculate_coverage(tests, code_analysis)
        
        test_suite = TestSuite(
            tests=tests,
            coverage=coverage,
            framework=test_framework.name
        )
        test_suite.test_files = test_files
        
        return test_suite
    
    async def generate_test_data(self, schema: DataSchema) -> TestData:
        """Generate test data based on schema"""
        
        # Build prompt for test data generation
        prompt = f"""
        Generate comprehensive test data for the following schema:
        
        Fields: {schema.fields}
        Constraints: {schema.constraints}
        
        Include:
        1. Valid examples (at least 5)
        2. Edge cases (null, empty, boundary values)
        3. Invalid cases for error testing
        
        Format as JSON.
        """
        
        # Get AI response
        ai_context = AICodeContext(
            file_path="test_data_generation",
            content="",
            language="json",
            cursor_position=0
        )
        
        request = AIRequest(
            task_type=TaskType.TESTING,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system",
            temperature=0.3,
            max_tokens=1000
        )
        
        response = await self.ai_service.process_request(request)
        
        # Parse response
        import json
        try:
            data = json.loads(response.content)
            return TestData(
                examples=data.get("valid_examples", []),
                edge_cases=data.get("edge_cases", [])
            )
        except:
            # Fallback to simple test data
            return TestData(
                examples=[{"id": 1, "name": "test"}],
                edge_cases=[{"id": None, "name": ""}]
            )
    
    async def update_tests(
        self,
        code_changes: List[Dict],
        existing_tests: TestSuite
    ) -> TestSuite:
        """Update tests based on code changes"""
        
        # Analyze what changed
        change_analysis = self._analyze_changes(code_changes)
        
        # Determine which tests need updating
        tests_to_update = []
        tests_to_add = []
        
        for change in change_analysis:
            if change["type"] == "function_added":
                # Need new tests
                tests_to_add.append(change)
            elif change["type"] == "function_modified":
                # Need to update existing tests
                tests_to_update.append(change)
        
        # Update existing tests
        updated_tests = existing_tests.tests.copy()
        
        for test_update in tests_to_update:
            # Find and update relevant tests
            for i, test in enumerate(updated_tests):
                if test.get("function") == test_update["function"]:
                    updated_tests[i] = await self._update_single_test(
                        test,
                        test_update
                    )
        
        # Add new tests
        for new_test_needed in tests_to_add:
            new_test = await self._generate_test_for_function(
                new_test_needed,
                existing_tests.framework
            )
            updated_tests.append(new_test)
        
        # Create updated test suite
        updated_suite = TestSuite(
            tests=updated_tests,
            coverage=existing_tests.coverage,
            framework=existing_tests.framework
        )
        
        return updated_suite
    
    async def estimate_task(self, context: Any, requirements: str) -> Dict:
        """Estimate time and credits for test generation"""
        
        # Estimate based on code complexity
        code_lines = 0
        if hasattr(context, 'content_map'):
            for content in context.content_map.values():
                code_lines += len(content.split('\n'))
        
        if code_lines < 100:
            complexity = "low"
            estimated_time = 60  # 1 minute
            estimated_credits = 10
        elif code_lines < 500:
            complexity = "medium"
            estimated_time = 180  # 3 minutes
            estimated_credits = 30
        else:
            complexity = "high"
            estimated_time = 300  # 5 minutes
            estimated_credits = 50
        
        return {
            "time": estimated_time,
            "credits": estimated_credits,
            "complexity": complexity,
            "confidence": 0.8
        }
    
    def _extract_code_file(self, context: Any, requirements: str) -> Optional[Dict]:
        """Extract code file to test from context"""
        
        # Check if specific file mentioned in requirements
        file_match = re.search(r'test\s+(?:file\s+)?([^\s]+\.\w+)', requirements, re.I)
        if file_match:
            file_path = file_match.group(1)
            
            # Get content from context
            if hasattr(context, 'content_map') and file_path in context.content_map:
                return {
                    "path": file_path,
                    "content": context.content_map[file_path],
                    "language": self._detect_language(file_path)
                }
        
        # If no specific file, use first code file from context
        if hasattr(context, 'file_paths') and context.file_paths:
            for file_path in context.file_paths:
                if self._is_code_file(file_path):
                    content = ""
                    if hasattr(context, 'content_map'):
                        content = context.content_map.get(file_path, "")
                    
                    return {
                        "path": file_path,
                        "content": content,
                        "language": self._detect_language(file_path)
                    }
        
        return None
    
    def _determine_test_framework(self, code_file: Dict, constraints: List[Any]) -> TestFramework:
        """Determine which test framework to use"""
        
        # Check constraints for framework specification
        for constraint in constraints:
            if hasattr(constraint, 'type') and constraint.type == "test_framework":
                framework_name = constraint.value
                language = code_file.get("language", "python")
                
                if language in self.test_frameworks:
                    framework = self.test_frameworks[language].get(framework_name)
                    if framework:
                        return framework
        
        # Use default framework for language
        return self._get_default_test_framework(code_file.get("language", "python"))
    
    def _get_default_test_framework(self, language: str) -> TestFramework:
        """Get default test framework for language"""
        
        defaults = {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest",
            "java": "junit",
            "go": "testing"
        }
        
        framework_name = defaults.get(language, "pytest")
        
        if language in self.test_frameworks:
            framework = self.test_frameworks[language].get(framework_name)
            if framework:
                return framework
        
        # Fallback to pytest
        return self.test_frameworks["python"]["pytest"]
    
    def _analyze_code_structure(self, code_file: Dict) -> Dict:
        """Analyze code structure to identify testable components"""
        
        analysis = {
            "functions": [],
            "classes": [],
            "methods": [],
            "complexity": 0,
            "dependencies": []
        }
        
        content = code_file.get("content", "")
        language = code_file.get("language", "python")
        
        if language == "python":
            # Simple regex-based analysis
            # Find functions
            func_pattern = r'def\s+(\w+)\s*\([^)]*\):'
            for match in re.finditer(func_pattern, content):
                func_name = match.group(1)
                if not func_name.startswith('_'):  # Skip private functions
                    analysis["functions"].append({
                        "name": func_name,
                        "line": content[:match.start()].count('\n') + 1
                    })
            
            # Find classes
            class_pattern = r'class\s+(\w+)(?:\([^)]*\))?:'
            for match in re.finditer(class_pattern, content):
                analysis["classes"].append({
                    "name": match.group(1),
                    "line": content[:match.start()].count('\n') + 1
                })
        
        # Calculate complexity (simple line count based)
        lines = content.split('\n')
        analysis["complexity"] = len(lines) // 50  # Every 50 lines adds complexity
        
        return analysis
    
    async def _identify_test_scenarios(
        self,
        code_file: Dict,
        code_analysis: Dict,
        coverage_target: float
    ) -> List[Dict]:
        """Identify test scenarios to achieve coverage target"""
        
        scenarios = []
        
        # Test each function
        for func in code_analysis.get("functions", []):
            scenarios.extend([
                {
                    "type": "unit",
                    "target": func["name"],
                    "scenario": "normal_operation",
                    "description": f"Test {func['name']} with valid inputs"
                },
                {
                    "type": "unit",
                    "target": func["name"],
                    "scenario": "edge_case",
                    "description": f"Test {func['name']} with edge cases"
                },
                {
                    "type": "unit",
                    "target": func["name"],
                    "scenario": "error_handling",
                    "description": f"Test {func['name']} error handling"
                }
            ])
        
        # Test each class
        for cls in code_analysis.get("classes", []):
            scenarios.extend([
                {
                    "type": "unit",
                    "target": cls["name"],
                    "scenario": "initialization",
                    "description": f"Test {cls['name']} initialization"
                },
                {
                    "type": "unit",
                    "target": cls["name"],
                    "scenario": "methods",
                    "description": f"Test {cls['name']} methods"
                }
            ])
        
        # Add integration tests if multiple components
        if len(code_analysis["functions"]) + len(code_analysis["classes"]) > 3:
            scenarios.append({
                "type": "integration",
                "target": "module",
                "scenario": "component_interaction",
                "description": "Test component interactions"
            })
        
        return scenarios
    
    async def _generate_test_code(
        self,
        scenario: Dict,
        code_file: Dict,
        test_framework: TestFramework,
        test_data: TestData
    ) -> Dict:
        """Generate test code for a specific scenario"""
        
        # Build prompt
        prompt = f"""
        Generate a {test_framework.name} test for the following scenario:
        
        Code to test:
        ```{code_file.get('language', 'python')}
        {code_file.get('content', '')[:1000]}  # Truncate for context
        ```
        
        Test scenario:
        - Type: {scenario['type']}
        - Target: {scenario['target']}
        - Scenario: {scenario['scenario']}
        - Description: {scenario['description']}
        
        Test framework patterns:
        - Test function: {test_framework.patterns.get('test_function', 'test_{}')}
        - Assertion: {test_framework.patterns.get('assertion', 'assert')}
        
        Generate a complete, working test.
        """
        
        # Get AI response
        ai_context = AICodeContext(
            file_path=f"test_{scenario['target']}.py",
            content="",
            language=code_file.get("language", "python"),
            cursor_position=0
        )
        
        request = AIRequest(
            task_type=TaskType.TESTING,
            provider=AIProvider.CLAUDE,
            context=ai_context,
            prompt=prompt,
            user_id="system",
            temperature=0.2,
            max_tokens=1000
        )
        
        response = await self.ai_service.process_request(request)
        
        # Extract test code
        test_code = self._extract_code_from_response(response.content)
        
        return {
            "scenario": scenario,
            "code": test_code,
            "function": scenario['target']
        }
    
    def _organize_test_files(
        self,
        tests: List[Dict],
        code_file: Dict,
        test_framework: TestFramework
    ) -> List[Dict]:
        """Organize tests into test files"""
        
        # Group tests by target
        test_groups = {}
        for test in tests:
            target = test["scenario"]["target"]
            if target not in test_groups:
                test_groups[target] = []
            test_groups[target].append(test)
        
        # Create test files
        test_files = []
        
        for target, target_tests in test_groups.items():
            # Generate test file name
            file_pattern = test_framework.patterns.get("test_file", "test_{}.py")
            test_file_name = file_pattern.format(target.lower())
            
            # Combine test code
            test_content = self._generate_test_file_content(
                target_tests,
                test_framework,
                code_file
            )
            
            test_files.append({
                "path": test_file_name,
                "content": test_content,
                "tests": len(target_tests)
            })
        
        return test_files
    
    def _generate_test_file_content(
        self,
        tests: List[Dict],
        test_framework: TestFramework,
        code_file: Dict
    ) -> str:
        """Generate complete test file content"""
        
        language = test_framework.language
        
        if language == "python":
            # Python test file
            imports = [
                f"import {test_framework.name}",
                f"from {self._get_module_name(code_file['path'])} import *"
            ]
            
            if test_framework.name == "unittest":
                imports.append("import unittest")
            
            content = "\n".join(imports) + "\n\n"
            
            # Add test class if needed
            if test_framework.name == "unittest":
                class_name = test_framework.patterns.get("test_class", "Test{}").format(
                    tests[0]["scenario"]["target"].title()
                )
                content += f"class {class_name}(unittest.TestCase):\n\n"
                
                # Add tests as methods
                for test in tests:
                    content += self._indent(test["code"], 1) + "\n\n"
            else:
                # Add tests as functions
                for test in tests:
                    content += test["code"] + "\n\n"
        
        elif language == "javascript":
            # JavaScript test file
            content = f"const {{ expect }} = require('chai');\n"
            content += f"const {{ {tests[0]['scenario']['target']} }} = require('./{code_file['path']}');\n\n"
            
            content += f"describe('{tests[0]['scenario']['target']}', () => {{\n"
            
            for test in tests:
                content += self._indent(test["code"], 1) + "\n\n"
            
            content += "});\n"
        
        return content
    
    def _calculate_coverage(self, tests: List[Dict], code_analysis: Dict) -> float:
        """Calculate estimated test coverage"""
        
        # Simple coverage calculation based on tested components
        total_components = (
            len(code_analysis.get("functions", [])) +
            len(code_analysis.get("classes", [])) +
            len(code_analysis.get("methods", []))
        )
        
        if total_components == 0:
            return 0.0
        
        tested_components = set()
        for test in tests:
            tested_components.add(test["scenario"]["target"])
        
        coverage = len(tested_components) / max(total_components, 1)
        
        # Boost coverage if we have edge cases and error tests
        has_edge_cases = any(t["scenario"]["scenario"] == "edge_case" for t in tests)
        has_error_tests = any(t["scenario"]["scenario"] == "error_handling" for t in tests)
        
        if has_edge_cases:
            coverage = min(coverage + 0.1, 1.0)
        if has_error_tests:
            coverage = min(coverage + 0.1, 1.0)
        
        return round(coverage, 2)
    
    # Helper methods
    
    def _detect_language(self, file_path: str) -> str:
        """Detect language from file path"""
        
        ext_to_lang = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust"
        }
        
        import os
        ext = os.path.splitext(file_path)[1].lower()
        return ext_to_lang.get(ext, "unknown")
    
    def _is_code_file(self, file_path: str) -> bool:
        """Check if file is a code file"""
        
        code_extensions = {".py", ".js", ".jsx", ".ts", ".tsx", ".java", ".go", ".rs", ".cpp", ".c"}
        import os
        ext = os.path.splitext(file_path)[1].lower()
        return ext in code_extensions
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from AI response"""
        
        # Look for code blocks
        import re
        code_pattern = r'```(?:\w+)?\n(.*?)\n```'
        matches = re.findall(code_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0]
        
        # If no code blocks, return cleaned response
        lines = response.split('\n')
        code_lines = [line for line in lines if line.strip() and not line.strip().endswith(':')]
        return '\n'.join(code_lines)
    
    def _get_module_name(self, file_path: str) -> str:
        """Get module name from file path"""
        
        import os
        module = os.path.splitext(os.path.basename(file_path))[0]
        return module
    
    def _indent(self, text: str, level: int) -> str:
        """Indent text by level"""
        
        indent = "    " * level
        lines = text.split('\n')
        return '\n'.join(indent + line if line.strip() else line for line in lines)
    
    async def _update_tests_after_changes(self, context: Dict, task_id: str) -> AgentResult:
        """Update tests after code changes"""
        
        # Get the changed code from previous results
        previous_results = context.get("previous_results", [])
        if not previous_results:
            return AgentResult(
                success=False,
                output={"error": "No previous results found"},
                artifacts=[],
                metrics={}
            )
        
        # Simple implementation - regenerate tests
        # In production, this would be more sophisticated
        return await self.execute_action("generate_tests", context, task_id)
    
    async def _generate_regression_tests(self, context: Dict, task_id: str) -> AgentResult:
        """Generate regression tests for bug fixes"""
        
        # Get bug fix details from context
        bug_fix_info = context.get("bug_fix_info", {})
        
        # Generate specific regression tests
        prompt = f"""
        Generate regression tests for the following bug fix:
        {bug_fix_info}
        
        Ensure the tests:
        1. Reproduce the original bug scenario
        2. Verify the fix works correctly
        3. Check edge cases around the fix
        """
        
        # For now, use standard test generation
        # In production, this would be specialized for regression testing
        return await self.execute_action("generate_tests", context, task_id)
    
    def _analyze_changes(self, code_changes: List[Dict]) -> List[Dict]:
        """Analyze code changes to determine test impact"""
        
        analysis = []
        
        for change in code_changes:
            if change.get("type") == "added":
                analysis.append({
                    "type": "function_added",
                    "function": change.get("name", "unknown"),
                    "needs": "new_tests"
                })
            elif change.get("type") == "modified":
                analysis.append({
                    "type": "function_modified",
                    "function": change.get("name", "unknown"),
                    "needs": "update_tests"
                })
        
        return analysis
    
    async def _update_single_test(self, test: Dict, change: Dict) -> Dict:
        """Update a single test based on code change"""
        
        # Simple implementation - mark test as needing update
        test["needs_update"] = True
        test["change_reason"] = change.get("description", "Code modified")
        
        return test
    
    async def _generate_test_for_function(self, function_info: Dict, framework: str) -> Dict:
        """Generate test for a new function"""
        
        return {
            "scenario": {
                "type": "unit",
                "target": function_info.get("function", "new_function"),
                "scenario": "normal_operation"
            },
            "code": f"# TODO: Implement test for {function_info.get('function', 'new_function')}",
            "function": function_info.get("function", "new_function")
        }
    
    async def _generate_test_data(self, code_analysis: Dict) -> TestData:
        """Generate test data based on code analysis"""
        
        # Simple test data generation
        return TestData(
            examples=[
                {"input": "test", "expected": "result"},
                {"input": 123, "expected": 246}
            ],
            edge_cases=[
                {"input": None, "expected": "error"},
                {"input": "", "expected": "empty"}
            ]
        )