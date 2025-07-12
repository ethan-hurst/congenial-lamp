"""
Collaboration API endpoints for CodeForge
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json
import uuid
from datetime import datetime

from ...services.collaboration_service import (
    CollaborationService, Operation, OperationType
)
from ...auth.dependencies import get_current_user, get_user_from_websocket_token
from ...models.user import User


router = APIRouter(prefix="/collaboration", tags=["collaboration"])

# Shared collaboration service instance
collaboration_service = CollaborationService()


class JoinSessionRequest(BaseModel):
    project_id: str


class OperationRequest(BaseModel):
    type: str
    position: int
    length: int
    content: str = ""
    file_path: str
    timestamp: Optional[str] = None


class CursorUpdateRequest(BaseModel):
    file_path: str
    cursor_position: int
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None


@router.post("/sessions/join")
async def join_collaboration_session(
    request: JoinSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """Join a collaboration session for a project"""
    try:
        session = await collaboration_service.join_session(
            project_id=request.project_id,
            user_id=current_user.id,
            username=current_user.username,
            avatar_url=getattr(current_user, 'avatar_url', None)
        )
        
        return {
            "success": True,
            "project_id": session.project_id,
            "user_count": len(session.users),
            "users": {
                user_id: {
                    "username": user.username,
                    "color": user.color,
                    "current_file": user.current_file,
                    "last_seen": user.last_seen.isoformat()
                }
                for user_id, user in session.users.items()
            },
            "file_versions": session.file_versions
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to join collaboration session: {str(e)}"
        )


@router.post("/sessions/{project_id}/leave")
async def leave_collaboration_session(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Leave a collaboration session"""
    try:
        await collaboration_service.leave_session(project_id, current_user.id)
        
        return {
            "success": True,
            "message": "Left collaboration session successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to leave collaboration session: {str(e)}"
        )


@router.post("/sessions/{project_id}/operations")
async def apply_operation(
    project_id: str,
    operation_request: OperationRequest,
    current_user: User = Depends(get_current_user)
):
    """Apply a collaborative operation"""
    try:
        # Parse timestamp
        timestamp = datetime.now()
        if operation_request.timestamp:
            timestamp = datetime.fromisoformat(operation_request.timestamp.replace('Z', '+00:00'))
        
        # Create operation
        operation = Operation(
            id=str(uuid.uuid4()),
            type=OperationType(operation_request.type),
            position=operation_request.position,
            length=operation_request.length,
            content=operation_request.content,
            user_id=current_user.id,
            timestamp=timestamp,
            file_path=operation_request.file_path
        )
        
        # Apply operation with transformation
        transformed_op = await collaboration_service.apply_operation(project_id, operation)
        
        return {
            "success": True,
            "operation": {
                "id": transformed_op.id,
                "type": transformed_op.type,
                "position": transformed_op.position,
                "length": transformed_op.length,
                "content": transformed_op.content,
                "timestamp": transformed_op.timestamp.isoformat()
            }
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply operation: {str(e)}"
        )


@router.post("/sessions/{project_id}/cursor")
async def update_cursor(
    project_id: str,
    cursor_request: CursorUpdateRequest,
    current_user: User = Depends(get_current_user)
):
    """Update user cursor position"""
    try:
        await collaboration_service.update_cursor(
            project_id=project_id,
            user_id=current_user.id,
            file_path=cursor_request.file_path,
            cursor_position=cursor_request.cursor_position,
            selection_start=cursor_request.selection_start,
            selection_end=cursor_request.selection_end
        )
        
        return {
            "success": True,
            "message": "Cursor updated successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update cursor: {str(e)}"
        )


