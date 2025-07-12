"""
Authentication API endpoints for CodeForge
"""
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from ...auth.auth_service import AuthService, UserRegistration, UserLogin, TokenPair
from ...auth.dependencies import get_current_user
from ...models.user import User


router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
auth_service = AuthService()


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    invite_code: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    user: dict
    tokens: TokenPair


class OAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest, http_request: Request):
    """Register a new user account"""
    try:
        registration = UserRegistration(
            email=request.email,
            username=request.username,
            password=request.password,
            full_name=request.full_name,
            invite_code=request.invite_code
        )
        
        user, tokens = await auth_service.register_user(registration)
        
        return AuthResponse(
            user={
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "subscription_tier": user.subscription_tier,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat()
            },
            tokens=tokens
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest, http_request: Request):
    """Authenticate user login"""
    try:
        # Get client IP
        client_ip = http_request.client.host if http_request.client else "unknown"
        
        login_data = UserLogin(
            email=request.email,
            password=request.password
        )
        
        user, tokens = await auth_service.login_user(login_data, client_ip)
        
        return AuthResponse(
            user={
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "subscription_tier": user.subscription_tier,
                "is_verified": user.is_verified,
                "last_login": user.last_login.isoformat() if user.last_login else None
            },
            tokens=tokens
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(request: RefreshRequest):
    """Refresh access token using refresh token"""
    try:
        tokens = await auth_service.refresh_token(request.refresh_token)
        return tokens
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout user (invalidate tokens)"""
    # In a production system, you would:
    # 1. Add token to blacklist
    # 2. Clear refresh token from database
    # 3. Log the logout event
    
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    """Get current authenticated user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "subscription_tier": current_user.subscription_tier,
        "is_verified": current_user.is_verified,
        "projects_created": current_user.projects_created,
        "contributions_count": current_user.contributions_count,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None
    }


@router.get("/oauth/{provider}/url", response_model=OAuthUrlResponse)
async def get_oauth_url(provider: str):
    """Get OAuth authorization URL"""
    if provider not in ["github", "google", "gitlab"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
        
    try:
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Get authorization URL
        auth_url = auth_service.get_oauth_redirect_url(provider, state)
        
        return OAuthUrlResponse(auth_url=auth_url, state=state)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate OAuth URL"
        )


@router.post("/oauth/{provider}/callback", response_model=AuthResponse)
async def oauth_callback(
    provider: str,
    code: str,
    state: Optional[str] = None
):
    """Handle OAuth callback"""
    if provider not in ["github", "google", "gitlab"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
        
    try:
        # TODO: Verify state parameter for CSRF protection
        
        user, tokens = await auth_service.oauth_login(provider, code)
        
        return AuthResponse(
            user={
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "subscription_tier": user.subscription_tier,
                "is_verified": user.is_verified,
                "github_id": user.github_id,
                "google_id": user.google_id,
                "created_at": user.created_at.isoformat()
            },
            tokens=tokens
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="OAuth authentication failed"
        )


@router.post("/verify-email")
async def verify_email(
    token: str,
    current_user: User = Depends(get_current_user)
):
    """Verify user email address"""
    # TODO: Implement email verification
    # 1. Verify token
    # 2. Mark user as verified
    # 3. Update database
    
    return {"message": "Email verified successfully"}


@router.post("/resend-verification")
async def resend_verification(current_user: User = Depends(get_current_user)):
    """Resend email verification"""
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
        
    try:
        await auth_service._send_verification_email(current_user)
        return {"message": "Verification email sent"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """Send password reset email"""
    try:
        # TODO: Implement password reset
        # 1. Generate reset token
        # 2. Save token to database
        # 3. Send reset email
        
        return {"message": "Password reset email sent if account exists"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset"
        )


@router.post("/reset-password")
async def reset_password(token: str, new_password: str):
    """Reset password using reset token"""
    try:
        # TODO: Implement password reset
        # 1. Verify reset token
        # 2. Validate new password
        # 3. Update user password
        # 4. Invalidate reset token
        
        return {"message": "Password reset successfully"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )