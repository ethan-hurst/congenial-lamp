"""
Database connection management
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from typing import Generator

from ..config.settings import settings

# Create declarative base
Base = declarative_base()

# Create metadata
metadata = MetaData()

# Database engine configuration
if settings.ENVIRONMENT == "test":
    # Use in-memory SQLite for testing
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=settings.is_development
    )
else:
    # Production/Development database
    engine = create_engine(
        settings.DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=20,
        max_overflow=0,
        echo=settings.is_development
    )

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_database_session() -> Generator[Session, None, None]:
    """
    Get database session for dependency injection
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """
    Create all database tables
    """
    # Import all models to ensure they're registered
    from ..models import user, project, container, deployment, collaboration, database
    
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """
    Drop all database tables (for testing)
    """
    Base.metadata.drop_all(bind=engine)


def get_db() -> Session:
    """
    Get database session (for use outside of FastAPI)
    """
    return SessionLocal()


class DatabaseManager:
    """
    Database management utility class
    """
    
    @staticmethod
    def init_db():
        """Initialize database with tables and initial data"""
        create_tables()
        DatabaseManager.create_initial_data()
    
    @staticmethod
    def create_initial_data():
        """Create initial data for development"""
        from ..models.user import User, UserRole
        from ..services.auth_service import AuthService
        
        db = get_db()
        try:
            # Check if admin user exists
            admin_user = db.query(User).filter(User.email == "admin@codeforge.dev").first()
            
            if not admin_user:
                # Create admin user
                auth_service = AuthService()
                admin_user = auth_service.create_user(
                    email="admin@codeforge.dev",
                    username="admin",
                    password="admin123",  # Should be changed in production
                    role=UserRole.ADMIN
                )
                db.add(admin_user)
                db.commit()
                print("Created admin user: admin@codeforge.dev")
            
        except Exception as e:
            db.rollback()
            print(f"Error creating initial data: {e}")
        finally:
            db.close()
    
    @staticmethod
    def reset_db():
        """Reset database (for development/testing)"""
        drop_tables()
        create_tables()
        DatabaseManager.create_initial_data()