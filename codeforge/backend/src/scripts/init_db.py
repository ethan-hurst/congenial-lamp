#!/usr/bin/env python3
"""
Initialize CodeForge database for Replit deployment
"""
import os
import sys
import asyncio
from pathlib import Path
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.database.base import Base
from src.models import *  # Import all models to ensure they're registered
from src.database.connection import engine
from src.auth.security import get_password_hash

# Load environment variables
load_dotenv()

def create_database():
    """Create database if it doesn't exist"""
    db_url = os.getenv("DATABASE_URL", "postgresql://codeforge:codeforge@localhost:5432/codeforge_db")
    
    # Extract database name
    db_name = db_url.split("/")[-1].split("?")[0]
    
    # Connect to postgres database to create our database
    base_url = db_url.rsplit("/", 1)[0]
    temp_engine = create_engine(f"{base_url}/postgres")
    
    try:
        with temp_engine.connect() as conn:
            conn.execute(text("COMMIT"))  # Exit any transaction
            
            # Check if database exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": db_name}
            )
            
            if not result.fetchone():
                print(f"Creating database: {db_name}")
                conn.execute(text(f"CREATE DATABASE {db_name}"))
            else:
                print(f"Database {db_name} already exists")
                
    except Exception as e:
        print(f"Note: Could not create database (may already exist): {e}")
    finally:
        temp_engine.dispose()

def init_database():
    """Initialize database tables and create default data"""
    print("🗄️ Initializing CodeForge database...")
    
    # Create database
    create_database()
    
    # Create all tables
    print("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user
    from src.models.user import User
    
    with Session(engine) as session:
        # Check if admin exists
        admin = session.query(User).filter_by(email="admin@codeforge.dev").first()
        
        if not admin:
            print("Creating default admin user...")
            admin = User(
                email="admin@codeforge.dev",
                username="admin",
                full_name="CodeForge Admin",
                hashed_password=get_password_hash("admin123"),
                is_active=True,
                is_superuser=True,
                credits_balance=10000
            )
            session.add(admin)
            session.commit()
            print("✅ Admin user created:")
            print("   Email: admin@codeforge.dev")
            print("   Password: admin123")
            print("   ⚠️  Please change the password after first login!")
        else:
            print("Admin user already exists")
    
    print("✅ Database initialization complete!")

if __name__ == "__main__":
    init_database()