@router.get("/sessions/{project_id}/state")
async def get_session_state(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get current collaboration session state"""
    try:
        state = await collaboration_service.get_session_state(project_id)
        
        if not state:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaboration session not found"
            )
            
        return state
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get session state: {str(e)}"
        )


@router.get("/sessions/{project_id}/files/{file_path:path}/operations")
async def get_file_operations(
    project_id: str,
    file_path: str,
    since_version: int = 0,
    current_user: User = Depends(get_current_user)
):
    """Get operations for a specific file"""
    try:
        operations = await collaboration_service.get_file_operations(
            project_id, file_path, since_version
        )
        
        return {
            "file_path": file_path,
            "operations": operations,
            "total_operations": len(operations)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file operations: {str(e)}"
        )


@router.websocket("/sessions/{project_id}/ws")
async def collaboration_websocket(
    websocket: WebSocket,
    project_id: str,
    token: str
):
    """WebSocket endpoint for real-time collaboration"""
    await websocket.accept()
    
    user = None
    try:
        # Authenticate user from token
        user = await get_user_from_websocket_token(token)
        if not user:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
            
        # Join collaboration session
        session = await collaboration_service.join_session(
            project_id=project_id,
            user_id=user.id,
            username=user.username,
            avatar_url=getattr(user, 'avatar_url', None),
            websocket=websocket
        )
        
        # Send initial session state
        await websocket.send_text(json.dumps({
            "type": "session_joined",
            "session": {
                "project_id": session.project_id,
                "users": {
                    user_id: {
                        "username": u.username,
                        "color": u.color,
                        "cursor_position": u.cursor_position,
                        "current_file": u.current_file
                    }
                    for user_id, u in session.users.items()
                },
                "file_versions": session.file_versions
            }
        }))
        
        # Listen for messages
        while True:
            try:
                data = await websocket.receive_text()
                message = json.loads(data)
                
                message_type = message.get("type")
                
                if message_type == "operation":
                    # Handle collaborative operation
                    op_data = message.get("operation", {})
                    operation = Operation(
                        id=str(uuid.uuid4()),
                        type=OperationType(op_data.get("type")),
                        position=op_data.get("position", 0),
                        length=op_data.get("length", 0),
                        content=op_data.get("content", ""),
                        user_id=user.id,
                        file_path=op_data.get("file_path", "")
                    )
                    
                    await collaboration_service.apply_operation(project_id, operation)
                    
                elif message_type == "cursor_update":
                    # Handle cursor position update
                    cursor_data = message.get("cursor", {})
                    await collaboration_service.update_cursor(
                        project_id=project_id,
                        user_id=user.id,
                        file_path=cursor_data.get("file_path", ""),
                        cursor_position=cursor_data.get("position", 0),
                        selection_start=cursor_data.get("selection_start"),
                        selection_end=cursor_data.get("selection_end")
                    )
                    
                elif message_type == "ping":
                    # Respond to ping with pong
                    await websocket.send_text(json.dumps({"type": "pong"}))
                    
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": "Invalid JSON format"
                }))
            except Exception as e:
                await websocket.send_text(json.dumps({
                    "type": "error",
                    "message": f"Error processing message: {str(e)}"
                }))
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Clean up on disconnect
        if user:
            await collaboration_service.leave_session(project_id, user.id)


@router.get("/sessions/active")
async def get_active_sessions(
    current_user: User = Depends(get_current_user)
):
    """Get all active collaboration sessions for the user"""
    try:
        active_sessions = []
        
        for project_id, session in collaboration_service.sessions.items():
            if current_user.id in session.users:
                active_sessions.append({
                    "project_id": project_id,
                    "user_count": len(session.users),
                    "last_activity": session.last_activity.isoformat(),
                    "current_file": session.users[current_user.id].current_file
                })
        
        return {
            "active_sessions": active_sessions,
            "total_count": len(active_sessions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active sessions: {str(e)}"
        )


@router.delete("/sessions/{project_id}")
async def end_collaboration_session(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """End a collaboration session (admin only)"""
    try:
        # TODO: Add admin check
        session = collaboration_service.sessions.get(project_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Collaboration session not found"
            )
        
        # Remove all users from session
        user_ids = list(session.users.keys())
        for user_id in user_ids:
            await collaboration_service.leave_session(project_id, user_id)
        
        return {
            "success": True,
            "message": "Collaboration session ended successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to end collaboration session: {str(e)}"
        )


@router.get("/health")
async def collaboration_health():
    """Get collaboration service health status"""
    return {
        "status": "healthy",
        "active_sessions": len(collaboration_service.sessions),
        "total_connections": sum(
            len(connections) 
            for connections in collaboration_service.connections.values()
        ),
        "service_uptime": "running"
    }