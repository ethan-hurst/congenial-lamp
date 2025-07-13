"""
Code Execution Service for CodeForge
Handles code execution within secure containers
"""
import asyncio
import json
import os
import tempfile
from typing import Dict, Optional, AsyncGenerator
from datetime import datetime

from .container_service import ContainerService


class CodeExecutionService:
    """
    Manages code execution with:
    - Language-specific runners
    - Real-time output streaming
    - Error handling
    - Resource monitoring
    """
    
    def __init__(self, container_service: ContainerService):
        self.container_service = container_service
        self.execution_handlers = {
            "python": self._execute_python,
            "javascript": self._execute_javascript,
            "typescript": self._execute_typescript,
            "go": self._execute_go,
            "bash": self._execute_bash
        }
        
    async def execute_code(
        self,
        container_id: str,
        code: str,
        language: str,
        filename: Optional[str] = None,
        args: Optional[list] = None,
        env: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Execute code in container with streaming output
        
        Yields dictionaries with:
        - type: 'stdout', 'stderr', 'exit'
        - data: output text or exit code
        - timestamp: when the event occurred
        """
        if language not in self.execution_handlers:
            yield {
                "type": "stderr",
                "data": f"Unsupported language: {language}",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield {
                "type": "exit",
                "data": 1,
                "timestamp": datetime.utcnow().isoformat()
            }
            return
            
        # Get execution handler for language
        handler = self.execution_handlers[language]
        
        # Execute code
        async for output in handler(container_id, code, filename, args, env):
            yield output
            
    async def _execute_python(
        self,
        container_id: str,
        code: str,
        filename: Optional[str] = None,
        args: Optional[list] = None,
        env: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Execute Python code"""
        # Create temporary file with code
        if filename:
            file_path = f"/workspace/{filename}"
            command = ["python", file_path]
        else:
            # Use python -c for inline code
            command = ["python", "-c", code]
            
        if args:
            command.extend(args)
            
        # Execute in container
        async for output in self._execute_command(container_id, command, env):
            yield output
            
    async def _execute_javascript(
        self,
        container_id: str,
        code: str,
        filename: Optional[str] = None,
        args: Optional[list] = None,
        env: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Execute JavaScript code"""
        if filename:
            file_path = f"/workspace/{filename}"
            command = ["node", file_path]
        else:
            # Use node -e for inline code
            command = ["node", "-e", code]
            
        if args:
            command.extend(args)
            
        async for output in self._execute_command(container_id, command, env):
            yield output
            
    async def _execute_typescript(
        self,
        container_id: str,
        code: str,
        filename: Optional[str] = None,
        args: Optional[list] = None,
        env: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Execute TypeScript code"""
        if filename:
            file_path = f"/workspace/{filename}"
            command = ["ts-node", file_path]
        else:
            # Use ts-node with eval flag
            command = ["ts-node", "-e", code]
            
        if args:
            command.extend(args)
            
        async for output in self._execute_command(container_id, command, env):
            yield output
            
    async def _execute_go(
        self,
        container_id: str,
        code: str,
        filename: Optional[str] = None,
        args: Optional[list] = None,
        env: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Execute Go code"""
        if filename:
            file_path = f"/workspace/{filename}"
            # Compile and run
            compile_cmd = ["go", "build", "-o", "/tmp/main", file_path]
            async for output in self._execute_command(container_id, compile_cmd, env):
                if output["type"] == "exit" and output["data"] != 0:
                    yield output
                    return
                    
            # Run compiled binary
            run_cmd = ["/tmp/main"]
            if args:
                run_cmd.extend(args)
            async for output in self._execute_command(container_id, run_cmd, env):
                yield output
        else:
            # Use go run with temporary file
            temp_file = "/tmp/main.go"
            write_cmd = ["sh", "-c", f"cat > {temp_file} << 'EOF'\n{code}\nEOF"]
            async for output in self._execute_command(container_id, write_cmd, env):
                if output["type"] == "exit" and output["data"] != 0:
                    yield output
                    return
                    
            run_cmd = ["go", "run", temp_file]
            if args:
                run_cmd.extend(args)
            async for output in self._execute_command(container_id, run_cmd, env):
                yield output
                
    async def _execute_bash(
        self,
        container_id: str,
        code: str,
        filename: Optional[str] = None,
        args: Optional[list] = None,
        env: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Execute Bash script"""
        if filename:
            file_path = f"/workspace/{filename}"
            command = ["bash", file_path]
        else:
            # Use bash -c for inline code
            command = ["bash", "-c", code]
            
        if args:
            command.extend(args)
            
        async for output in self._execute_command(container_id, command, env):
            yield output
            
    async def _execute_command(
        self,
        container_id: str,
        command: list,
        env: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict, None]:
        """Execute command in container with streaming output"""
        if container_id not in self.container_service.containers:
            yield {
                "type": "stderr",
                "data": f"Container {container_id} not found",
                "timestamp": datetime.utcnow().isoformat()
            }
            yield {
                "type": "exit",
                "data": 1,
                "timestamp": datetime.utcnow().isoformat()
            }
            return
            
        # Get container
        docker_id = self.container_service.containers[container_id]["docker_id"]
        container = await self.container_service.docker.containers.get(docker_id)
        
        # Create exec instance
        exec_config = {
            "Cmd": command,
            "AttachStdout": True,
            "AttachStderr": True,
            "Tty": False,
            "WorkingDir": "/workspace"
        }
        
        if env:
            exec_config["Env"] = [f"{k}={v}" for k, v in env.items()]
            
        exec_instance = await container.exec(exec_config)
        
        # Start execution and stream output
        async with exec_instance.start(detach=False) as stream:
            async for chunk in stream:
                # Docker multiplexes stdout/stderr
                # First byte indicates stream type: 1=stdout, 2=stderr
                if chunk:
                    stream_type = chunk[0]
                    # Skip header (8 bytes)
                    data = chunk[8:].decode('utf-8', errors='replace')
                    
                    if stream_type == 1:
                        yield {
                            "type": "stdout",
                            "data": data,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    elif stream_type == 2:
                        yield {
                            "type": "stderr",
                            "data": data,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        
        # Get exit code
        inspect_result = await exec_instance.inspect()
        exit_code = inspect_result.get("ExitCode", 0)
        
        yield {
            "type": "exit",
            "data": exit_code,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    async def run_tests(
        self,
        container_id: str,
        test_framework: str,
        test_path: Optional[str] = None,
        pattern: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
        """Run tests in container"""
        commands = {
            "pytest": ["pytest", "-v"],
            "jest": ["npm", "test"],
            "go-test": ["go", "test", "-v"],
            "mocha": ["mocha"],
            "unittest": ["python", "-m", "unittest", "discover"]
        }
        
        if test_framework not in commands:
            yield {
                "type": "stderr",
                "data": f"Unsupported test framework: {test_framework}",
                "timestamp": datetime.utcnow().isoformat()
            }
            return
            
        command = commands[test_framework].copy()
        
        if test_path:
            command.append(test_path)
        if pattern and test_framework == "pytest":
            command.extend(["-k", pattern])
            
        async for output in self._execute_command(container_id, command):
            yield output
            
    async def install_dependencies(
        self,
        container_id: str,
        language: str,
        dependencies: list
    ) -> AsyncGenerator[Dict, None]:
        """Install dependencies in container"""
        install_commands = {
            "python": ["pip", "install"],
            "javascript": ["npm", "install"],
            "go": ["go", "get"]
        }
        
        if language not in install_commands:
            yield {
                "type": "stderr",
                "data": f"Unsupported language: {language}",
                "timestamp": datetime.utcnow().isoformat()
            }
            return
            
        command = install_commands[language].copy()
        command.extend(dependencies)
        
        async for output in self._execute_command(container_id, command):
            yield output