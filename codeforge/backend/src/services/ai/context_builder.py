"""
Context Builder - Builds semantic understanding of code for AI agents
"""
import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
import logging

from sqlalchemy.orm import Session

from ...models.ai_agent import CodeContext as CodeContextModel
from ..file_service import FileService

logger = logging.getLogger(__name__)


class ContextScope:
    """Scope for context building"""
    FILE = "file"
    DIRECTORY = "directory"
    PROJECT = "project"


class CodeContext:
    """Runtime code context for agents"""
    def __init__(self, scope: str, file_paths: List[str]):
        self.scope = scope
        self.file_paths = file_paths
        self.symbols = {}
        self.dependencies = {}
        self.architecture = {}
        self.content_map = {}
        self.language_stats = {}
        self.framework_detection = {}


class SymbolExtractor:
    """Extract symbols from different programming languages"""
    
    @staticmethod
    def extract_python(content: str, file_path: str) -> Dict:
        """Extract symbols from Python code"""
        symbols = {
            "classes": [],
            "functions": [],
            "variables": [],
            "imports": []
        }
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    class_info = {
                        "name": node.name,
                        "line": node.lineno,
                        "methods": [],
                        "attributes": []
                    }
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            class_info["methods"].append({
                                "name": item.name,
                                "line": item.lineno,
                                "args": [arg.arg for arg in item.args.args]
                            })
                    
                    symbols["classes"].append(class_info)
                
                elif isinstance(node, ast.FunctionDef) and not any(
                    isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)
                    if hasattr(parent, 'body') and node in parent.body
                ):
                    symbols["functions"].append({
                        "name": node.name,
                        "line": node.lineno,
                        "args": [arg.arg for arg in node.args.args]
                    })
                
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        symbols["imports"].append({
                            "module": alias.name,
                            "alias": alias.asname,
                            "line": node.lineno
                        })
                
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        symbols["imports"].append({
                            "module": f"{module}.{alias.name}" if module else alias.name,
                            "alias": alias.asname,
                            "line": node.lineno,
                            "from": module
                        })
        
        except SyntaxError as e:
            logger.warning(f"Syntax error in {file_path}: {e}")
        except Exception as e:
            logger.error(f"Error extracting Python symbols from {file_path}: {e}")
        
        return symbols
    
    @staticmethod
    def extract_javascript(content: str, file_path: str) -> Dict:
        """Extract symbols from JavaScript/TypeScript code"""
        symbols = {
            "classes": [],
            "functions": [],
            "variables": [],
            "imports": [],
            "exports": []
        }
        
        # Simple regex-based extraction for JS/TS
        import re
        
        # Extract classes
        class_pattern = r'(?:export\s+)?(?:default\s+)?class\s+(\w+)'
        for match in re.finditer(class_pattern, content):
            symbols["classes"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })
        
        # Extract functions
        func_pattern = r'(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)'
        for match in re.finditer(func_pattern, content):
            symbols["functions"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })
        
        # Extract arrow functions
        arrow_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>'
        for match in re.finditer(arrow_pattern, content):
            symbols["functions"].append({
                "name": match.group(1),
                "line": content[:match.start()].count('\n') + 1,
                "type": "arrow"
            })
        
        # Extract imports
        import_pattern = r'import\s+(?:{[^}]+}|[\w\s,]+)\s+from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, content):
            symbols["imports"].append({
                "module": match.group(1),
                "line": content[:match.start()].count('\n') + 1
            })
        
        return symbols


