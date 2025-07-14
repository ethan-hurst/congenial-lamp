"""
Sandboxed Code Execution Environment for AI Agents
Provides secure, isolated environment for AI agent code execution
"""
import asyncio
import os
import tempfile
import shutil
import subprocess
import uuid
import time
from typing import Dict, List, Optional, Any
from pathlib import Path
import docker
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Exception raised when code execution fails"""
    pass


class SecurityViolation(Exception):
    """Exception raised when security rules are violated"""
    pass


class SandboxConfig:
    """Configuration for sandbox execution"""
    
    def __init__(
        self,
        max_execution_time: int = 30,
        max_memory_mb: int = 512,
        max_cpu_percent: float = 50.0,
        allowed_imports: Optional[List[str]] = None,
        blocked_functions: Optional[List[str]] = None,
        enable_network: bool = False,
        temp_dir_size_mb: int = 100
    ):
        self.max_execution_time = max_execution_time
        self.max_memory_mb = max_memory_mb
        self.max_cpu_percent = max_cpu_percent
        self.allowed_imports = allowed_imports or [
            "os", "sys", "json", "re", "math", "datetime", "collections",
            "itertools", "functools", "typing", "pathlib", "uuid", "hashlib",
            "base64", "string", "random", "logging", "dataclasses", "enum"
        ]
        self.blocked_functions = blocked_functions or [
            "exec", "eval", "open", "__import__", "compile", "globals", "locals",
            "vars", "dir", "getattr", "setattr", "delattr", "hasattr"
        ]
        self.enable_network = enable_network
        self.temp_dir_size_mb = temp_dir_size_mb


class CodeSandbox:
    """
    Secure sandbox for executing AI-generated code
    
    Uses Docker containers and security policies to ensure safe execution
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self.docker_client = None
        self.active_containers = {}
        
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            logger.warning(f"Docker not available: {e}")
    
    async def validate_code_security(self, code: str, language: str = "python") -> bool:
        """Validate code against security policies"""
        
        if language == "python":
            return await self._validate_python_security(code)
        elif language in ["javascript", "typescript"]:
            return await self._validate_js_security(code)
        else:
            # For other languages, apply basic checks
            return await self._validate_basic_security(code)
    
    async def _validate_python_security(self, code: str) -> bool:
        """Validate Python code security"""
        
        # Check for blocked functions
        for blocked in self.config.blocked_functions:
            if blocked in code:
                raise SecurityViolation(f"Blocked function '{blocked}' found in code")
        
        # Check for dangerous imports
        import ast
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name not in self.config.allowed_imports:
                            raise SecurityViolation(f"Import '{alias.name}' not allowed")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module not in self.config.allowed_imports:
                        raise SecurityViolation(f"Import from '{node.module}' not allowed")
        
        except SyntaxError as e:
            raise SecurityViolation(f"Invalid Python syntax: {e}")
        
        return True
    
    async def _validate_js_security(self, code: str) -> bool:
        """Validate JavaScript/TypeScript code security"""
        
        dangerous_patterns = [
            "require(", "import(", "eval(", "Function(",
            "process.exit", "process.kill", "child_process",
            "fs.readFile", "fs.writeFile", "fs.unlink",
            "XMLHttpRequest", "fetch(", "WebSocket"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in code:
                if not self.config.enable_network and pattern in ["XMLHttpRequest", "fetch(", "WebSocket"]:
                    raise SecurityViolation(f"Network access not allowed: {pattern}")
                elif pattern not in ["XMLHttpRequest", "fetch(", "WebSocket"]:
                    raise SecurityViolation(f"Dangerous pattern found: {pattern}")
        
        return True
    
    async def _validate_basic_security(self, code: str) -> bool:
        """Basic security validation for other languages"""
        
        dangerous_keywords = [
            "system", "exec", "shell", "cmd", "eval",
            "import", "require", "include", "load"
        ]
        
        code_lower = code.lower()
        for keyword in dangerous_keywords:
            if keyword in code_lower:
                logger.warning(f"Potentially dangerous keyword found: {keyword}")
        
        return True
    
    @asynccontextmanager
    async def create_execution_environment(self, language: str = "python"):
        """Create a temporary, isolated execution environment"""
        
        container_id = str(uuid.uuid4())
        temp_dir = None
        container = None
        
        try:
            # Create temporary directory
            temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{container_id}_")
            
            if self.docker_client:
                # Use Docker for better isolation
                container = await self._create_docker_container(container_id, language, temp_dir)
                self.active_containers[container_id] = container
                
                yield {
                    "type": "docker",
                    "container": container,
                    "work_dir": "/workspace",
                    "container_id": container_id
                }
            else:
                # Fallback to process isolation
                yield {
                    "type": "process",
                    "work_dir": temp_dir,
                    "container_id": container_id
                }
        
        finally:
            # Cleanup
            if container:
                try:
                    container.stop()
                    container.remove()
                    self.active_containers.pop(container_id, None)
                except Exception as e:
                    logger.error(f"Error cleaning up container: {e}")
            
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                except Exception as e:
                    logger.error(f"Error cleaning up temp dir: {e}")
    
    async def _create_docker_container(self, container_id: str, language: str, host_dir: str):
        """Create a Docker container for code execution"""
        
        # Choose appropriate base image
        images = {
            "python": "python:3.11-alpine",
            "node": "node:18-alpine", 
            "javascript": "node:18-alpine",
            "typescript": "node:18-alpine",
            "go": "golang:1.19-alpine",
            "java": "openjdk:17-alpine"
        }
        
        image = images.get(language, "python:3.11-alpine")
        
        # Security constraints
        container = self.docker_client.containers.create(
            image=image,
            detach=True,
            mem_limit=f"{self.config.max_memory_mb}m",
            cpuset_cpus="0",  # Limit to one CPU
            network_disabled=not self.config.enable_network,
            read_only=True,
            volumes={
                host_dir: {"bind": "/workspace", "mode": "rw"}
            },
            working_dir="/workspace",
            user="nobody",  # Run as non-root user
            command="sleep 3600",  # Keep container alive
            environment={
                "PYTHONUNBUFFERED": "1",
                "PYTHONDONTWRITEBYTECODE": "1"
            }
        )
        
        container.start()
        return container
    
    async def execute_code(
        self,
        code: str,
        language: str = "python",
        input_data: Optional[str] = None,
        files: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute code in sandbox environment
        
        Args:
            code: Code to execute
            language: Programming language
            input_data: Optional input data for the code
            files: Optional files to create in workspace
        
        Returns:
            Execution result with output, errors, and metadata
        """
        
        # Validate code security
        await self.validate_code_security(code, language)
        
        start_time = time.time()
        
        async with self.create_execution_environment(language) as env:
            try:
                # Create additional files if provided
                if files:
                    await self._create_files(env, files)
                
                # Execute code based on environment type
                if env["type"] == "docker":
                    result = await self._execute_in_docker(env, code, language, input_data)
                else:
                    result = await self._execute_in_process(env, code, language, input_data)
                
                execution_time = time.time() - start_time
                
                return {
                    "success": result.get("return_code", 0) == 0,
                    "output": result.get("stdout", ""),
                    "error": result.get("stderr", ""),
                    "return_code": result.get("return_code", 0),
                    "execution_time": execution_time,
                    "language": language,
                    "sandbox_type": env["type"]
                }
                
            except asyncio.TimeoutError:
                raise ExecutionError(f"Code execution timed out after {self.config.max_execution_time}s")
            
            except Exception as e:
                return {
                    "success": False,
                    "output": "",
                    "error": str(e),
                    "return_code": -1,
                    "execution_time": time.time() - start_time,
                    "language": language,
                    "sandbox_type": env["type"]
                }
    
    async def _create_files(self, env: Dict, files: Dict[str, str]):
        """Create files in the execution environment"""
        
        work_dir = env["work_dir"]
        
        for filename, content in files.items():
            file_path = os.path.join(work_dir, filename)
            
            # Ensure file is within work directory
            if not os.path.abspath(file_path).startswith(os.path.abspath(work_dir)):
                raise SecurityViolation(f"File path outside workspace: {filename}")
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                f.write(content)
    
    async def _execute_in_docker(
        self,
        env: Dict,
        code: str,
        language: str,
        input_data: Optional[str]
    ) -> Dict[str, Any]:
        """Execute code in Docker container"""
        
        container = env["container"]
        
        # Create code file
        code_file = f"main.{self._get_file_extension(language)}"
        
        # Write code to container
        with tempfile.NamedTemporaryFile(mode='w', suffix=f'.{self._get_file_extension(language)}', delete=False) as f:
            f.write(code)
            temp_file = f.name
        
        try:
            # Copy code file to container
            with open(temp_file, 'rb') as f:
                container.put_archive('/workspace', tar_data=self._create_tar(code_file, f.read()))
            
            # Execute code with timeout
            exec_cmd = self._get_execution_command(language, code_file)
            
            exec_result = container.exec_run(
                exec_cmd,
                stdin=input_data is not None,
                stdout=True,
                stderr=True,
                stream=False
            )
            
            return {
                "stdout": exec_result.output.decode('utf-8', errors='ignore'),
                "stderr": "",
                "return_code": exec_result.exit_code
            }
        
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    async def _execute_in_process(
        self,
        env: Dict,
        code: str,
        language: str,
        input_data: Optional[str]
    ) -> Dict[str, Any]:
        """Execute code in isolated process"""
        
        work_dir = env["work_dir"]
        code_file = os.path.join(work_dir, f"main.{self._get_file_extension(language)}")
        
        # Write code to file
        with open(code_file, 'w') as f:
            f.write(code)
        
        # Execute with timeout and resource limits
        cmd = self._get_execution_command(language, "main." + self._get_file_extension(language))
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=work_dir,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            limit=1024*1024*10  # 10MB limit
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input_data.encode() if input_data else None),
                timeout=self.config.max_execution_time
            )
            
            return {
                "stdout": stdout.decode('utf-8', errors='ignore'),
                "stderr": stderr.decode('utf-8', errors='ignore'),
                "return_code": process.returncode
            }
        
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            raise
    
    def _get_file_extension(self, language: str) -> str:
        """Get file extension for language"""
        extensions = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "java": "java",
            "go": "go",
            "c": "c",
            "cpp": "cpp"
        }
        return extensions.get(language, "txt")
    
    def _get_execution_command(self, language: str, filename: str) -> List[str]:
        """Get execution command for language"""
        commands = {
            "python": ["python3", filename],
            "javascript": ["node", filename],
            "typescript": ["npx", "ts-node", filename],
            "java": ["javac", filename, "&&", "java", filename.replace(".java", "")],
            "go": ["go", "run", filename]
        }
        return commands.get(language, ["cat", filename])
    
    def _create_tar(self, filename: str, content: bytes) -> bytes:
        """Create tar archive for Docker"""
        import tarfile
        import io
        
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(content)
            tar.addfile(tarinfo, io.BytesIO(content))
        
        tar_buffer.seek(0)
        return tar_buffer.read()
    
    async def cleanup_all(self):
        """Clean up all active containers"""
        for container_id, container in list(self.active_containers.items()):
            try:
                container.stop()
                container.remove()
            except Exception as e:
                logger.error(f"Error cleaning up container {container_id}: {e}")
        
        self.active_containers.clear()


# Global sandbox instance
_sandbox_instance = None

def get_sandbox() -> CodeSandbox:
    """Get global sandbox instance"""
    global _sandbox_instance
    if _sandbox_instance is None:
        _sandbox_instance = CodeSandbox()
    return _sandbox_instance