"""
Authentication API endpoints for CodeForge
"""
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from ...services.auth_service import AuthService
from ...auth.dependencies import get_current_user
from ...models.user import User
from ...database.connection import get_database_session


router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class AuthResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    user: dict


class OAuthUrlResponse(BaseModel):
    auth_url: str
    state: str


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


@router.post("/register", response_model=AuthResponse)
async def register(request: RegisterRequest):
    """Register a new user account"""
    try:
        auth_service = AuthService()
        
        # Create user
        user = auth_service.create_user(
            email=request.email,
            username=request.username,
            password=request.password,
            full_name=request.full_name
        )
        
        # Generate tokens
        tokens = auth_service.create_access_token_for_user(user)
        
        return AuthResponse(**tokens)
        
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
async def login(request: LoginRequest):
    """Authenticate user login"""
    try:
        auth_service = AuthService()
        
        # Authenticate user
        user = auth_service.authenticate_user(request.email, request.password)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password"
            )
        
        # Generate tokens
        tokens = auth_service.create_access_token_for_user(user)
        
        return AuthResponse(**tokens)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh")
async def refresh_tokens(request: RefreshRequest):
    """Refresh access token using refresh token"""
    try:
        auth_service = AuthService()
        tokens = auth_service.refresh_access_token(request.refresh_token)
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
        "bio": current_user.bio,
        "location": current_user.location,
        "website": current_user.website,
        "avatar_url": current_user.avatar_url,
        "subscription_tier": current_user.subscription_tier,
        "is_verified": current_user.is_verified,
        "is_student": current_user.is_student,
        "is_nonprofit": current_user.is_nonprofit,
        "projects_created": current_user.projects_created,
        "contributions_count": current_user.contributions_count,
        "helpful_answers_count": current_user.helpful_answers_count,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        "preferences": current_user.preferences,
        "editor_settings": current_user.editor_settings
    }


@router.put("/me")
async def update_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user)
):
    """Update user profile"""
    try:
        auth_service = AuthService()
        
        updated_user = auth_service.update_user_profile(
            user_id=current_user.id,
            full_name=request.full_name,
            bio=request.bio,
            location=request.location,
            website=request.website
        )
        
        if not updated_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "id": updated_user.id,
            "email": updated_user.email,
            "username": updated_user.username,
            "full_name": updated_user.full_name,
            "bio": updated_user.bio,
            "location": updated_user.location,
            "website": updated_user.website,
            "avatar_url": updated_user.avatar_url,
            "updated_at": updated_user.updated_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile"
        )


@router.get("/oauth/{provider}/url", response_model=OAuthUrlResponse)
async def get_oauth_url(
    provider: str,
    redirect_uri: str = Query(..., description="OAuth redirect URI")
):
    """Get OAuth authorization URL"""
    if provider not in ["github", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
        
    try:
        auth_service = AuthService()
        
        # Generate state for CSRF protection
        state = secrets.token_urlsafe(32)
        
        # Get authorization URL
        auth_url = await auth_service.get_oauth_authorization_url(provider, redirect_uri, state)
        
        return OAuthUrlResponse(auth_url=auth_url, state=state)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate OAuth URL"
        )


@router.post("/oauth/{provider}/callback", response_model=AuthResponse)
async def oauth_callback(
    provider: str,
    code: str = Query(..., description="OAuth authorization code"),
    redirect_uri: str = Query(..., description="OAuth redirect URI"),
    state: Optional[str] = Query(None, description="CSRF state parameter")
):
    """Handle OAuth callback"""
    if provider not in ["github", "google"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported OAuth provider"
        )
        
    try:
        auth_service = AuthService()
        
        # TODO: Verify state parameter for CSRF protection
        
        tokens = await auth_service.handle_oauth_callback(provider, code, redirect_uri)
        
        return AuthResponse(**tokens)
        
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
    token: str = Query(..., description="Email verification token"),
    current_user: User = Depends(get_current_user)
):
    """Verify user email address"""
    try:
        auth_service = AuthService()
        
        success = auth_service.verify_email(current_user.id, token)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token"
            )
        
        return {"message": "Email verified successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed"
        )


@router.post("/resend-verification")
async def resend_verification(current_user: User = Depends(get_current_user)):
    """Resend email verification"""
    if current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already verified"
        )
        
    try:
        auth_service = AuthService()
        verification_token = auth_service.send_verification_email(current_user)
        
        return {
            "message": "Verification email sent",
            "token": verification_token  # In production, don't return this
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email"
        )


@router.post("/forgot-password")
async def forgot_password(email: EmailStr):
    """Send password reset email"""
    try:
        auth_service = AuthService()
        reset_token = auth_service.send_password_reset_email(email)
        
        # Always return success for security (don't leak if email exists)
        return {
            "message": "Password reset email sent if account exists",
            "token": reset_token if reset_token else None  # In production, don't return this
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process password reset"
        )


@router.post("/reset-password")
async def reset_password(
    token: str = Query(..., description="Password reset token"),
    new_password: str = Query(..., description="New password")
):
    """Reset password using reset token"""
    try:
        auth_service = AuthService()
        
        success = auth_service.reset_password(token, new_password)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )
        
        return {"message": "Password reset successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed"
        )


@router.delete("/account")
async def deactivate_account(current_user: User = Depends(get_current_user)):
    """Deactivate user account"""
    try:
        auth_service = AuthService()
        
        success = auth_service.deactivate_user(current_user.id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate account"
            )
        
        return {"message": "Account deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Account deactivation failed"
        )