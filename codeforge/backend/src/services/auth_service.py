"""
Authentication Service for CodeForge
Handles user registration, login, OAuth, and session management
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from jose import jwt
import httpx
import bcrypt

from ..database.connection import get_db
from ..models.user import User, Team, TeamMember
from ..config.settings import settings
from ..auth.dependencies import create_access_token


class AuthService:
    """
    Authentication service handling all auth operations
    """
    
    def __init__(self):
        self.password_context = bcrypt
        
        # OAuth configurations
        self.oauth_configs = {
            "github": {
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "authorize_url": "https://github.com/login/oauth/authorize",
                "token_url": "https://github.com/login/oauth/access_token",
                "user_url": "https://api.github.com/user",
                "scope": "user:email"
            },
            "google": {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
                "token_url": "https://oauth2.googleapis.com/token",
                "user_url": "https://www.googleapis.com/oauth2/v2/userinfo",
                "scope": "openid email profile"
            }
        }
    
    def hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))
    
    def create_user(
        self,
        email: str,
        username: str,
        password: str,
        full_name: Optional[str] = None,
        role: str = "user",
        is_verified: bool = False
    ) -> User:
        """Create a new user account"""
        db = get_db()
        
        try:
            # Check if email already exists
            existing_email = db.query(User).filter(User.email == email).first()
            if existing_email:
                raise ValueError("Email already registered")
            
            # Check if username already exists
            existing_username = db.query(User).filter(User.username == username).first()
            if existing_username:
                raise ValueError("Username already taken")
            
            # Create user
            user = User(
                id=str(uuid.uuid4()),
                email=email,
                username=username,
                hashed_password=self.hash_password(password),
                full_name=full_name,
                is_verified=is_verified,
                subscription_tier="free"
            )
            
            db.add(user)
            db.commit()
            db.refresh(user)
            
            return user
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password"""
        db = get_db()
        
        try:
            user = db.query(User).filter(User.email == email, User.is_active == True).first()
            
            if not user or not self.verify_password(password, user.hashed_password):
                return None
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.commit()
            
            return user
            
        finally:
            db.close()
    
    def create_access_token_for_user(self, user: User) -> Dict[str, Any]:
        """Create access and refresh tokens for user"""
        access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        refresh_token_expires = timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        
        access_token = create_access_token(
            data={"sub": user.id, "email": user.email},
            expires_delta=access_token_expires
        )
        
        refresh_token = create_access_token(
            data={"sub": user.id, "type": "refresh"},
            expires_delta=refresh_token_expires
        )
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "full_name": user.full_name,
                "avatar_url": user.avatar_url,
                "is_verified": user.is_verified,
                "subscription_tier": user.subscription_tier
            }
        }
    
    async def get_oauth_authorization_url(self, provider: str, redirect_uri: str, state: str) -> str:
        """Get OAuth authorization URL"""
        if provider not in self.oauth_configs:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        config = self.oauth_configs[provider]
        
        params = {
            "client_id": config["client_id"],
            "redirect_uri": redirect_uri,
            "scope": config["scope"],
            "state": state,
            "response_type": "code"
        }
        
        if provider == "google":
            params["access_type"] = "offline"
            params["prompt"] = "consent"
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        return f"{config['authorize_url']}?{query_string}"
    
    async def handle_oauth_callback(
        self,
        provider: str,
        code: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """Handle OAuth callback and create/login user"""
        if provider not in self.oauth_configs:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
        
        config = self.oauth_configs[provider]
        
        # Exchange code for access token
        token_data = await self._exchange_oauth_code(provider, code, redirect_uri)
        access_token = token_data["access_token"]
        
        # Get user info from OAuth provider
        user_info = await self._get_oauth_user_info(provider, access_token)
        
        # Create or update user
        user = await self._create_or_update_oauth_user(provider, user_info)
        
        # Generate our tokens
        return self.create_access_token_for_user(user)
    
    async def _exchange_oauth_code(self, provider: str, code: str, redirect_uri: str) -> Dict[str, Any]:
        """Exchange OAuth code for access token"""
        config = self.oauth_configs[provider]
        
        token_data = {
            "client_id": config["client_id"],
            "client_secret": config["client_secret"],
            "code": code,
            "redirect_uri": redirect_uri,
            "grant_type": "authorization_code"
        }
        
        headers = {"Accept": "application/json"}
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                config["token_url"],
                data=token_data,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
    
    async def _get_oauth_user_info(self, provider: str, access_token: str) -> Dict[str, Any]:
        """Get user info from OAuth provider"""
        config = self.oauth_configs[provider]
        
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(config["user_url"], headers=headers)
            response.raise_for_status()
            user_data = response.json()
            
            # Get email for GitHub (requires separate API call)
            if provider == "github" and not user_data.get("email"):
                email_response = await client.get(
                    "https://api.github.com/user/emails",
                    headers=headers
                )
                if email_response.status_code == 200:
                    emails = email_response.json()
                    primary_email = next(
                        (email["email"] for email in emails if email["primary"]),
                        emails[0]["email"] if emails else None
                    )
                    user_data["email"] = primary_email
            
            return user_data
    
    async def _create_or_update_oauth_user(self, provider: str, user_info: Dict[str, Any]) -> User:
        """Create or update user from OAuth info"""
        db = get_db()
        
        try:
            # Extract user data based on provider
            if provider == "github":
                oauth_id = str(user_info["id"])
                email = user_info.get("email")
                username = user_info["login"]
                full_name = user_info.get("name")
                avatar_url = user_info.get("avatar_url")
                id_field = "github_id"
            elif provider == "google":
                oauth_id = user_info["id"]
                email = user_info["email"]
                username = email.split("@")[0]  # Use email prefix as username
                full_name = user_info.get("name")
                avatar_url = user_info.get("picture")
                id_field = "google_id"
            
            # Check if user exists by OAuth ID
            user = db.query(User).filter(getattr(User, id_field) == oauth_id).first()
            
            if user:
                # Update existing user
                user.email = email or user.email
                user.full_name = full_name or user.full_name
                user.avatar_url = avatar_url or user.avatar_url
                user.last_login = datetime.utcnow()
                user.is_verified = True  # OAuth users are considered verified
            else:
                # Check if user exists by email
                user = db.query(User).filter(User.email == email).first()
                
                if user:
                    # Link existing account
                    setattr(user, id_field, oauth_id)
                    user.is_verified = True
                    user.last_login = datetime.utcnow()
                else:
                    # Create new user
                    # Ensure username is unique
                    base_username = username
                    counter = 1
                    while db.query(User).filter(User.username == username).first():
                        username = f"{base_username}{counter}"
                        counter += 1
                    
                    user = User(
                        id=str(uuid.uuid4()),
                        email=email,
                        username=username,
                        hashed_password=self.hash_password(secrets.token_urlsafe(32)),  # Random password
                        full_name=full_name,
                        avatar_url=avatar_url,
                        is_verified=True,
                        subscription_tier="free",
                        last_login=datetime.utcnow()
                    )
                    setattr(user, id_field, oauth_id)
                    db.add(user)
            
            db.commit()
            db.refresh(user)
            return user
            
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh access token using refresh token"""
        try:
            payload = jwt.decode(refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if token_type != "refresh" or not user_id:
                raise ValueError("Invalid refresh token")
            
        except jwt.JWTError:
            raise ValueError("Invalid refresh token")
        
        db = get_db()
        try:
            user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
            
            if not user:
                raise ValueError("User not found")
            
            return self.create_access_token_for_user(user)
            
        finally:
            db.close()
    
    def send_verification_email(self, user: User) -> str:
        """Send email verification (returns verification token for now)"""
        # Generate verification token
        verification_token = secrets.token_urlsafe(32)
        
        # TODO: Store token in database with expiration
        # TODO: Send actual email
        
        return verification_token
    
    def verify_email(self, user_id: str, token: str) -> bool:
        """Verify email with token"""
        db = get_db()
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return False
            
            # TODO: Validate token from database
            # For now, just mark as verified
            user.is_verified = True
            db.commit()
            
            return True
            
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()
    
    def send_password_reset_email(self, email: str) -> Optional[str]:
        """Send password reset email"""
        db = get_db()
        
        try:
            user = db.query(User).filter(User.email == email, User.is_active == True).first()
            
            if not user:
                return None
            
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            
            # TODO: Store token in database with expiration
            # TODO: Send actual email
            
            return reset_token
            
        finally:
            db.close()
    
    def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password with token"""
        # TODO: Validate token from database and get user
        # For now, this is a placeholder
        return False
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate user account"""
        db = get_db()
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return False
            
            user.is_active = False
            db.commit()
            
            return True
            
        except Exception:
            db.rollback()
            return False
        finally:
            db.close()
    
    def update_user_profile(
        self,
        user_id: str,
        full_name: Optional[str] = None,
        bio: Optional[str] = None,
        location: Optional[str] = None,
        website: Optional[str] = None
    ) -> Optional[User]:
        """Update user profile"""
        db = get_db()
        
        try:
            user = db.query(User).filter(User.id == user_id).first()
            
            if not user:
                return None
            
            if full_name is not None:
                user.full_name = full_name
            if bio is not None:
                user.bio = bio
            if location is not None:
                user.location = location
            if website is not None:
                user.website = website
            
            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)
            
            return user
            
        except Exception:
            db.rollback()
            return None
        finally:
            db.close()