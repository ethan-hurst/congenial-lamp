"""
WebSocket endpoints for real-time communication
"""
from typing import Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
import asyncio
import json

from ...core.auth import get_current_user_ws
from ...services.container_service import ContainerService
from ...services.code_execution_service import CodeExecutionService
from ...services.collaboration_service import CollaborationService


router = APIRouter()

# Active WebSocket connections
connections: Dict[str, Dict[str, WebSocket]] = {
    "terminal": {},
    "collaboration": {},
    "execution": {}
}

# Service instances
container_service = ContainerService()
execution_service = CodeExecutionService(container_service)
collaboration_service = CollaborationService()


@router.websocket("/terminal/{container_id}")
async def terminal_websocket(
    websocket: WebSocket,
    container_id: str,
    user = Depends(get_current_user_ws)
):
    """WebSocket endpoint for terminal communication"""
    await websocket.accept()
    
    # Store connection
    connection_id = f"{user.id}:{container_id}"
    connections["terminal"][connection_id] = websocket
    
    # Create terminal in container
    try:
        master_fd, slave_fd = await container_service.create_terminal(container_id)
        
        # Start tasks for bidirectional communication
        read_task = asyncio.create_task(
            read_terminal_output(websocket, container_id, master_fd)
        )
        write_task = asyncio.create_task(
            handle_terminal_input(websocket, container_id, master_fd)
        )
        
        # Wait for tasks
        await asyncio.gather(read_task, write_task)
        
    except WebSocketDisconnect:
        # Cleanup on disconnect
        if connection_id in connections["terminal"]:
            del connections["terminal"][connection_id]
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "data": str(e)
        })
        await websocket.close()


async def read_terminal_output(websocket: WebSocket, container_id: str, master_fd: int):
    """Read output from terminal and send to WebSocket"""
    while True:
        try:
            output = await container_service.read_terminal_output(master_fd)
            if output:
                await websocket.send_json({
                    "type": "output",
                    "data": output
                })
            else:
                await asyncio.sleep(0.01)
        except Exception:
            break


async def handle_terminal_input(websocket: WebSocket, container_id: str, master_fd: int):
    """Handle input from WebSocket and write to terminal"""
    while True:
        try:
            message = await websocket.receive_json()
            
            if message["type"] == "input":
                await container_service.write_to_terminal(master_fd, message["data"])
            elif message["type"] == "resize":
                # Handle terminal resize
                await container_service.resize_terminal(
                    container_id,
                    message["rows"],
                    message["cols"]
                )
        except WebSocketDisconnect:
            break
        except Exception:
            break


@router.websocket("/execute/{container_id}")
async def execution_websocket(
    websocket: WebSocket,
    container_id: str,
    user = Depends(get_current_user_ws)
):
    """WebSocket endpoint for code execution with streaming output"""
    await websocket.accept()
    
    connection_id = f"{user.id}:{container_id}"
    connections["execution"][connection_id] = websocket
    
    try:
        while True:
            # Wait for execution request
            message = await websocket.receive_json()
            
            if message["type"] == "execute":
                # Extract execution parameters
                code = message["code"]
                language = message["language"]
                filename = message.get("filename")
                args = message.get("args")
                env = message.get("env")
                
                # Execute code and stream output
                async for output in execution_service.execute_code(
                    container_id, code, language, filename, args, env
                ):
                    await websocket.send_json(output)
                    
            elif message["type"] == "stop":
                # Handle execution stop
                # TODO: Implement execution cancellation
                pass
                
    except WebSocketDisconnect:
        if connection_id in connections["execution"]:
            del connections["execution"][connection_id]
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "data": str(e)
        })
        await websocket.close()


