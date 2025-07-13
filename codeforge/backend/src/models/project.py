"""
Project and related models for CodeForge
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from enum import Enum

from ..database.connection import Base


class ProjectType(str, Enum):
    """Project template types"""
    REACT = "react"
    NEXT_JS = "nextjs"
    VUE = "vue"
    ANGULAR = "angular"
    SVELTE = "svelte"
    NODE_JS = "nodejs"
    EXPRESS = "express"
    FASTAPI = "fastapi"
    DJANGO = "django"
    FLASK = "flask"
    PYTHON = "python"
    JUPYTER = "jupyter"
    HTML_CSS_JS = "html"
    STATIC = "static"
    DOCKER = "docker"
    BLANK = "blank"


class ProjectVisibility(str, Enum):
    """Project visibility settings"""
    PRIVATE = "private"
    PUBLIC = "public"
    UNLISTED = "unlisted"


class Project(Base):
    """Project model"""
    __tablename__ = "projects"
    
    id = Column(String, primary_key=True)
    
    # Basic info
    name = Column(String, nullable=False, index=True)
    slug = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Project settings
    project_type = Column(String, nullable=False, default=ProjectType.BLANK)
    visibility = Column(String, nullable=False, default=ProjectVisibility.PRIVATE)
    language = Column(String, nullable=True)  # Primary language
    framework = Column(String, nullable=True)  # Framework used
    
    # Template info
    template_id = Column(String, nullable=True)
    forked_from = Column(String, ForeignKey("projects.id"), nullable=True)
    
    # Repository
    git_url = Column(String, nullable=True)
    git_branch = Column(String, default="main", nullable=False)
    git_provider = Column(String, nullable=True)  # github, gitlab, bitbucket
    
    # Container configuration
    container_image = Column(String, nullable=True)
    start_command = Column(String, nullable=True)
    install_command = Column(String, nullable=True)
    build_command = Column(String, nullable=True)
    dev_command = Column(String, nullable=True)
    
    # Environment
    environment_variables = Column(JSON, default={}, nullable=False)
    secrets = Column(JSON, default={}, nullable=False)  # Encrypted secrets
    packages = Column(JSON, default=[], nullable=False)  # Installed packages
    
    # Settings
    settings = Column(JSON, default={}, nullable=False)
    editor_config = Column(JSON, default={}, nullable=False)
    
    # Features
    is_featured = Column(Boolean, default=False, nullable=False)
    is_template = Column(Boolean, default=False, nullable=False)
    template_category = Column(String, nullable=True)
    
    # Statistics
    views_count = Column(Integer, default=0, nullable=False)
    forks_count = Column(Integer, default=0, nullable=False)
    stars_count = Column(Integer, default=0, nullable=False)
    runs_count = Column(Integer, default=0, nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_archived = Column(Boolean, default=False, nullable=False)
    last_activity = Column(DateTime, nullable=True)
    
    # Ownership
    owner_id = Column(String, ForeignKey("users.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    owner = relationship("User", back_populates="projects")
    team = relationship("Team", back_populates="projects")
    collaborators = relationship("ProjectCollaborator", back_populates="project")
    files = relationship("ProjectFile", back_populates="project")
    containers = relationship("ContainerSession", back_populates="project")
    deployments = relationship("Deployment", back_populates="project")
    snapshots = relationship("ProjectSnapshot", back_populates="project")
    
    # Indexes
    __table_args__ = (
        Index('idx_project_owner', 'owner_id', 'is_active'),
        Index('idx_project_type', 'project_type', 'visibility'),
        Index('idx_project_template', 'is_template', 'template_category'),
        Index('idx_project_slug_owner', 'slug', 'owner_id', unique=True),
    )


class ProjectCollaborator(Base):
    """Project collaboration model"""
    __tablename__ = "project_collaborators"
    
    id = Column(String, primary_key=True)
    
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Permissions
    role = Column(String, nullable=False)  # admin, write, read
    permissions = Column(JSON, default=[], nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    invited_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    added_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_access = Column(DateTime, nullable=True)
    
    # Relationships
    project = relationship("Project", back_populates="collaborators")
    user = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_collab_project_user', 'project_id', 'user_id', unique=True),
        Index('idx_collab_user', 'user_id', 'is_active'),
    )


class ProjectFile(Base):
    """Project file model"""
    __tablename__ = "project_files"
    
    id = Column(String, primary_key=True)
    
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # File info
    path = Column(String, nullable=False)  # Relative path from project root
    name = Column(String, nullable=False)
    content = Column(Text, nullable=True)  # File content (for small files)
    content_hash = Column(String, nullable=True)  # SHA256 hash of content
    
    # File metadata
    size_bytes = Column(Integer, default=0, nullable=False)
    mimetype = Column(String, nullable=True)
    encoding = Column(String, default="utf-8", nullable=False)
    
    # File type
    is_directory = Column(Boolean, default=False, nullable=False)
    is_binary = Column(Boolean, default=False, nullable=False)
    is_hidden = Column(Boolean, default=False, nullable=False)
    
    # Version control
    version = Column(Integer, default=1, nullable=False)
    parent_version = Column(String, ForeignKey("project_files.id"), nullable=True)
    
    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    updated_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="files")
    creator = relationship("User", foreign_keys=[created_by])
    updater = relationship("User", foreign_keys=[updated_by])
    
    # Indexes
    __table_args__ = (
        Index('idx_file_project_path', 'project_id', 'path', unique=True),
        Index('idx_file_project_name', 'project_id', 'name'),
        Index('idx_file_directory', 'project_id', 'is_directory'),
    )


class ProjectSnapshot(Base):
    """Project snapshot/backup model"""
    __tablename__ = "project_snapshots"
    
    id = Column(String, primary_key=True)
    
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    
    # Snapshot info
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Snapshot data
    files_archive_url = Column(String, nullable=False)  # S3/Storage URL
    environment_snapshot = Column(JSON, default={}, nullable=False)
    package_snapshot = Column(JSON, default={}, nullable=False)
    
    # Metadata
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    is_automatic = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="snapshots")
    creator = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_snapshot_project', 'project_id', 'created_at'),
        Index('idx_snapshot_user', 'created_by', 'created_at'),
    )


class ProjectTemplate(Base):
    """Project template model"""
    __tablename__ = "project_templates"
    
    id = Column(String, primary_key=True)
    
    # Template info
    name = Column(String, nullable=False, index=True)
    slug = Column(String, nullable=False, unique=True, index=True)
    description = Column(Text, nullable=False)
    
    # Template configuration
    project_type = Column(String, nullable=False)
    language = Column(String, nullable=False)
    framework = Column(String, nullable=True)
    category = Column(String, nullable=False)
    tags = Column(JSON, default=[], nullable=False)
    
    # Template files
    files_archive_url = Column(String, nullable=False)
    config = Column(JSON, default={}, nullable=False)
    
    # Display
    icon_url = Column(String, nullable=True)
    thumbnail_url = Column(String, nullable=True)
    demo_url = Column(String, nullable=True)
    
    # Features
    is_featured = Column(Boolean, default=False, nullable=False)
    is_official = Column(Boolean, default=False, nullable=False)
    difficulty_level = Column(String, default="beginner", nullable=False)  # beginner, intermediate, advanced
    
    # Statistics
    usage_count = Column(Integer, default=0, nullable=False)
    rating_average = Column(Integer, default=0, nullable=False)  # 0-5 stars
    rating_count = Column(Integer, default=0, nullable=False)
    
    # Ownership
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    creator = relationship("User")
    
    # Indexes
    __table_args__ = (
        Index('idx_template_category', 'category', 'is_active'),
        Index('idx_template_featured', 'is_featured', 'category'),
        Index('idx_template_official', 'is_official', 'is_active'),
    )