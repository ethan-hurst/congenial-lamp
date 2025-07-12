"""
Project model for CodeForge
"""
from datetime import datetime
from typing import Optional
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer, ForeignKey, Index, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Project(Base):
    """Project/Repository model"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    
    # Basic info
    name = Column(String, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Ownership
    owner_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True, index=True)
    
    # Visibility
    is_public = Column(Boolean, default=True, nullable=False, index=True)
    is_template = Column(Boolean, default=False, nullable=False)
    
    # Repository
    git_url = Column(String, nullable=True)
    default_branch = Column(String, default="main", nullable=False)
    
    # Runtime configuration
    language = Column(String, nullable=True)  # python, javascript, go, rust, etc.
    framework = Column(String, nullable=True)  # fastapi, express, django, etc.
    runtime_version = Column(String, nullable=True)  # python:3.11, node:20, etc.
    
    # Resources
    cpu_limit = Column(Integer, default=2, nullable=False)  # CPU cores
    memory_limit_mb = Column(Integer, default=2048, nullable=False)
    storage_limit_gb = Column(Integer, default=10, nullable=False)
    
    # Environment
    environment_variables = Column(JSON, default={}, nullable=False)
    secrets = Column(JSON, default={}, nullable=False)  # Encrypted
    
    # Features
    auto_deploy_enabled = Column(Boolean, default=False, nullable=False)
    time_travel_enabled = Column(Boolean, default=True, nullable=False)
    
    # Statistics
    stars_count = Column(Integer, default=0, nullable=False)
    forks_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed = Column(DateTime, nullable=True)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    team = relationship("Team", back_populates="projects")
    resource_usage = relationship("ResourceUsage", back_populates="project")
    container_sessions = relationship("ContainerSession", back_populates="project")
    
    # Indexes
    __table_args__ = (
        Index('idx_project_owner', 'owner_id', 'is_public'),
        Index('idx_project_team', 'team_id', 'is_public'),
        Index('idx_project_template', 'is_template', 'is_public'),
    )