"""
Real-time Collaboration Service
Enables multiple users to collaborate on projects with operational transforms
"""
import asyncio
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol
import redis
from collections import defaultdict

from ..config.settings import settings


class OperationType(str, Enum):
    """Types of collaborative operations"""
    INSERT = "insert"
    DELETE = "delete"
    RETAIN = "retain"
    CURSOR_MOVE = "cursor_move"
    SELECTION_CHANGE = "selection_change"
    FILE_OPEN = "file_open"
    FILE_CLOSE = "file_close"
    USER_JOIN = "user_join"
    USER_LEAVE = "user_leave"


@dataclass
class Operation:
    """Single collaborative operation"""
    id: str
    type: OperationType
    position: int
    length: int
    content: str = ""
    user_id: str = ""
    timestamp: datetime = None
    file_path: str = ""
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)


@dataclass
class UserPresence:
    """User presence information"""
    user_id: str
    username: str
    avatar_url: Optional[str]
    cursor_position: int = 0
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    current_file: Optional[str] = None
    color: str = "#007acc"
    last_seen: datetime = None
    
    def __post_init__(self):
        if self.last_seen is None:
            self.last_seen = datetime.now(timezone.utc)


@dataclass
class CollaborationSession:
    """Collaboration session for a project"""
    project_id: str
    users: Dict[str, UserPresence]
    operations: List[Operation]
    file_versions: Dict[str, int]  # file_path -> version
    created_at: datetime
    last_activity: datetime
    
    def __post_init__(self):
        if not hasattr(self, 'users'):
            self.users = {}
        if not hasattr(self, 'operations'):
            self.operations = []
        if not hasattr(self, 'file_versions'):
            self.file_versions = {}


