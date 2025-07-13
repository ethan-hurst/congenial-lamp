"""
Authentication Service for CodeForge
Handles user registration, login, OAuth, and JWT tokens
"""
import asyncio
import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, Tuple
import bcrypt
import jwt
from pydantic import BaseModel, EmailStr
import httpx
from urllib.parse import urlencode

from ..config.settings import settings
from ..models.user import User
from ..services.credits_service_memory import CreditsService
from ..storage.storage_adapter import get_storage


class UserRegistration(BaseModel):
    """User registration data"""
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None
    invite_code: Optional[str] = None


class UserLogin(BaseModel):
    """User login data"""
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    """JWT token pair"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthService:
    """
    Comprehensive authentication service with:
    - Email/password authentication
    - OAuth integration (GitHub, Google, GitLab)
    - JWT token management
    - Rate limiting
    - Security features (2FA, device tracking)
    """
    
    def __init__(self):
        self.credits_service = None  # Initialized when needed
        self.failed_attempts: Dict[str, int] = {}
        self.lockout_times: Dict[str, datetime] = {}
        
    async def register_user(self, registration: UserRegistration) -> Tuple[User, TokenPair]:
        """Register a new user"""
        # Validate username and email availability
        if await self._user_exists(registration.email, registration.username):
            raise ValueError("User with this email or username already exists")
            
        # Validate password strength
        self._validate_password(registration.password)
        
        # Hash password
        password_hash = self._hash_password(registration.password)
        
        # Create user
        user = User(
            id=self._generate_user_id(),
            email=registration.email,
            username=registration.username,
            hashed_password=password_hash,
            full_name=registration.full_name,
            is_active=True,
            is_verified=False,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        # Save user to database
        await self._save_user(user)
        
        # Initialize user credits
        if not self.credits_service:
            self.credits_service = CreditsService(None)  # TODO: Pass DB session
        await self.credits_service.get_user_credits(user.id)
        
        # Generate tokens
        tokens = self._generate_token_pair(user)
        
        # Send verification email
        await self._send_verification_email(user)
        
        return user, tokens
        
    async def login_user(self, login: UserLogin, ip_address: str) -> Tuple[User, TokenPair]:
        """Authenticate user login"""
        # Check rate limiting
        if self._is_locked_out(login.email, ip_address):
            raise ValueError("Too many failed attempts. Please try again later.")
            
        # Find user
        user = await self._get_user_by_email(login.email)
        if not user:
            self._record_failed_attempt(login.email, ip_address)
            raise ValueError("Invalid email or password")
            
        # Verify password
        if not self._verify_password(login.password, user.hashed_password):
            self._record_failed_attempt(login.email, ip_address)
            raise ValueError("Invalid email or password")
            
        # Check if user is active
        if not user.is_active:
            raise ValueError("Account is deactivated")
            
        # Clear failed attempts
        self._clear_failed_attempts(login.email, ip_address)
        
        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await self._save_user(user)
        
        # Generate tokens
        tokens = self._generate_token_pair(user)
        
        return user, tokens
        
    async def refresh_token(self, refresh_token: str) -> TokenPair:
        """Refresh access token"""
        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            token_type = payload.get("type")
            
            if token_type != "refresh":
                raise ValueError("Invalid token type")
                
            # Get user
            user = await self._get_user_by_id(user_id)
            if not user or not user.is_active:
                raise ValueError("User not found or inactive")
                
            # Generate new token pair
            return self._generate_token_pair(user)
            
        except jwt.InvalidTokenError:
            raise ValueError("Invalid refresh token")
            
    async def verify_token(self, token: str) -> Optional[User]:
        """Verify JWT token and return user"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            user_id = payload.get("sub")
            token_type = payload.get("type", "access")
            
            if token_type != "access":
                return None
                
            # Get user
            user = await self._get_user_by_id(user_id)
            if not user or not user.is_active:
                return None
                
            return user
            
        except jwt.InvalidTokenError:
            return None
            
    async def verify_websocket_token(self, token: str) -> Optional[User]:
        """Verify JWT token for WebSocket connections"""
        # WebSocket connections use the same token verification
        return await self.verify_token(token)
            
    async def oauth_login(self, provider: str, code: str) -> Tuple[User, TokenPair]:
        """Handle OAuth login"""
        if provider == "github":
            return await self._github_oauth(code)
        elif provider == "google":
            return await self._google_oauth(code)
        elif provider == "gitlab":
            return await self._gitlab_oauth(code)
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")
            
    async def _github_oauth(self, code: str) -> Tuple[User, TokenPair]:
        """Handle GitHub OAuth"""
        # Exchange code for access token
        token_url = "https://github.com/login/oauth/access_token"
        token_data = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                token_url,
                data=token_data,
                headers={"Accept": "application/json"}
            )
            token_info = token_response.json()
            
            if "access_token" not in token_info:
                raise ValueError("Failed to get GitHub access token")
                
            # Get user info
            user_response = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {token_info['access_token']}",
                    "Accept": "application/json"
                }
            )
            github_user = user_response.json()
            
            # Get user emails
            emails_response = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"token {token_info['access_token']}",
                    "Accept": "application/json"
                }
            )
            emails = emails_response.json()
            
        # Find primary email
        primary_email = None
        for email in emails:
            if email.get("primary"):
                primary_email = email["email"]
                break
                
        if not primary_email:
            raise ValueError("No primary email found in GitHub account")
            
        # Check if user exists
        user = await self._get_user_by_email(primary_email)
        
        if not user:
            # Create new user
            user = User(
                id=self._generate_user_id(),
                email=primary_email,
                username=github_user["login"],
                hashed_password="",  # No password for OAuth users
                full_name=github_user.get("name"),
                avatar_url=github_user.get("avatar_url"),
                github_id=str(github_user["id"]),
                is_active=True,
                is_verified=True,  # GitHub emails are verified
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            await self._save_user(user)
            
            # Initialize credits
            if not self.credits_service:
                self.credits_service = CreditsService(None)
            await self.credits_service.get_user_credits(user.id)
        else:
            # Update GitHub ID if not set
            if not user.github_id:
                user.github_id = str(github_user["id"])
                await self._save_user(user)
                
        # Generate tokens
        tokens = self._generate_token_pair(user)
        
        return user, tokens
        
    async def _google_oauth(self, code: str) -> Tuple[User, TokenPair]:
        """Handle Google OAuth"""
        # Exchange code for access token
        token_url = "https://oauth2.googleapis.com/token"
        token_data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": "http://localhost:3000/auth/google/callback"  # TODO: Make configurable
        }
        
        async with httpx.AsyncClient() as client:
            token_response = await client.post(token_url, data=token_data)
            token_info = token_response.json()
            
            if "access_token" not in token_info:
                raise ValueError("Failed to get Google access token")
                
            # Get user info
            user_response = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={
                    "Authorization": f"Bearer {token_info['access_token']}"
                }
            )
            google_user = user_response.json()
            
        # Check if user exists
        user = await self._get_user_by_email(google_user["email"])
        
        if not user:
            # Create new user
            username = google_user.get("email", "").split("@")[0]
            # Ensure username is unique
            counter = 1
            original_username = username
            while await self._username_exists(username):
                username = f"{original_username}{counter}"
                counter += 1
                
            user = User(
                id=self._generate_user_id(),
                email=google_user["email"],
                username=username,
                hashed_password="",
                full_name=google_user.get("name"),
                avatar_url=google_user.get("picture"),
                google_id=google_user["id"],
                is_active=True,
                is_verified=google_user.get("verified_email", False),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            
            await self._save_user(user)
            
            # Initialize credits
            if not self.credits_service:
                self.credits_service = CreditsService(None)
            await self.credits_service.get_user_credits(user.id)
        else:
            # Update Google ID if not set
            if not user.google_id:
                user.google_id = google_user["id"]
                await self._save_user(user)
                
        # Generate tokens
        tokens = self._generate_token_pair(user)
        
        return user, tokens
        
    def _generate_token_pair(self, user: User) -> TokenPair:
        """Generate JWT token pair"""
        now = datetime.now(timezone.utc)
        
        # Access token (short-lived)
        access_payload = {
            "sub": user.id,
            "email": user.email,
            "username": user.username,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        }
        
        access_token = jwt.encode(
            access_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        # Refresh token (long-lived)
        refresh_payload = {
            "sub": user.id,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        }
        
        refresh_token = jwt.encode(
            refresh_payload,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        
    def _hash_password(self, password: str) -> str:
        """Hash password using bcrypt"""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
    def _verify_password(self, password: str, hashed: str) -> bool:
        """Verify password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
        
    def _validate_password(self, password: str):
        """Validate password strength"""
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")
            
        if not any(c.isupper() for c in password):
            raise ValueError("Password must contain at least one uppercase letter")
            
        if not any(c.islower() for c in password):
            raise ValueError("Password must contain at least one lowercase letter")
            
        if not any(c.isdigit() for c in password):
            raise ValueError("Password must contain at least one digit")
            
    def _generate_user_id(self) -> str:
        """Generate unique user ID"""
        return f"user_{secrets.token_urlsafe(16)}"
        
    def _is_locked_out(self, email: str, ip_address: str) -> bool:
        """Check if user/IP is locked out"""
        now = datetime.now(timezone.utc)
        
        # Check email lockout
        email_key = f"email:{email}"
        if email_key in self.lockout_times:
            if now < self.lockout_times[email_key]:
                return True
                
        # Check IP lockout
        ip_key = f"ip:{ip_address}"
        if ip_key in self.lockout_times:
            if now < self.lockout_times[ip_key]:
                return True
                
        return False
        
    def _record_failed_attempt(self, email: str, ip_address: str):
        """Record failed login attempt"""
        email_key = f"email:{email}"
        ip_key = f"ip:{ip_address}"
        
        # Increment counters
        self.failed_attempts[email_key] = self.failed_attempts.get(email_key, 0) + 1
        self.failed_attempts[ip_key] = self.failed_attempts.get(ip_key, 0) + 1
        
        # Apply lockout if threshold reached
        if self.failed_attempts[email_key] >= 5:
            self.lockout_times[email_key] = datetime.now(timezone.utc) + timedelta(minutes=15)
            
        if self.failed_attempts[ip_key] >= 10:
            self.lockout_times[ip_key] = datetime.now(timezone.utc) + timedelta(minutes=30)
            
    def _clear_failed_attempts(self, email: str, ip_address: str):
        """Clear failed attempts for successful login"""
        email_key = f"email:{email}"
        ip_key = f"ip:{ip_address}"
        
        self.failed_attempts.pop(email_key, None)
        self.failed_attempts.pop(ip_key, None)
        self.lockout_times.pop(email_key, None)
        self.lockout_times.pop(ip_key, None)
        
    async def _user_exists(self, email: str, username: str) -> bool:
        """Check if user exists by email or username"""
        storage = get_storage()
        user_by_email = await storage.get_user_by_email(email)
        user_by_username = await storage.get_user_by_username(username)
        return user_by_email is not None or user_by_username is not None
        
    async def _username_exists(self, username: str) -> bool:
        """Check if username exists"""
        storage = get_storage()
        user = await storage.get_user_by_username(username)
        return user is not None
        
    async def _get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email"""
        storage = get_storage()
        user_data = await storage.get_user_by_email(email)
        if user_data:
            return User(**user_data)
        return None
        
    async def _get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID"""
        storage = get_storage()
        user_data = await storage.get_user_by_id(user_id)
        if user_data:
            return User(**user_data)
        return None
        
    async def _save_user(self, user: User):
        """Save user to database"""
        storage = get_storage()
        user_data = user.dict()
        
        # Check if user exists
        existing = await storage.get_user_by_id(user.id)
        if existing:
            # Update existing user
            await storage.update_user(user.id, user_data)
        else:
            # Create new user
            await storage.create_user(user_data)
        
    async def _send_verification_email(self, user: User):
        """Send email verification"""
        # TODO: Implement email sending
        print(f"Would send verification email to {user.email}")
        
    def get_oauth_redirect_url(self, provider: str, state: str) -> str:
        """Get OAuth redirect URL"""
        if provider == "github":
            params = {
                "client_id": settings.GITHUB_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/auth/github/callback",
                "scope": "user:email",
                "state": state
            }
            return f"https://github.com/login/oauth/authorize?{urlencode(params)}"
            
        elif provider == "google":
            params = {
                "client_id": settings.GOOGLE_CLIENT_ID,
                "redirect_uri": "http://localhost:3000/auth/google/callback",
                "scope": "openid email profile",
                "response_type": "code",
                "state": state
            }
            return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
            
        else:
            raise ValueError(f"Unsupported OAuth provider: {provider}")