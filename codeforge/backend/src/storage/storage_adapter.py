"""
Storage Adapter - Provides unified interface for database and in-memory storage
"""
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
import os

from ..config.settings import settings
from .memory_storage import memory_storage


class StorageAdapter(ABC):
    """Abstract base class for storage adapters"""
    
    @abstractmethod
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def delete_project(self, project_id: str):
        pass


class InMemoryStorageAdapter(StorageAdapter):
    """In-memory storage adapter for development"""
    
    def __init__(self):
        self.storage = memory_storage
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.create_user(user_data)
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.storage.get_user_by_id(user_id)
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        return await self.storage.get_user_by_email(email)
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        return await self.storage.get_user_by_username(username)
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.update_user(user_id, updates)
    
    async def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.create_project(project_data)
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        return await self.storage.get_project(project_id)
    
    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.storage.get_user_projects(user_id)
    
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.update_project(project_id, updates)
    
    async def delete_project(self, project_id: str):
        return await self.storage.delete_project(project_id)
    
    # Additional methods specific to in-memory storage
    async def get_user_credits(self, user_id: str) -> Dict[str, Any]:
        return await self.storage.get_user_credits(user_id)
    
    async def update_credits(self, user_id: str, amount: float, transaction_type: str, description: str) -> Dict[str, Any]:
        return await self.storage.update_credits(user_id, amount, transaction_type, description)
    
    async def get_credit_transactions(self, user_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return await self.storage.get_credit_transactions(user_id, limit)
    
    async def create_file(self, file_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.create_file(file_data)
    
    async def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        return await self.storage.get_file(file_id)
    
    async def get_file_by_path(self, project_id: str, path: str) -> Optional[Dict[str, Any]]:
        return await self.storage.get_file_by_path(project_id, path)
    
    async def get_project_files(self, project_id: str) -> List[Dict[str, Any]]:
        return await self.storage.get_project_files(project_id)
    
    async def update_file(self, file_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.update_file(file_id, updates)
    
    async def delete_file(self, file_id: str):
        return await self.storage.delete_file(file_id)
    
    async def create_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.create_session(session_data)
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        return await self.storage.get_session(session_id)
    
    async def delete_session(self, session_id: str):
        return await self.storage.delete_session(session_id)
    
    async def create_container_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.create_container_session(session_data)
    
    async def get_container_sessions(self, user_id: str) -> List[Dict[str, Any]]:
        return await self.storage.get_container_sessions(user_id)
    
    async def update_container_session(self, session_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        return await self.storage.update_container_session(session_id, updates)


class DatabaseStorageAdapter(StorageAdapter):
    """Database storage adapter for production"""
    
    def __init__(self, db_session):
        self.db = db_session
        # TODO: Implement actual database operations
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def update_user(self, user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def create_project(self, project_data: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def get_user_projects(self, user_id: str) -> List[Dict[str, Any]]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def update_project(self, project_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")
    
    async def delete_project(self, project_id: str):
        # TODO: Implement with SQLAlchemy
        raise NotImplementedError("Database storage not yet implemented")


# Factory function to get the appropriate storage adapter
def get_storage_adapter(db_session=None) -> StorageAdapter:
    """
    Get the appropriate storage adapter based on configuration
    """
    # Check if we should use in-memory storage
    use_memory_storage = (
        os.getenv("USE_MEMORY_STORAGE", "false").lower() == "true" or
        not settings.DATABASE_URL or
        settings.DATABASE_URL == "sqlite:///:memory:"
    )
    
    if use_memory_storage:
        print("Using in-memory storage (no database required)")
        return InMemoryStorageAdapter()
    else:
        if not db_session:
            raise ValueError("Database session required for database storage")
        return DatabaseStorageAdapter(db_session)


# Global storage instance for easy access
storage: Optional[StorageAdapter] = None


def init_storage(db_session=None):
    """Initialize the global storage adapter"""
    global storage
    storage = get_storage_adapter(db_session)
    return storage


# For convenience, we can also provide a function to get the storage
def get_storage() -> StorageAdapter:
    """Get the initialized storage adapter"""
    if not storage:
        # Auto-initialize with in-memory storage if not initialized
        init_storage()
    return storage