class OperationalTransform:
    """
    Operational Transform implementation for conflict resolution
    Based on the Jupiter algorithm for real-time collaborative editing
    """
    
    @staticmethod
    def transform_operation(op1: Operation, op2: Operation) -> tuple[Operation, Operation]:
        """
        Transform two concurrent operations against each other
        Returns transformed versions of both operations
        """
        # If operations are on different files, no transformation needed
        if op1.file_path != op2.file_path:
            return op1, op2
            
        # Transform based on operation types
        if op1.type == OperationType.INSERT and op2.type == OperationType.INSERT:
            return OperationalTransform._transform_insert_insert(op1, op2)
        elif op1.type == OperationType.INSERT and op2.type == OperationType.DELETE:
            return OperationalTransform._transform_insert_delete(op1, op2)
        elif op1.type == OperationType.DELETE and op2.type == OperationType.INSERT:
            op2_prime, op1_prime = OperationalTransform._transform_insert_delete(op2, op1)
            return op1_prime, op2_prime
        elif op1.type == OperationType.DELETE and op2.type == OperationType.DELETE:
            return OperationalTransform._transform_delete_delete(op1, op2)
        else:
            # For other operation types, return as-is
            return op1, op2
    
    @staticmethod
    def _transform_insert_insert(op1: Operation, op2: Operation) -> tuple[Operation, Operation]:
        """Transform two concurrent insert operations"""
        if op1.position <= op2.position:
            # op1 is before op2, op2 position needs to be adjusted
            op2_prime = Operation(
                id=op2.id,
                type=op2.type,
                position=op2.position + len(op1.content),
                length=op2.length,
                content=op2.content,
                user_id=op2.user_id,
                timestamp=op2.timestamp,
                file_path=op2.file_path
            )
            return op1, op2_prime
        else:
            # op2 is before op1, op1 position needs to be adjusted
            op1_prime = Operation(
                id=op1.id,
                type=op1.type,
                position=op1.position + len(op2.content),
                length=op1.length,
                content=op1.content,
                user_id=op1.user_id,
                timestamp=op1.timestamp,
                file_path=op1.file_path
            )
            return op1_prime, op2
    
    @staticmethod
    def _transform_insert_delete(insert_op: Operation, delete_op: Operation) -> tuple[Operation, Operation]:
        """Transform insert and delete operations"""
        if insert_op.position <= delete_op.position:
            # Insert is before delete, adjust delete position
            delete_prime = Operation(
                id=delete_op.id,
                type=delete_op.type,
                position=delete_op.position + len(insert_op.content),
                length=delete_op.length,
                content=delete_op.content,
                user_id=delete_op.user_id,
                timestamp=delete_op.timestamp,
                file_path=delete_op.file_path
            )
            return insert_op, delete_prime
        elif insert_op.position >= delete_op.position + delete_op.length:
            # Insert is after delete, adjust insert position
            insert_prime = Operation(
                id=insert_op.id,
                type=insert_op.type,
                position=insert_op.position - delete_op.length,
                length=insert_op.length,
                content=insert_op.content,
                user_id=insert_op.user_id,
                timestamp=insert_op.timestamp,
                file_path=insert_op.file_path
            )
            return insert_prime, delete_op
        else:
            # Insert is within delete range, complex case
            # Adjust delete to account for insertion
            delete_prime = Operation(
                id=delete_op.id,
                type=delete_op.type,
                position=delete_op.position,
                length=delete_op.length + len(insert_op.content),
                content=delete_op.content,
                user_id=delete_op.user_id,
                timestamp=delete_op.timestamp,
                file_path=delete_op.file_path
            )
            return insert_op, delete_prime
    
    @staticmethod
    def _transform_delete_delete(op1: Operation, op2: Operation) -> tuple[Operation, Operation]:
        """Transform two concurrent delete operations"""
        if op1.position + op1.length <= op2.position:
            # op1 is completely before op2
            op2_prime = Operation(
                id=op2.id,
                type=op2.type,
                position=op2.position - op1.length,
                length=op2.length,
                content=op2.content,
                user_id=op2.user_id,
                timestamp=op2.timestamp,
                file_path=op2.file_path
            )
            return op1, op2_prime
        elif op2.position + op2.length <= op1.position:
            # op2 is completely before op1
            op1_prime = Operation(
                id=op1.id,
                type=op1.type,
                position=op1.position - op2.length,
                length=op1.length,
                content=op1.content,
                user_id=op1.user_id,
                timestamp=op1.timestamp,
                file_path=op1.file_path
            )
            return op1_prime, op2
        else:
            # Overlapping deletes - complex conflict resolution
            # For simplicity, give precedence to the earlier operation
            if op1.timestamp <= op2.timestamp:
                # op1 wins, adjust op2
                op2_prime = Operation(
                    id=op2.id,
                    type=op2.type,
                    position=op1.position,
                    length=max(0, op2.length - op1.length),
                    content=op2.content,
                    user_id=op2.user_id,
                    timestamp=op2.timestamp,
                    file_path=op2.file_path
                )
                return op1, op2_prime
            else:
                # op2 wins, adjust op1
                op1_prime = Operation(
                    id=op1.id,
                    type=op1.type,
                    position=op2.position,
                    length=max(0, op1.length - op2.length),
                    content=op1.content,
                    user_id=op1.user_id,
                    timestamp=op1.timestamp,
                    file_path=op1.file_path
                )
                return op1_prime, op2


