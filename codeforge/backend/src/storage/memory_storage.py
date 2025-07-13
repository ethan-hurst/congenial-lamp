"""
In-Memory Storage for Development
Provides database-like functionality without requiring a real database
"""
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import json
import asyncio
from collections import defaultdict


class InMemoryStorage:
    """
    In-memory storage implementation for development and testing
    Mimics database operations without persistence
    """
    
    def __init__(self):
        # User storage
        self.users: Dict[str, Dict[str, Any]] = {}
        self.users_by_email: Dict[str, str] = {}  # email -> user_id
        self.users_by_username: Dict[str, str] = {}  # username -> user_id
        
        # Project storage
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.projects_by_user: Dict[str, List[str]] = defaultdict(list)  # user_id -> [project_ids]
        
        # File storage
        self.files: Dict[str, Dict[str, Any]] = {}
        self.files_by_project: Dict[str, List[str]] = defaultdict(list)  # project_id -> [file_ids]
        
        # Credits storage
        self.user_credits: Dict[str, Dict[str, Any]] = {}
        self.credit_transactions: List[Dict[str, Any]] = []
        
        # Session storage
        self.sessions: Dict[str, Dict[str, Any]] = {}
        self.refresh_tokens: Dict[str, Dict[str, Any]] = {}
        
        # Container sessions
        self.container_sessions: Dict[str, Dict[str, Any]] = {}
        
        # AI conversations
        self.ai_conversations: Dict[str, Dict[str, Any]] = {}
        self.ai_messages: List[Dict[str, Any]] = []
        
        # Collaboration sessions
        self.collaboration_sessions: Dict[str, Dict[str, Any]] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
        
        # Initialize with demo data
        self._init_demo_data()
        
    def _init_demo_data(self):
        """Initialize with some demo data for development"""
        # Create demo user
        demo_user_id = "user_demo_123"
        self.users[demo_user_id] = {
            "id": demo_user_id,
            "email": "demo@codeforge.dev",
            "username": "demo",
            "hashed_password": "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiLXCrXEJDiK",  # password: demo123
            "full_name": "Demo User",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_login": None,
            "avatar_url": None,
            "github_id": None,
            "google_id": None,
        }
        self.users_by_email["demo@codeforge.dev"] = demo_user_id
        self.users_by_username["demo"] = demo_user_id
        
        # Initialize demo user credits
        self.user_credits[demo_user_id] = {
            "user_id": demo_user_id,
            "balance": 10000.0,  # $100 in credits
            "total_earned": 0.0,
            "total_spent": 0.0,
            "updated_at": datetime.now(timezone.utc),
        }
        
        # Create demo project
        demo_project_id = "proj_demo_456"
        self.projects[demo_project_id] = {
            "id": demo_project_id,
            "user_id": demo_user_id,
            "name": "Demo Project",
            "description": "A demo project for testing",
            "language": "python",
            "framework": None,
            "is_public": False,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "last_accessed": datetime.now(timezone.utc),
            "settings": {
                "cpu_limit": 2,
                "memory_limit_mb": 2048,
                "environment_variables": {},
            },
        }
        self.projects_by_user[demo_user_id].append(demo_project_id)
        
        # Create demo files
        demo_files = [
            {
                "id": "file_demo_001",
                "project_id": demo_project_id,
                "path": "/main.py",
                "name": "main.py",
                "type": "file",
                "content": '# Welcome to CodeForge!\n\nprint("Hello, World!")\n',
                "size": 50,
                "mime_type": "text/x-python",
                "created_at": datetime.now(timezone.utc),
                "modified_at": datetime.now(timezone.utc),
                "version": 1,
            },
            {
                "id": "file_demo_002",
                "project_id": demo_project_id,
                "path": "/README.md",
                "name": "README.md",
                "type": "file",
                "content": "# Demo Project\n\nThis is a demo project for CodeForge.",
                "size": 45,
                "mime_type": "text/markdown",
                "created_at": datetime.now(timezone.utc),
                "modified_at": datetime.now(timezone.utc),
                "version": 1,
            },
        ]
        
        for file_data in demo_files:
            self.files[file_data["id"]] = file_data
            self.files_by_project[demo_project_id].append(file_data["id"])
    
    # User operations
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user"""
        async with self._lock:
            user_id = user_data["id"]
            
            # Check if user already exists
            if user_id in self.users:
                raise ValueError("User already exists")
            if user_data["email"] in self.users_by_email:
                raise ValueError("Email already in use")
            if user_data["username"] in self.users_by_username:
                raise ValueError("Username already in use")
            
            # Store user
            self.users[user_id] = user_data
            self.users_by_email[user_data["email"]] = user_id
            self.users_by_username[user_data["username"]] = user_id
            
            # Initialize user credits
            self.user_credits[user_id] = {
                "user_id": user_id,
                "balance": 500.0,  # $5 free credits for new users
                "total_earned": 0.0,
                "total_spent": 0.0,
                "updated_at": datetime.now(timezone.utc),
            }
            
            return user_data
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return self.users.get(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        user_id = self.users_by_email.get(email)
        if user_id:
            return self.users.get(user_id)
        return None
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        user_id = self.users_by_username.get(username)
        if user_id:
            return self.users.get(user_id)
        return None
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update user data"""
        async with self._lock:
            if user_id not in self.users:
                raise ValueError("User not found")
            
            user = self.users[user_id]
            
            # Handle email change
            if "email" in updates and updates["email"] != user["email"]:
                # Check if new email is available
                if updates["email"] in self.users_by_email:
                    raise ValueError("Email already in use")
                
                # Update email mapping
                del self.users_by_email[user["email"]]
                self.users_by_email[updates["email"]] = user_id
            
            # Handle username change
            if "username" in updates and updates["username"] != user["username"]:
                # Check if new username is available
                if updates["username"] in self.users_by_username:
                    raise ValueError("Username already in use")
                
                # Update username mapping
                del self.users_by_username[user["username"]]
                self.users_by_username[updates["username"]] = user_id
            
            # Update user data
            user.update(updates)
            user["updated_at"] = datetime.now(timezone.utc)
            
            return user
    
    # Project operations
    async def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new project"""
        async with self._lock:
            project_id = project_data["id"]
            user_id = project_data["user_id"]
            
            # Store project
            self.projects[project_id] = project_data
            self.projects_by_user[user_id].append(project_id)
            
            return project_data
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Get project by ID"""
        return self.projects.get(project_id)
    
    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all projects for a user"""
        project_ids = self.projects_by_user.get(user_id, [])
        return [self.projects[pid] for pid in project_ids if pid in self.projects]
    
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update project data"""
        async with self._lock:
            if project_id not in self.projects:
                raise ValueError("Project not found")
            
            project = self.projects[project_id]
            project.update(updates)
            project["updated_at"] = datetime.now(timezone.utc)
            
            return project
    
    async def delete_project(self, project_id: str):
        """Delete a project"""
        async with self._lock:
            if project_id not in self.projects:
                return
            
            project = self.projects[project_id]
            user_id = project["user_id"]
            
            # Remove from user's projects
            self.projects_by_user[user_id].remove(project_id)
            
            # Delete all project files
            file_ids = self.files_by_project.get(project_id, []).copy()
            for file_id in file_ids:
                del self.files[file_id]
            del self.files_by_project[project_id]
            
            # Delete project
            del self.projects[project_id]
    
    # File operations
    async def create_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new file"""
        async with self._lock:
            file_id = file_data["id"]
            project_id = file_data["project_id"]
            
            # Store file
            self.files[file_id] = file_data
            self.files_by_project[project_id].append(file_id)
            
            return file_data
    
    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file by ID"""
        return self.files.get(file_id)
    
    async def get_file_by_path(self, project_id: str, path: str) -> Optional[Dict[str, Any]]:
        """Get file by project and path"""
        file_ids = self.files_by_project.get(project_id, [])
        for file_id in file_ids:
            file_data = self.files.get(file_id)
            if file_data and file_data["path"] == path:
                return file_data
        return None
    
    async def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        """Get all files for a project"""
        file_ids = self.files_by_project.get(project_id, [])
        return [self.files[fid] for fid in file_ids if fid in self.files]
    
    async def update_file(self, file_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update file data"""
        async with self._lock:
            if file_id not in self.files:
                raise ValueError("File not found")
            
            file_data = self.files[file_id]
            file_data.update(updates)
            file_data["modified_at"] = datetime.now(timezone.utc)
            file_data["version"] = file_data.get("version", 1) + 1
            
            return file_data
    
    async def delete_file(self, file_id: str):
        """Delete a file"""
        async with self._lock:
            if file_id not in self.files:
                return
            
            file_data = self.files[file_id]
            project_id = file_data["project_id"]
            
            # Remove from project's files
            self.files_by_project[project_id].remove(file_id)
            
            # Delete file
            del self.files[file_id]
    
    # Credits operations
    async def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        """Get user credits"""
        return self.user_credits.get(user_id, {
            "user_id": user_id,
            "balance": 0.0,
            "total_earned": 0.0,
            "total_spent": 0.0,
            "updated_at": datetime.now(timezone.utc),
        })
    
    async def update_credits(self, user_id: str, amount: float, transaction_type: str, description: str) -> Dict[str, Any]:
        """Update user credits"""
        async with self._lock:
            credits = await self.get_user_credits(user_id)
            
            # Update balance
            credits["balance"] += amount
            
            if amount > 0:
                credits["total_earned"] += amount
            else:
                credits["total_spent"] += abs(amount)
            
            credits["updated_at"] = datetime.now(timezone.utc)
            
            # Store updated credits
            self.user_credits[user_id] = credits
            
            # Record transaction
            transaction = {
                "id": f"txn_{len(self.credit_transactions) + 1}",
                "user_id": user_id,
                "amount": amount,
                "type": transaction_type,
                "description": description,
                "balance_after": credits["balance"],
                "created_at": datetime.now(timezone.utc),
            }
            self.credit_transactions.append(transaction)
            
            return credits
    
    async def get_credit_transactions(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get credit transactions for a user"""
        user_transactions = [
            txn for txn in self.credit_transactions
            if txn["user_id"] == user_id
        ]
        return sorted(user_transactions, key=lambda x: x["created_at"], reverse=True)[:limit]
    
    # Session operations
    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new session"""
        async with self._lock:
            session_id = session_data["id"]
            self.sessions[session_id] = session_data
            return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        return self.sessions.get(session_id)
    
    async def delete_session(self, session_id: str):
        """Delete a session"""
        async with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]
    
    # Container session operations
    async def create_container_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a container session"""
        async with self._lock:
            session_id = session_data["id"]
            self.container_sessions[session_id] = session_data
            return session_data
    
    async def get_container_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get container sessions for a user"""
        return [
            session for session in self.container_sessions.values()
            if session["user_id"] == user_id
        ]
    
    async def update_container_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update container session"""
        async with self._lock:
            if session_id not in self.container_sessions:
                raise ValueError("Container session not found")
            
            session = self.container_sessions[session_id]
            session.update(updates)
            return session


# Global instance for development
memory_storage = InMemoryStorage()