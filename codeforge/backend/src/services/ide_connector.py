"""
CodeForge Universal IDE Connector Service
Enables ANY IDE to connect to cloud backend via extensions/plugins
"""
import asyncio
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any, Callable
from dataclasses import dataclass, asdict
import websockets
from websockets.server import WebSocketServerProtocol
import jwt
from pathlib import Path

from ..config.settings import settings
from ..models.user import User
from ..models.project import Project
from ..services.container_service import ContainerService
from ..services.file_sync_service import FileSyncService


@dataclass
class IDEConnection:
    """Represents an active IDE connection"""
    connection_id: str
    user_id: str
    project_id: str
    ide_type: str  # vscode, jetbrains, vim, emacs, sublime, etc.
    ide_version: str
    extension_version: str
    capabilities: List[str]  # file_sync, terminal, debug, ai_assist, etc.
    websocket: WebSocketServerProtocol
    container_id: Optional[str] = None
    connected_at: datetime = None
    last_heartbeat: datetime = None
    
    def __post_init__(self):
        if self.connected_at is None:
            self.connected_at = datetime.utcnow()
        if self.last_heartbeat is None:
            self.last_heartbeat = datetime.utcnow()
            
    def to_dict(self) -> Dict:
        """Convert to dictionary, excluding websocket"""
        data = asdict(self)
        data.pop('websocket', None)
        data['connected_at'] = self.connected_at.isoformat()
        data['last_heartbeat'] = self.last_heartbeat.isoformat()
        return data


