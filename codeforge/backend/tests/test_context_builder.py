"""
Tests for Context Builder
"""
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from datetime import datetime
import os

from src.services.ai.context_builder import (
    ContextBuilder, FileContext, ProjectContext, ContextScope
)
from src.services.ai.base import CodeContext


@pytest.fixture
def mock_db():
    """Mock database session"""
    return MagicMock()


@pytest.fixture
def context_builder(mock_db):
    """Create context builder instance"""
    return ContextBuilder(mock_db)


@pytest.fixture
def sample_file_content():
    """Sample file content for testing"""
    return {
        "src/main.py": """
import flask
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/api/hello')
def hello():
    return jsonify({'message': 'Hello, World!'})

if __name__ == '__main__':
    app.run()
""",
        "src/utils.py": """
def format_date(date):
    return date.strftime('%Y-%m-%d')

def parse_json(data):
    import json
    return json.loads(data)
""",
        "tests/test_main.py": """
import pytest
from src.main import app

def test_hello():
    client = app.test_client()
    response = client.get('/api/hello')
    assert response.status_code == 200
""",
        "requirements.txt": """
flask==2.0.0
pytest==7.0.0
requests==2.26.0
"""
    }


class TestContextBuilder:
    """Test Context Builder functionality"""
    
    @pytest.mark.asyncio
    async def test_build_context_file_scope(self, context_builder, sample_file_content):
        """Test building context for specific files"""
        file_paths = ["src/main.py", "src/utils.py"]
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getsize') as mock_getsize, \
             patch('os.path.getmtime') as mock_getmtime:
            
            mock_exists.return_value = True
            mock_getsize.return_value = 100
            mock_getmtime.return_value = datetime.now().timestamp()
            
            # Configure mock_open to return different content for different files
            def mock_open_side_effect(path, *args, **kwargs):
                mock_file = MagicMock()
                mock_file.__enter__.return_value.read.return_value = sample_file_content.get(path, "")
                return mock_file
            
            mock_open.side_effect = mock_open_side_effect
            
            context = await context_builder.build_context(
                project_id="test-project",
                scope=ContextScope.FILE,
                file_paths=file_paths
            )
            
            assert context.project_id == "test-project"
            assert len(context.files) == 2
            assert context.files[0].path == "src/main.py"
            assert context.files[1].path == "src/utils.py"
            assert "flask" in context.files[0].content
    
    @pytest.mark.asyncio
    async def test_build_context_directory_scope(self, context_builder):
        """Test building context for a directory"""
        with patch('os.walk') as mock_walk, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getsize') as mock_getsize, \
             patch('os.path.getmtime') as mock_getmtime:
            
            mock_walk.return_value = [
                ("src", ["subdir"], ["main.py", "utils.py"]),
                ("src/subdir", [], ["helper.py"])
            ]
            mock_exists.return_value = True
            mock_getsize.return_value = 100
            mock_getmtime.return_value = datetime.now().timestamp()
            mock_open.return_value.__enter__.return_value.read.return_value = "test content"
            
            context = await context_builder.build_context(
                project_id="test-project",
                scope=ContextScope.DIRECTORY,
                directory_path="src"
            )
            
            assert context.project_id == "test-project"
            assert len(context.files) == 3
            file_paths = [f.path for f in context.files]
            assert "src/main.py" in file_paths
            assert "src/utils.py" in file_paths
            assert "src/subdir/helper.py" in file_paths
    
    @pytest.mark.asyncio
    async def test_extract_file_context(self, context_builder, sample_file_content):
        """Test extracting context from a single file"""
        file_path = "src/main.py"
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getsize') as mock_getsize, \
             patch('os.path.getmtime') as mock_getmtime:
            
            mock_exists.return_value = True
            mock_getsize.return_value = len(sample_file_content[file_path])
            mock_getmtime.return_value = datetime.now().timestamp()
            mock_open.return_value.__enter__.return_value.read.return_value = sample_file_content[file_path]
            
            file_context = await context_builder._extract_file_context(file_path)
            
            assert file_context.path == file_path
            assert file_context.language == "python"
            assert file_context.size == len(sample_file_content[file_path])
            assert "flask" in file_context.content
            assert len(file_context.imports) > 0
            assert "flask" in file_context.imports
    
    @pytest.mark.asyncio
    async def test_extract_project_structure(self, context_builder):
        """Test extracting project structure"""
        with patch('os.walk') as mock_walk, \
             patch('os.path.isfile') as mock_isfile:
            
            mock_walk.return_value = [
                ("/project", ["src", "tests", "docs"], ["README.md", "setup.py"]),
                ("/project/src", ["utils"], ["main.py", "config.py"]),
                ("/project/src/utils", [], ["helper.py", "validators.py"]),
                ("/project/tests", [], ["test_main.py", "test_utils.py"]),
                ("/project/docs", [], ["api.md", "guide.md"])
            ]
            
            def isfile_side_effect(path):
                return path.endswith(('.py', '.md'))
            
            mock_isfile.side_effect = isfile_side_effect
            
            project_context = await context_builder._extract_project_structure("/project")
            
            assert project_context.root_path == "/project"
            assert len(project_context.directories) == 4  # src, tests, docs, utils
            assert project_context.total_files == 10
            assert project_context.languages["python"] == 6
            assert project_context.languages["markdown"] == 4
    
    @pytest.mark.asyncio
    async def test_extract_dependencies(self, context_builder, sample_file_content):
        """Test extracting project dependencies"""
        with patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists:
            
            mock_exists.return_value = True
            mock_open.return_value.__enter__.return_value.read.return_value = sample_file_content["requirements.txt"]
            
            dependencies = await context_builder._extract_dependencies("/project")
            
            assert "flask" in dependencies
            assert dependencies["flask"] == "2.0.0"
            assert "pytest" in dependencies
            assert dependencies["pytest"] == "7.0.0"
            assert "requests" in dependencies
    
    @pytest.mark.asyncio
    async def test_extract_dependencies_no_requirements(self, context_builder):
        """Test extracting dependencies when requirements.txt doesn't exist"""
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = False
            
            dependencies = await context_builder._extract_dependencies("/project")
            
            assert dependencies == {}
    
    @pytest.mark.asyncio
    async def test_extract_test_coverage(self, context_builder):
        """Test extracting test coverage data"""
        coverage_data = {
            "overall": 85.5,
            "files": {
                "src/main.py": 90.0,
                "src/utils.py": 75.0,
                "src/config.py": 100.0
            }
        }
        
        with patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists, \
             patch('json.load') as mock_json_load:
            
            mock_exists.return_value = True
            mock_json_load.return_value = coverage_data
            
            coverage = await context_builder._extract_test_coverage("/project")
            
            assert coverage["overall"] == 85.5
            assert len(coverage["files"]) == 3
            assert coverage["files"]["src/main.py"] == 90.0
    
    @pytest.mark.asyncio
    async def test_get_language_from_extension(self, context_builder):
        """Test language detection from file extension"""
        test_cases = [
            ("main.py", "python"),
            ("app.js", "javascript"),
            ("index.ts", "typescript"),
            ("Main.java", "java"),
            ("main.go", "go"),
            ("style.css", "css"),
            ("index.html", "html"),
            ("config.yml", "yaml"),
            ("data.json", "json"),
            ("README.md", "markdown"),
            ("unknown.xyz", "text")
        ]
        
        for filename, expected_language in test_cases:
            language = context_builder._get_language_from_extension(filename)
            assert language == expected_language
    
    @pytest.mark.asyncio
    async def test_extract_imports_python(self, context_builder):
        """Test extracting imports from Python code"""
        python_code = """
import os
import sys
from datetime import datetime
from typing import List, Dict
import numpy as np
from flask import Flask, request, jsonify
from .utils import helper_function
from ..config import settings

# This is not an import
# import commented_module
"""
        
        imports = context_builder._extract_imports(python_code, "python")
        
        assert "os" in imports
        assert "sys" in imports
        assert "datetime" in imports
        assert "typing" in imports
        assert "numpy" in imports
        assert "flask" in imports
        assert "commented_module" not in imports
    
    @pytest.mark.asyncio
    async def test_extract_imports_javascript(self, context_builder):
        """Test extracting imports from JavaScript code"""
        js_code = """
import React from 'react';
import { useState, useEffect } from 'react';
import axios from 'axios';
import './styles.css';
const lodash = require('lodash');
const { readFile } = require('fs');

// import commented from 'commented';
"""
        
        imports = context_builder._extract_imports(js_code, "javascript")
        
        assert "react" in imports
        assert "axios" in imports
        assert "lodash" in imports
        assert "fs" in imports
        assert "commented" not in imports
    
    @pytest.mark.asyncio
    async def test_build_context_with_filters(self, context_builder):
        """Test building context with file filters"""
        with patch('os.walk') as mock_walk, \
             patch('builtins.open', create=True) as mock_open, \
             patch('os.path.exists') as mock_exists, \
             patch('os.path.getsize') as mock_getsize, \
             patch('os.path.getmtime') as mock_getmtime:
            
            mock_walk.return_value = [
                ("/project", ["src", "tests"], ["README.md"]),
                ("/project/src", [], ["main.py", "utils.py", "config.json"]),
                ("/project/tests", [], ["test_main.py"])
            ]
            mock_exists.return_value = True
            mock_getsize.return_value = 100
            mock_getmtime.return_value = datetime.now().timestamp()
            mock_open.return_value.__enter__.return_value.read.return_value = "test content"
            
            # Only include Python files
            filters = {"extensions": [".py"]}
            
            context = await context_builder.build_context(
                project_id="test-project",
                scope=ContextScope.PROJECT,
                filters=filters
            )
            
            # Should only include .py files
            assert len(context.files) == 3
            for file_context in context.files:
                assert file_context.path.endswith(".py")
    
    @pytest.mark.asyncio
    async def test_build_context_error_handling(self, context_builder):
        """Test error handling in context building"""
        with patch('os.walk') as mock_walk:
            mock_walk.side_effect = OSError("Permission denied")
            
            with pytest.raises(Exception) as exc_info:
                await context_builder.build_context(
                    project_id="test-project",
                    scope=ContextScope.PROJECT
                )
            
            assert "Permission denied" in str(exc_info.value)