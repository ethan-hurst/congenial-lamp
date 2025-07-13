"""
Authentication dependencies for FastAPI
"""
from typing import Optional
from fastapi import Depends, HTTPException, status, WebSocket, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..auth.auth_service import AuthService
from ..models.user import User


# Security scheme
security = HTTPBearer()

# Auth service instance
auth_service = AuthService()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from JWT token
    """
    token = credentials.credentials
    
    user = await auth_service.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user if authenticated, None otherwise
    """
    if not credentials:
        return None
        
    user = await auth_service.verify_token(credentials.credentials)
    return user


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
) -> User:
    """
    Get current authenticated user for WebSocket connections
    WebSocket auth can come from query params or first message
    """
    if not token:
        # Try to get token from first message
        try:
            first_message = await websocket.receive_json()
            token = first_message.get("token")
            
            if not token:
                await websocket.close(code=4001, reason="Authentication required")
                raise ValueError("No authentication token provided")
        except Exception:
            await websocket.close(code=4001, reason="Authentication required")
            raise ValueError("Failed to authenticate WebSocket connection")
    
    user = await auth_service.verify_websocket_token(token)
    if not user:
        await websocket.close(code=4001, reason="Invalid authentication token")
        raise ValueError("Invalid authentication token")
    
    return user


class RequirePermission:
    """
    Dependency to require specific permissions
    """
    def __init__(self, permission: str):
        self.permission = permission
        
    async def __call__(self, user: User = Depends(get_current_user)) -> User:
        # TODO: Implement permission checking
        # For now, just return the user
        return user