class IDEConnectorService:
    """
    Universal IDE backend service that provides:
    - WebSocket connection for any IDE
    - File synchronization
    - Terminal access
    - Language Server Protocol proxy
    - Debug Adapter Protocol proxy
    - AI assistance integration
    - Real-time collaboration
    """
    
    def __init__(self):
        self.connections: Dict[str, IDEConnection] = {}
        self.container_service = ContainerService()
        self.file_sync_service = FileSyncService()
        self.message_handlers: Dict[str, Callable] = {
            "auth": self._handle_auth,
            "file_read": self._handle_file_read,
            "file_write": self._handle_file_write,
            "file_watch": self._handle_file_watch,
            "terminal_create": self._handle_terminal_create,
            "terminal_data": self._handle_terminal_data,
            "lsp_request": self._handle_lsp_request,
            "dap_request": self._handle_dap_request,
            "ai_request": self._handle_ai_request,
            "sync_request": self._handle_sync_request,
            "heartbeat": self._handle_heartbeat,
        }
        self.heartbeat_interval = 30  # seconds
        self.heartbeat_timeout = 90  # seconds
        
    async def start_server(self, host: str = "0.0.0.0", port: int = 8765):
        """Start the WebSocket server for IDE connections"""
        print(f"Starting IDE Connector on {host}:{port}")
        
        # Start heartbeat monitor
        asyncio.create_task(self._monitor_heartbeats())
        
        # Start WebSocket server
        async with websockets.serve(
            self.handle_connection,
            host,
            port,
            ping_interval=20,
            ping_timeout=10
        ):
            await asyncio.Future()  # run forever
            
    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new IDE connection"""
        connection_id = str(uuid.uuid4())
        connection = None
        
        try:
            # Wait for authentication
            auth_message = await asyncio.wait_for(
                websocket.recv(),
                timeout=10.0
            )
            
            auth_data = json.loads(auth_message)
            if auth_data.get("type") != "auth":
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "First message must be authentication"
                }))
                return
                
            # Validate authentication
            user_id = await self._validate_token(auth_data.get("token"))
            if not user_id:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": "Invalid authentication token"
                }))
                return
                
            # Create connection
            connection = IDEConnection(
                connection_id=connection_id,
                user_id=user_id,
                project_id=auth_data.get("project_id"),
                ide_type=auth_data.get("ide_type", "unknown"),
                ide_version=auth_data.get("ide_version", "unknown"),
                extension_version=auth_data.get("extension_version", "unknown"),
                capabilities=auth_data.get("capabilities", []),
                websocket=websocket
            )
            
            self.connections[connection_id] = connection
            
            # Send success response
            await websocket.send(json.dumps({
                "type": "auth_success",
                "connection_id": connection_id,
                "server_capabilities": [
                    "file_sync",
                    "terminal",
                    "lsp_proxy",
                    "dap_proxy",
                    "ai_assist",
                    "real_time_collab",
                    "container_exec",
                    "hot_reload"
                ]
            }))
            
            # Initialize container if needed
            if connection.project_id:
                container_id = await self.container_service.get_or_create_container(
                    user_id=user_id,
                    project_id=connection.project_id
                )
                connection.container_id = container_id
                
            # Handle messages
            async for message in websocket:
                await self._handle_message(connection, message)
                
        except websockets.exceptions.ConnectionClosed:
            print(f"IDE connection {connection_id} closed")
        except asyncio.TimeoutError:
            print(f"IDE connection {connection_id} timed out during auth")
        except Exception as e:
            print(f"Error in IDE connection {connection_id}: {e}")
            if connection:
                await websocket.send(json.dumps({
                    "type": "error",
                    "message": str(e)
                }))
        finally:
            # Cleanup connection
            if connection_id in self.connections:
                del self.connections[connection_id]
                
    async def _handle_message(self, connection: IDEConnection, message: str):
        """Route message to appropriate handler"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type in self.message_handlers:
                response = await self.message_handlers[message_type](connection, data)
                if response:
                    await connection.websocket.send(json.dumps(response))
            else:
                await connection.websocket.send(json.dumps({
                    "type": "error",
                    "message": f"Unknown message type: {message_type}"
                }))
                
        except json.JSONDecodeError:
            await connection.websocket.send(json.dumps({
                "type": "error",
                "message": "Invalid JSON message"
            }))
        except Exception as e:
            await connection.websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))
            
    async def _validate_token(self, token: str) -> Optional[str]:
        """Validate JWT token and return user ID"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload.get("sub")  # user_id
        except jwt.InvalidTokenError:
            return None
            
    async def _handle_auth(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle authentication message (already processed in handle_connection)"""
        return {"type": "auth_already_completed"}
        
    async def _handle_file_read(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle file read request"""
        file_path = data.get("path")
        if not file_path:
            return {"type": "error", "message": "Missing file path"}
            
        try:
            content = await self.file_sync_service.read_file(
                container_id=connection.container_id,
                file_path=file_path
            )
            
            return {
                "type": "file_content",
                "path": file_path,
                "content": content,
                "encoding": "utf-8"
            }
        except FileNotFoundError:
            return {
                "type": "error",
                "message": f"File not found: {file_path}"
            }
            
    async def _handle_file_write(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle file write request"""
        file_path = data.get("path")
        content = data.get("content")
        
        if not file_path or content is None:
            return {"type": "error", "message": "Missing file path or content"}
            
        try:
            await self.file_sync_service.write_file(
                container_id=connection.container_id,
                file_path=file_path,
                content=content
            )
            
            # Notify other connected IDEs about the change
            await self._broadcast_file_change(
                connection.project_id,
                file_path,
                exclude_connection=connection.connection_id
            )
            
            return {
                "type": "file_written",
                "path": file_path,
                "success": True
            }
        except Exception as e:
            return {
                "type": "error",
                "message": f"Failed to write file: {str(e)}"
            }
            
    async def _handle_file_watch(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle file watch request"""
        patterns = data.get("patterns", ["**/*"])
        
        # Register file watcher
        watcher_id = await self.file_sync_service.add_watcher(
            container_id=connection.container_id,
            patterns=patterns,
            callback=lambda event: self._notify_file_event(connection, event)
        )
        
        return {
            "type": "watch_registered",
            "watcher_id": watcher_id,
            "patterns": patterns
        }
        
    async def _handle_terminal_create(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle terminal creation request"""
        terminal_id = str(uuid.uuid4())
        
        # Create terminal in container
        pty_master, pty_slave = await self.container_service.create_terminal(
            container_id=connection.container_id,
            shell=data.get("shell", "/bin/bash"),
            env=data.get("env", {}),
            cwd=data.get("cwd", "/workspace")
        )
        
        # Store terminal info
        connection.terminals = getattr(connection, 'terminals', {})
        connection.terminals[terminal_id] = {
            "pty_master": pty_master,
            "pty_slave": pty_slave,
            "created_at": datetime.utcnow()
        }
        
        # Start terminal output reader
        asyncio.create_task(
            self._read_terminal_output(connection, terminal_id, pty_master)
        )
        
        return {
            "type": "terminal_created",
            "terminal_id": terminal_id,
            "rows": data.get("rows", 24),
            "cols": data.get("cols", 80)
        }
        
    async def _handle_terminal_data(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle terminal input data"""
        terminal_id = data.get("terminal_id")
        input_data = data.get("data")
        
        if not terminal_id or input_data is None:
            return {"type": "error", "message": "Missing terminal_id or data"}
            
        terminals = getattr(connection, 'terminals', {})
        terminal = terminals.get(terminal_id)
        
        if not terminal:
            return {"type": "error", "message": "Terminal not found"}
            
        # Write to terminal
        await self.container_service.write_to_terminal(
            terminal["pty_master"],
            input_data
        )
        
        return {"type": "terminal_data_written", "terminal_id": terminal_id}
        
    async def _handle_lsp_request(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle Language Server Protocol request"""
        # Proxy LSP request to appropriate language server in container
        lsp_method = data.get("method")
        lsp_params = data.get("params", {})
        
        response = await self.container_service.proxy_lsp_request(
            container_id=connection.container_id,
            language=data.get("language", "python"),
            method=lsp_method,
            params=lsp_params
        )
        
        return {
            "type": "lsp_response",
            "id": data.get("id"),
            "result": response
        }
        
    async def _handle_dap_request(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle Debug Adapter Protocol request"""
        # Proxy DAP request to debug adapter in container
        dap_command = data.get("command")
        dap_arguments = data.get("arguments", {})
        
        response = await self.container_service.proxy_dap_request(
            container_id=connection.container_id,
            command=dap_command,
            arguments=dap_arguments
        )
        
        return {
            "type": "dap_response",
            "request_seq": data.get("seq"),
            "success": True,
            "body": response
        }
        
    async def _handle_ai_request(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle AI assistance request"""
        ai_action = data.get("action")  # complete, explain, fix, refactor, etc.
        context = data.get("context", {})
        
        # Route to appropriate AI service
        if ai_action == "complete":
            result = await self._handle_code_completion(connection, context)
        elif ai_action == "explain":
            result = await self._handle_code_explanation(connection, context)
        elif ai_action == "fix":
            result = await self._handle_code_fix(connection, context)
        elif ai_action == "refactor":
            result = await self._handle_code_refactor(connection, context)
        else:
            return {"type": "error", "message": f"Unknown AI action: {ai_action}"}
            
        return {
            "type": "ai_response",
            "action": ai_action,
            "result": result
        }
        
    async def _handle_sync_request(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle file synchronization request"""
        sync_type = data.get("sync_type", "full")  # full, incremental, diff
        
        if sync_type == "full":
            # Get all files from container
            files = await self.file_sync_service.get_all_files(
                container_id=connection.container_id
            )
            
            return {
                "type": "sync_response",
                "sync_type": "full",
                "files": files
            }
        elif sync_type == "incremental":
            # Get files changed since timestamp
            since = datetime.fromisoformat(data.get("since"))
            files = await self.file_sync_service.get_changed_files(
                container_id=connection.container_id,
                since=since
            )
            
            return {
                "type": "sync_response",
                "sync_type": "incremental",
                "files": files,
                "timestamp": datetime.utcnow().isoformat()
            }
            
    async def _handle_heartbeat(self, connection: IDEConnection, data: Dict) -> Dict:
        """Handle heartbeat to keep connection alive"""
        connection.last_heartbeat = datetime.utcnow()
        
        return {
            "type": "heartbeat_ack",
            "timestamp": connection.last_heartbeat.isoformat()
        }
        
    async def _monitor_heartbeats(self):
        """Monitor connections and close stale ones"""
        while True:
            try:
                now = datetime.utcnow()
                stale_connections = []
                
                for conn_id, connection in self.connections.items():
                    time_since_heartbeat = (now - connection.last_heartbeat).total_seconds()
                    
                    if time_since_heartbeat > self.heartbeat_timeout:
                        stale_connections.append(conn_id)
                        
                # Close stale connections
                for conn_id in stale_connections:
                    connection = self.connections.get(conn_id)
                    if connection:
                        await connection.websocket.close()
                        del self.connections[conn_id]
                        print(f"Closed stale connection: {conn_id}")
                        
                await asyncio.sleep(self.heartbeat_interval)
                
            except Exception as e:
                print(f"Error in heartbeat monitor: {e}")
                await asyncio.sleep(self.heartbeat_interval)
                
    async def _broadcast_file_change(
        self,
        project_id: str,
        file_path: str,
        exclude_connection: Optional[str] = None
    ):
        """Broadcast file change to all connected IDEs for the project"""
        for conn_id, connection in self.connections.items():
            if connection.project_id == project_id and conn_id != exclude_connection:
                try:
                    await connection.websocket.send(json.dumps({
                        "type": "file_changed",
                        "path": file_path,
                        "timestamp": datetime.utcnow().isoformat()
                    }))
                except Exception as e:
                    print(f"Failed to notify connection {conn_id}: {e}")
                    
    async def _notify_file_event(self, connection: IDEConnection, event: Dict):
        """Notify IDE about file system event"""
        try:
            await connection.websocket.send(json.dumps({
                "type": "file_event",
                "event": event
            }))
        except Exception as e:
            print(f"Failed to send file event: {e}")
            
    async def _read_terminal_output(
        self,
        connection: IDEConnection,
        terminal_id: str,
        pty_master: int
    ):
        """Read terminal output and send to IDE"""
        try:
            while terminal_id in getattr(connection, 'terminals', {}):
                output = await self.container_service.read_terminal_output(pty_master)
                if output:
                    await connection.websocket.send(json.dumps({
                        "type": "terminal_output",
                        "terminal_id": terminal_id,
                        "data": output
                    }))
                await asyncio.sleep(0.01)  # Small delay to prevent CPU spinning
        except Exception as e:
            print(f"Error reading terminal output: {e}")
            
    # AI assistance methods (simplified implementations)
    async def _handle_code_completion(self, connection: IDEConnection, context: Dict) -> Dict:
        """Handle code completion request"""
        # This would integrate with AI service
        return {
            "completions": [
                {
                    "text": "# AI-generated completion",
                    "detail": "Generated by CodeForge AI",
                    "score": 0.95
                }
            ]
        }
        
    async def _handle_code_explanation(self, connection: IDEConnection, context: Dict) -> Dict:
        """Handle code explanation request"""
        return {
            "explanation": "This code implements a WebSocket server for IDE connections..."
        }
        
    async def _handle_code_fix(self, connection: IDEConnection, context: Dict) -> Dict:
        """Handle code fix request"""
        return {
            "fixes": [
                {
                    "description": "Add error handling",
                    "edits": []
                }
            ]
        }
        
    async def _handle_code_refactor(self, connection: IDEConnection, context: Dict) -> Dict:
        """Handle code refactoring request"""
        return {
            "refactorings": [
                {
                    "description": "Extract method",
                    "edits": []
                }
            ]
        }