@router.websocket("/collaboration/{project_id}")
async def collaboration_websocket(
    websocket: WebSocket,
    project_id: str,
    user = Depends(get_current_user_ws)
):
    """WebSocket endpoint for real-time collaboration"""
    await websocket.accept()
    
    # Join collaboration session
    session_id = await collaboration_service.join_session(
        project_id, user.id, websocket
    )
    
    connection_id = f"{user.id}:{project_id}"
    connections["collaboration"][connection_id] = websocket
    
    try:
        # Send initial state
        await websocket.send_json({
            "type": "init",
            "data": {
                "session_id": session_id,
                "users": await collaboration_service.get_active_users(project_id)
            }
        })
        
        while True:
            message = await websocket.receive_json()
            
            # Handle different collaboration events
            if message["type"] == "cursor":
                await collaboration_service.broadcast_cursor(
                    project_id, user.id, message["data"]
                )
            elif message["type"] == "selection":
                await collaboration_service.broadcast_selection(
                    project_id, user.id, message["data"]
                )
            elif message["type"] == "edit":
                # Handle collaborative editing
                await collaboration_service.handle_edit(
                    project_id, user.id, message["data"]
                )
            elif message["type"] == "awareness":
                # Update user awareness (file being viewed, etc)
                await collaboration_service.update_awareness(
                    project_id, user.id, message["data"]
                )
                
    except WebSocketDisconnect:
        # Leave collaboration session
        await collaboration_service.leave_session(project_id, user.id)
        if connection_id in connections["collaboration"]:
            del connections["collaboration"][connection_id]
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "data": str(e)
        })
        await websocket.close()


@router.websocket("/lsp/{container_id}")
async def lsp_websocket(
    websocket: WebSocket,
    container_id: str,
    language: str,
    user = Depends(get_current_user_ws)
):
    """WebSocket endpoint for Language Server Protocol proxy"""
    await websocket.accept()
    
    try:
        while True:
            # Receive LSP request
            message = await websocket.receive_json()
            
            # Proxy to container
            result = await container_service.proxy_lsp_request(
                container_id,
                language,
                message.get("method"),
                message.get("params", {})
            )
            
            # Send response
            await websocket.send_json(result)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "jsonrpc": "2.0",
            "error": {
                "code": -32603,
                "message": str(e)
            }
        })
        await websocket.close()


@router.websocket("/debug/{container_id}")
async def debug_websocket(
    websocket: WebSocket,
    container_id: str,
    user = Depends(get_current_user_ws)
):
    """WebSocket endpoint for Debug Adapter Protocol proxy"""
    await websocket.accept()
    
    try:
        while True:
            # Receive DAP request
            message = await websocket.receive_json()
            
            # Proxy to container
            result = await container_service.proxy_dap_request(
                container_id,
                message.get("command"),
                message.get("arguments", {})
            )
            
            # Send response
            await websocket.send_json(result)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "success": False,
            "message": str(e)
        })
        await websocket.close()


# Test endpoint for WebSocket
@router.get("/test")
async def test_websocket():
    """Simple WebSocket test page"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Test</title>
    </head>
    <body>
        <h1>WebSocket Test</h1>
        <button onclick="testTerminal()">Test Terminal</button>
        <button onclick="testExecution()">Test Execution</button>
        <div id="output"></div>
        
        <script>
            function testTerminal() {
                const ws = new WebSocket("ws://localhost:8000/api/v1/ws/terminal/test-container");
                
                ws.onopen = () => {
                    console.log("Terminal connected");
                    ws.send(JSON.stringify({type: "input", data: "ls -la\\n"}));
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    document.getElementById("output").innerHTML += 
                        `<pre>${data.data}</pre>`;
                };
            }
            
            function testExecution() {
                const ws = new WebSocket("ws://localhost:8000/api/v1/ws/execute/test-container");
                
                ws.onopen = () => {
                    console.log("Execution connected");
                    ws.send(JSON.stringify({
                        type: "execute",
                        language: "python",
                        code: "print('Hello from CodeForge!')"
                    }));
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    document.getElementById("output").innerHTML += 
                        `<pre>${data.type}: ${data.data}</pre>`;
                };
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)