class ContextBuilder:
    """
    Builds comprehensive code context for AI agents to understand the codebase
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.file_service = FileService()
        self.symbol_extractors = {
            ".py": SymbolExtractor.extract_python,
            ".js": SymbolExtractor.extract_javascript,
            ".jsx": SymbolExtractor.extract_javascript,
            ".ts": SymbolExtractor.extract_javascript,
            ".tsx": SymbolExtractor.extract_javascript
        }
        
        # Language detection patterns
        self.language_map = {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".c": "c",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php"
        }
        
        # Framework detection patterns
        self.framework_patterns = {
            "python": {
                "fastapi": ["from fastapi", "FastAPI"],
                "django": ["from django", "django.conf"],
                "flask": ["from flask", "Flask"],
                "pytest": ["import pytest", "from pytest"]
            },
            "javascript": {
                "react": ["from 'react'", "import React", "useState", "useEffect"],
                "vue": ["from 'vue'", "createApp", "Vue."],
                "express": ["express()", "app.listen"],
                "nextjs": ["from 'next'", "next/"]
            }
        }
    
    async def build_context(
        self,
        project_id: str,
        scope: ContextScope,
        file_paths: Optional[List[str]] = None,
        force_rebuild: bool = False
    ) -> CodeContext:
        """Build code context for the specified scope"""
        
        # Check if we have a cached context
        if not force_rebuild:
            cached_context = self._get_cached_context(project_id, scope)
            if cached_context:
                return cached_context
        
        # Create new context
        context = CodeContext(scope, file_paths or [])
        
        # Determine files to analyze
        files_to_analyze = await self._get_files_for_scope(project_id, scope, file_paths)
        
        # Analyze each file
        for file_path in files_to_analyze:
            await self._analyze_file(project_id, file_path, context)
        
        # Build architecture understanding
        self._analyze_architecture(context)
        
        # Detect frameworks
        self._detect_frameworks(context)
        
        # Save context to database
        self._save_context(project_id, context)
        
        return context
    
    async def update_context(
        self,
        context: CodeContext,
        changes: List[Dict],
        project_id: str
    ) -> CodeContext:
        """Update existing context with file changes"""
        
        for change in changes:
            file_path = change.get("file_path")
            change_type = change.get("type")
            
            if change_type == "modified" or change_type == "created":
                # Re-analyze the file
                await self._analyze_file(project_id, file_path, context)
            
            elif change_type == "deleted":
                # Remove file from context
                context.file_paths = [f for f in context.file_paths if f != file_path]
                context.content_map.pop(file_path, None)
                context.symbols.pop(file_path, None)
        
        # Re-analyze architecture after changes
        self._analyze_architecture(context)
        
        # Update in database
        self._save_context(project_id, context)
        
        return context
    
    async def _get_files_for_scope(
        self,
        project_id: str,
        scope: str,
        file_paths: Optional[List[str]]
    ) -> List[str]:
        """Get list of files to analyze based on scope"""
        
        if scope == ContextScope.FILE and file_paths:
            return file_paths
        
        # For directory and project scope, we need to list files
        # This is a simplified version - in production, this would interface
        # with the file service to get actual project files
        
        files = []
        
        if scope == ContextScope.DIRECTORY and file_paths and len(file_paths) > 0:
            # Get all files in the directory
            directory = os.path.dirname(file_paths[0])
            # In production, this would use file service
            # For now, return the provided files
            files = file_paths
        
        elif scope == ContextScope.PROJECT:
            # Get all project files
            # In production, this would query the file service
            # For now, return empty list
            files = []
        
        # Filter to only supported file types
        supported_extensions = set(self.language_map.keys())
        return [f for f in files if any(f.endswith(ext) for ext in supported_extensions)]
    
    async def _analyze_file(
        self,
        project_id: str,
        file_path: str,
        context: CodeContext
    ) -> None:
        """Analyze a single file and add to context"""
        
        try:
            # Get file content
            # In production, this would use the file service
            # For now, we'll simulate
            content = ""  # Would be: await self.file_service.read_file(project_id, file_path)
            
            # Store content
            context.content_map[file_path] = content
            
            # Detect language
            ext = Path(file_path).suffix.lower()
            language = self.language_map.get(ext, "unknown")
            
            # Update language stats
            if language not in context.language_stats:
                context.language_stats[language] = 0
            context.language_stats[language] += len(content.split('\n'))
            
            # Extract symbols if we have an extractor
            if ext in self.symbol_extractors:
                symbols = self.symbol_extractors[ext](content, file_path)
                context.symbols[file_path] = symbols
                
                # Extract dependencies
                if symbols.get("imports"):
                    context.dependencies[file_path] = [
                        imp["module"] for imp in symbols["imports"]
                    ]
        
        except Exception as e:
            logger.error(f"Error analyzing file {file_path}: {e}")
    
    def _analyze_architecture(self, context: CodeContext) -> None:
        """Analyze overall architecture patterns"""
        
        architecture = {
            "patterns": [],
            "structure": {},
            "entry_points": [],
            "test_files": []
        }
        
        # Analyze file structure
        directories = {}
        for file_path in context.file_paths:
            parts = file_path.split('/')
            dir_path = '/'.join(parts[:-1])
            
            if dir_path not in directories:
                directories[dir_path] = []
            directories[dir_path].append(parts[-1])
        
        architecture["structure"] = directories
        
        # Detect common patterns
        if any("models" in path or "model" in path for path in context.file_paths):
            architecture["patterns"].append("MVC/Model layer detected")
        
        if any("controllers" in path or "routes" in path or "api" in path for path in context.file_paths):
            architecture["patterns"].append("API/Controller layer detected")
        
        if any("services" in path or "service" in path for path in context.file_paths):
            architecture["patterns"].append("Service layer detected")
        
        # Identify entry points
        for file_path in context.file_paths:
            if any(name in file_path.lower() for name in ["main", "app", "index", "server"]):
                architecture["entry_points"].append(file_path)
        
        # Identify test files
        architecture["test_files"] = [
            f for f in context.file_paths 
            if "test" in f.lower() or "spec" in f.lower()
        ]
        
        context.architecture = architecture
    
    def _detect_frameworks(self, context: CodeContext) -> None:
        """Detect frameworks used in the project"""
        
        detected_frameworks = {}
        
        for file_path, content in context.content_map.items():
            ext = Path(file_path).suffix.lower()
            language = self.language_map.get(ext)
            
            if language and language in self.framework_patterns:
                for framework, patterns in self.framework_patterns[language].items():
                    if any(pattern in content for pattern in patterns):
                        if framework not in detected_frameworks:
                            detected_frameworks[framework] = []
                        detected_frameworks[framework].append(file_path)
        
        context.framework_detection = detected_frameworks
    
    def _get_cached_context(self, project_id: str, scope: str) -> Optional[CodeContext]:
        """Get cached context from database"""
        
        # Query for recent context
        context_model = self.db.query(CodeContextModel).filter(
            CodeContextModel.project_id == project_id,
            CodeContextModel.scope == scope
        ).order_by(CodeContextModel.updated_at.desc()).first()
        
        if context_model and context_model.last_indexed_at:
            # Check if context is recent enough (e.g., less than 1 hour old)
            age = datetime.utcnow() - context_model.last_indexed_at
            if age.total_seconds() < 3600:  # 1 hour
                # Reconstruct context from model
                context = CodeContext(scope, context_model.file_paths or [])
                context.symbols = context_model.symbols or {}
                context.dependencies = context_model.dependencies or {}
                context.architecture = context_model.architecture or {}
                
                return context
        
        return None
    
    def _save_context(self, project_id: str, context: CodeContext) -> None:
        """Save context to database"""
        
        # Check if context exists
        context_model = self.db.query(CodeContextModel).filter(
            CodeContextModel.project_id == project_id,
            CodeContextModel.scope == context.scope
        ).first()
        
        if not context_model:
            context_model = CodeContextModel(
                project_id=project_id,
                scope=context.scope
            )
            self.db.add(context_model)
        
        # Update context
        context_model.file_paths = context.file_paths
        context_model.symbols = context.symbols
        context_model.dependencies = context.dependencies
        context_model.architecture = context.architecture
        context_model.languages = context.language_stats
        context_model.frameworks = list(context.framework_detection.keys())
        context_model.total_files = len(context.file_paths)
        context_model.total_lines = sum(context.language_stats.values())
        context_model.last_indexed_at = datetime.utcnow()
        
        self.db.commit()
    
    def get_context_summary(self, context: CodeContext) -> Dict:
        """Get a summary of the context for agents"""
        
        return {
            "scope": context.scope,
            "total_files": len(context.file_paths),
            "languages": context.language_stats,
            "frameworks": list(context.framework_detection.keys()),
            "architecture_patterns": context.architecture.get("patterns", []),
            "entry_points": context.architecture.get("entry_points", []),
            "test_coverage": len(context.architecture.get("test_files", [])) / max(len(context.file_paths), 1)
        }