class CollaborationService:
    """
    Real-time collaboration service with operational transforms
    """
    
    def __init__(self):
        self.redis_client = None
        if settings.REDIS_URL:
            self.redis_client = redis.from_url(settings.REDIS_URL)
            
        # In-memory storage for development
        self.sessions: Dict[str, CollaborationSession] = {}
        self.connections: Dict[str, Dict[str, WebSocketServerProtocol]] = defaultdict(dict)
        self.user_colors = [
            "#007acc", "#ff6b6b", "#4ecdc4", "#45b7d1", "#96ceb4",
            "#feca57", "#ff9ff3", "#54a0ff", "#5f27cd", "#00d2d3"
        ]
        self.color_index = 0
        
    async def create_session(self, project_id: str) -> CollaborationSession:
        """Create a new collaboration session"""
        session = CollaborationSession(
            project_id=project_id,
            users={},
            operations=[],
            file_versions={},
            created_at=datetime.now(timezone.utc),
            last_activity=datetime.now(timezone.utc)
        )
        
        self.sessions[project_id] = session
        
        # Store in Redis if available
        if self.redis_client:
            await self._store_session_redis(session)
            
        return session
    
    async def join_session(
        self, 
        project_id: str, 
        user_id: str, 
        username: str,
        avatar_url: Optional[str] = None,
        websocket: Optional[WebSocketServerProtocol] = None
    ) -> CollaborationSession:
        """User joins a collaboration session"""
        # Get or create session
        session = self.sessions.get(project_id)
        if not session:
            session = await self.create_session(project_id)
            
        # Assign user color
        color = self.user_colors[self.color_index % len(self.user_colors)]
        self.color_index += 1
        
        # Add user to session
        user_presence = UserPresence(
            user_id=user_id,
            username=username,
            avatar_url=avatar_url,
            color=color,
            last_seen=datetime.now(timezone.utc)
        )
        
        session.users[user_id] = user_presence
        session.last_activity = datetime.now(timezone.utc)
        
        # Store websocket connection
        if websocket:
            self.connections[project_id][user_id] = websocket
            
        # Broadcast user join event
        await self._broadcast_operation(project_id, Operation(
            id=str(uuid.uuid4()),
            type=OperationType.USER_JOIN,
            position=0,
            length=0,
            user_id=user_id,
            file_path=""
        ), exclude_user=user_id)
        
        # Update in Redis
        if self.redis_client:
            await self._store_session_redis(session)
            
        return session
    
    async def leave_session(self, project_id: str, user_id: str) -> None:
        """User leaves a collaboration session"""
        session = self.sessions.get(project_id)
        if not session:
            return
            
        # Remove user from session
        if user_id in session.users:
            del session.users[user_id]
            
        # Remove websocket connection
        if project_id in self.connections and user_id in self.connections[project_id]:
            del self.connections[project_id][user_id]
            
        # Broadcast user leave event
        await self._broadcast_operation(project_id, Operation(
            id=str(uuid.uuid4()),
            type=OperationType.USER_LEAVE,
            position=0,
            length=0,
            user_id=user_id,
            file_path=""
        ))
        
        # Clean up empty sessions
        if not session.users:
            del self.sessions[project_id]
            if project_id in self.connections:
                del self.connections[project_id]
        else:
            session.last_activity = datetime.now(timezone.utc)
            if self.redis_client:
                await self._store_session_redis(session)
    
    async def apply_operation(self, project_id: str, operation: Operation) -> Operation:
        """Apply an operation to the collaboration session"""
        session = self.sessions.get(project_id)
        if not session:
            raise ValueError(f"No collaboration session found for project {project_id}")
            
        # Transform operation against concurrent operations
        transformed_op = operation
        for existing_op in reversed(session.operations[-10:]):  # Only check recent ops
            if (existing_op.timestamp > operation.timestamp and 
                existing_op.file_path == operation.file_path and
                existing_op.user_id != operation.user_id):
                transformed_op, _ = OperationalTransform.transform_operation(
                    transformed_op, existing_op
                )
        
        # Add operation to session
        session.operations.append(transformed_op)
        session.last_activity = datetime.now(timezone.utc)
        
        # Update file version
        if transformed_op.file_path:
            current_version = session.file_versions.get(transformed_op.file_path, 0)
            session.file_versions[transformed_op.file_path] = current_version + 1
        
        # Broadcast to other users
        await self._broadcast_operation(project_id, transformed_op, exclude_user=operation.user_id)
        
        # Store in Redis
        if self.redis_client:
            await self._store_session_redis(session)
            
        return transformed_op
    
    async def update_cursor(
        self, 
        project_id: str, 
        user_id: str, 
        file_path: str,
        cursor_position: int,
        selection_start: Optional[int] = None,
        selection_end: Optional[int] = None
    ) -> None:
        """Update user cursor position"""
        session = self.sessions.get(project_id)
        if not session or user_id not in session.users:
            return
            
        user = session.users[user_id]
        user.cursor_position = cursor_position
        user.selection_start = selection_start
        user.selection_end = selection_end
        user.current_file = file_path
        user.last_seen = datetime.now(timezone.utc)
        
        # Broadcast cursor update
        await self._broadcast_operation(project_id, Operation(
            id=str(uuid.uuid4()),
            type=OperationType.CURSOR_MOVE,
            position=cursor_position,
            length=0,
            user_id=user_id,
            file_path=file_path
        ), exclude_user=user_id)
    
    async def get_session_state(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get current collaboration session state"""
        session = self.sessions.get(project_id)
        if not session:
            return None
            
        return {
            "project_id": session.project_id,
            "users": {
                user_id: {
                    "user_id": user.user_id,
                    "username": user.username,
                    "avatar_url": user.avatar_url,
                    "cursor_position": user.cursor_position,
                    "selection_start": user.selection_start,
                    "selection_end": user.selection_end,
                    "current_file": user.current_file,
                    "color": user.color,
                    "last_seen": user.last_seen.isoformat()
                }
                for user_id, user in session.users.items()
            },
            "file_versions": session.file_versions,
            "operation_count": len(session.operations),
            "last_activity": session.last_activity.isoformat()
        }
    
    async def get_file_operations(self, project_id: str, file_path: str, since_version: int = 0) -> List[Dict]:
        """Get operations for a specific file since a version"""
        session = self.sessions.get(project_id)
        if not session:
            return []
            
        file_operations = [
            {
                "id": op.id,
                "type": op.type,
                "position": op.position,
                "length": op.length,
                "content": op.content,
                "user_id": op.user_id,
                "timestamp": op.timestamp.isoformat(),
                "file_path": op.file_path
            }
            for op in session.operations
            if op.file_path == file_path
        ]
        
        return file_operations[since_version:]
    
    async def _broadcast_operation(self, project_id: str, operation: Operation, exclude_user: Optional[str] = None) -> None:
        """Broadcast operation to all connected users"""
        if project_id not in self.connections:
            return
            
        message = {
            "type": "collaboration_operation",
            "operation": {
                "id": operation.id,
                "type": operation.type,
                "position": operation.position,
                "length": operation.length,
                "content": operation.content,
                "user_id": operation.user_id,
                "timestamp": operation.timestamp.isoformat(),
                "file_path": operation.file_path
            }
        }
        
        # Send to all connected users except the sender
        for user_id, websocket in self.connections[project_id].items():
            if user_id != exclude_user:
                try:
                    await websocket.send(json.dumps(message))
                except websockets.exceptions.ConnectionClosed:
                    # Remove closed connection
                    await self.leave_session(project_id, user_id)
                except Exception as e:
                    print(f"Error broadcasting to {user_id}: {e}")
    
    async def _store_session_redis(self, session: CollaborationSession) -> None:
        """Store session state in Redis"""
        if not self.redis_client:
            return
            
        try:
            session_data = {
                "project_id": session.project_id,
                "users": {
                    user_id: asdict(user) 
                    for user_id, user in session.users.items()
                },
                "operations": [asdict(op) for op in session.operations[-100:]],  # Keep last 100 ops
                "file_versions": session.file_versions,
                "created_at": session.created_at.isoformat(),
                "last_activity": session.last_activity.isoformat()
            }
            
            await self.redis_client.setex(
                f"collaboration:{session.project_id}",
                3600,  # 1 hour TTL
                json.dumps(session_data, default=str)
            )
        except Exception as e:
            print(f"Error storing session in Redis: {e}")
    
    async def cleanup_inactive_sessions(self) -> None:
        """Clean up inactive collaboration sessions"""
        now = datetime.now(timezone.utc)
        inactive_sessions = []
        
        for project_id, session in self.sessions.items():
            # Remove sessions inactive for more than 1 hour
            if (now - session.last_activity).total_seconds() > 3600:
                inactive_sessions.append(project_id)
                
        for project_id in inactive_sessions:
            del self.sessions[project_id]
            if project_id in self.connections:
                del self.connections[project_id]