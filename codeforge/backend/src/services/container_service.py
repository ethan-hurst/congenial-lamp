"""
Container Management Service for CodeForge
Handles Docker container lifecycle with gVisor/Firecracker security
"""
import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, List, Tuple, Any
import aiodocker
import docker
from docker.types import Mount
import pty
import termios
import struct
import fcntl

from ..config.settings import settings
from ..models.project import Project
from ..models.usage import ContainerSession
from ..services.usage_calculator import UsageCalculator


class ContainerService:
    """
    Manages secure container execution with:
    - gVisor/Firecracker isolation
    - Resource limits and monitoring
    - Hot reload support
    - Terminal multiplexing
    - LSP/DAP protocol proxying
    """
    
    def __init__(self):
        self.docker_sync = docker.from_env()
        self.docker = aiodocker.Docker()
        self.usage_calculator = UsageCalculator(self.docker_sync)
        self.containers: Dict[str, Dict] = {}
        self.terminals: Dict[str, Dict] = {}
        
    async def get_or_create_container(
        self,
        user_id: str,
        project_id: str,
        force_new: bool = False
    ) -> str:
        """Get existing container or create new one"""
        # Check for existing container
        if not force_new:
            existing = await self._find_existing_container(user_id, project_id)
            if existing:
                return existing
                
        # Create new container
        return await self.create_container(user_id, project_id)
        
    async def create_container(
        self,
        user_id: str,
        project_id: str
    ) -> str:
        """Create new secure container for project"""
        container_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        
        # TODO: Get project details from database
        # For now, use defaults
        project_config = {
            "language": "python",
            "runtime_version": "3.11",
            "cpu_limit": 2,
            "memory_limit_mb": 2048,
            "environment_variables": {}
        }
        
        # Determine image based on language
        image = self._get_image_for_language(
            project_config["language"],
            project_config["runtime_version"]
        )
        
        # Create container with security and resource limits
        container_config = {
            "image": image,
            "name": f"codeforge-{user_id}-{project_id}-{container_id[:8]}",
            "hostname": f"codeforge-{container_id[:8]}",
            "environment": {
                "USER_ID": user_id,
                "PROJECT_ID": project_id,
                "CONTAINER_ID": container_id,
                **project_config["environment_variables"]
            },
            "working_dir": "/workspace",
            "command": ["/bin/bash", "-c", "tail -f /dev/null"],  # Keep container running
            "detach": True,
            "tty": True,
            "stdin_open": True,
            "labels": {
                "codeforge.user_id": user_id,
                "codeforge.project_id": project_id,
                "codeforge.session_id": session_id
            },
            "host_config": {
                "runtime": settings.GVISOR_RUNTIME if settings.ENVIRONMENT == "production" else "runc",
                "cpu_shares": project_config["cpu_limit"] * 1024,
                "mem_limit": f"{project_config['memory_limit_mb']}m",
                "memswap_limit": f"{project_config['memory_limit_mb'] * 2}m",
                "pids_limit": 1000,
                "network_mode": settings.CONTAINER_NETWORK,
                "cap_drop": ["ALL"],
                "cap_add": ["CHOWN", "SETUID", "SETGID", "FOWNER"],
                "security_opt": ["no-new-privileges"],
                "mounts": [
                    Mount(
                        target="/workspace",
                        source=f"{settings.STORAGE_PATH}/projects/{project_id}",
                        type="bind",
                        read_only=False
                    )
                ]
            }
        }
        
        # Create container
        container = await self.docker.containers.create(**container_config)
        await container.start()
        
        # Store container info
        self.containers[container_id] = {
            "docker_id": container.id,
            "user_id": user_id,
            "project_id": project_id,
            "session_id": session_id,
            "created_at": datetime.utcnow()
        }
        
        # Start resource tracking
        await self.usage_calculator.start_tracking(
            session_id=session_id,
            container_id=container.id,
            user_id=user_id,
            project_id=project_id,
            environment_type="development"
        )
        
        # Initialize development tools in container
        await self._initialize_container(container)
        
        return container_id
        
    async def _find_existing_container(self, user_id: str, project_id: str) -> Optional[str]:
        """Find existing container for user/project"""
        # List containers with labels
        filters = {
            "label": [
                f"codeforge.user_id={user_id}",
                f"codeforge.project_id={project_id}"
            ],
            "status": "running"
        }
        
        containers = await self.docker.containers.list(filters=filters)
        
        if containers:
            # Return the first running container
            container = containers[0]
            container_info = await container.show()
            
            # Find our container ID from stored containers
            for cid, info in self.containers.items():
                if info["docker_id"] == container.id:
                    return cid
                    
            # Container exists but not in our cache, add it
            container_id = str(uuid.uuid4())
            self.containers[container_id] = {
                "docker_id": container.id,
                "user_id": user_id,
                "project_id": project_id,
                "session_id": container_info["Config"]["Labels"].get("codeforge.session_id"),
                "created_at": datetime.utcnow()
            }
            
            return container_id
            
        return None
        
    def _get_image_for_language(self, language: str, version: str) -> str:
        """Get Docker image for language/runtime"""
        # Map language to runtime versions
        version_map = {
            "python": "3.11",
            "javascript": "20",
            "typescript": "20",
            "go": "1.21"
        }
        
        # Use mapped version if no specific version provided
        if not version or version == "latest":
            version = version_map.get(language, "latest")
            
        images = {
            "python": f"codeforge/python:{version}",
            "javascript": f"codeforge/node:{version}",
            "typescript": f"codeforge/node:{version}",
            "go": f"codeforge/go:{version}",
            "rust": f"codeforge/rust:{version}",
            "java": f"codeforge/java:{version}",
            "cpp": f"codeforge/cpp:{version}",
            "ruby": f"codeforge/ruby:{version}",
            "php": f"codeforge/php:{version}"
        }
        
        # Default to Ubuntu if language not found
        return images.get(language, "codeforge/ubuntu:latest")
        
    async def _initialize_container(self, container):
        """Initialize development tools in container"""
        # Install language servers, debuggers, etc.
        init_commands = [
            # Create workspace directory if not exists
            ["/bin/mkdir", "-p", "/workspace"],
            # Set proper permissions
            ["/bin/chown", "-R", "1000:1000", "/workspace"]
        ]
        
        for cmd in init_commands:
            exec_instance = await container.exec(cmd, stdout=True, stderr=True)
            async with exec_instance.start() as stream:
                async for _ in stream:
                    pass  # Consume output
                    
    async def create_terminal(
        self,
        container_id: str,
        shell: str = "/bin/bash",
        env: Dict[str, str] = None,
        cwd: str = "/workspace"
    ) -> Tuple[int, int]:
        """Create pseudo-terminal in container"""
        if container_id not in self.containers:
            raise ValueError(f"Container {container_id} not found")
            
        # Create pseudo-terminal
        master_fd, slave_fd = pty.openpty()
        
        # Set terminal size
        winsize = struct.pack("HHHH", 24, 80, 0, 0)
        fcntl.ioctl(slave_fd, termios.TIOCSWINSZ, winsize)
        
        # Get container
        docker_id = self.containers[container_id]["docker_id"]
        container = await self.docker.containers.get(docker_id)
        
        # Create exec instance
        exec_config = {
            "Cmd": [shell],
            "AttachStdin": True,
            "AttachStdout": True,
            "AttachStderr": True,
            "Tty": True,
            "WorkingDir": cwd
        }
        
        if env:
            exec_config["Env"] = [f"{k}={v}" for k, v in env.items()]
            
        exec_instance = await container.exec(exec_config)
        
        # Store terminal info
        terminal_id = str(uuid.uuid4())
        self.terminals[terminal_id] = {
            "container_id": container_id,
            "master_fd": master_fd,
            "slave_fd": slave_fd,
            "exec_instance": exec_instance,
            "created_at": datetime.utcnow()
        }
        
        # Start exec instance
        stream = exec_instance.start(detach=False, socket=True)
        
        # Start forwarding between pty and docker exec
        asyncio.create_task(self._forward_terminal(terminal_id, stream))
        
        return master_fd, slave_fd
        
    async def _forward_terminal(self, terminal_id: str, stream):
        """Forward data between PTY and Docker exec stream"""
        terminal = self.terminals.get(terminal_id)
        if not terminal:
            return
            
        master_fd = terminal["master_fd"]
        
        # Set non-blocking mode
        flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
        fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)
        
        try:
            async with stream as docker_socket:
                while terminal_id in self.terminals:
                    # Read from PTY
                    try:
                        pty_data = os.read(master_fd, 4096)
                        if pty_data:
                            await docker_socket.send(pty_data)
                    except (OSError, IOError):
                        pass
                        
                    # Read from Docker
                    try:
                        docker_data = await asyncio.wait_for(
                            docker_socket.recv(),
                            timeout=0.1
                        )
                        if docker_data:
                            os.write(master_fd, docker_data)
                    except asyncio.TimeoutError:
                        pass
                    except Exception:
                        break
                        
                    await asyncio.sleep(0.01)
                    
        finally:
            # Cleanup
            if terminal_id in self.terminals:
                os.close(master_fd)
                os.close(terminal["slave_fd"])
                del self.terminals[terminal_id]
                
    async def write_to_terminal(self, master_fd: int, data: str):
        """Write data to terminal"""
        os.write(master_fd, data.encode('utf-8'))
        
    async def read_terminal_output(self, master_fd: int) -> Optional[str]:
        """Read output from terminal"""
        try:
            data = os.read(master_fd, 4096)
            return data.decode('utf-8', errors='replace')
        except (OSError, IOError):
            return None
            
    async def resize_terminal(self, terminal_id: str, rows: int, cols: int):
        """Resize terminal window"""
        terminal = self.terminals.get(terminal_id)
        if not terminal:
            return
            
        # Update terminal size
        winsize = struct.pack("HHHH", rows, cols, 0, 0)
        fcntl.ioctl(terminal["master_fd"], termios.TIOCSWINSZ, winsize)
        
        # Send resize signal to process
        # This would be done through Docker API
        
    async def proxy_lsp_request(
        self,
        container_id: str,
        language: str,
        method: str,
        params: Dict
    ) -> Dict:
        """Proxy Language Server Protocol request to container"""
        # This is a simplified implementation
        # In production, we'd maintain persistent LSP connections
        
        lsp_commands = {
            "python": ["pylsp"],
            "javascript": ["typescript-language-server", "--stdio"],
            "go": ["gopls"],
            "rust": ["rust-analyzer"]
        }
        
        command = lsp_commands.get(language)
        if not command:
            return {"error": f"No LSP server for {language}"}
            
        # Execute LSP request in container
        # This would involve maintaining a persistent LSP process
        # and sending/receiving JSON-RPC messages
        
        return {
            "jsonrpc": "2.0",
            "id": 1,
            "result": {
                "capabilities": {
                    "completionProvider": True,
                    "hoverProvider": True,
                    "definitionProvider": True
                }
            }
        }
        
    async def proxy_dap_request(
        self,
        container_id: str,
        command: str,
        arguments: Dict
    ) -> Dict:
        """Proxy Debug Adapter Protocol request to container"""
        # Simplified implementation
        # Would maintain persistent debug adapter connections
        
        return {
            "success": True,
            "body": {
                "supportsConfigurationDoneRequest": True,
                "supportsFunctionBreakpoints": True,
                "supportsConditionalBreakpoints": True
            }
        }
        
    async def stop_container(self, container_id: str):
        """Stop and remove container"""
        if container_id not in self.containers:
            return
            
        container_info = self.containers[container_id]
        
        # Stop usage tracking
        if "session_id" in container_info:
            await self.usage_calculator.stop_tracking(container_info["session_id"])
            
        # Stop container
        try:
            container = await self.docker.containers.get(container_info["docker_id"])
            await container.stop()
            await container.delete()
        except Exception as e:
            print(f"Error stopping container: {e}")
            
        # Cleanup
        del self.containers[container_id]
        
    async def cleanup(self):
        """Cleanup all resources"""
        # Stop all containers
        for container_id in list(self.containers.keys()):
            await self.stop_container(container_id)
            
        # Close Docker connection
        await self.docker.close()