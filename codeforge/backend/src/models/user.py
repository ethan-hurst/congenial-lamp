"""
User and team models for CodeForge
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, String, Boolean, DateTime, JSON, Integer, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class User(Base):
    """User account model"""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    
    # Authentication
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    
    # Profile
    full_name = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    bio = Column(String, nullable=True)
    location = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # OAuth connections
    github_id = Column(String, unique=True, nullable=True, index=True)
    google_id = Column(String, unique=True, nullable=True, index=True)
    gitlab_id = Column(String, unique=True, nullable=True, index=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_student = Column(Boolean, default=False, nullable=False)
    is_nonprofit = Column(Boolean, default=False, nullable=False)
    
    # Subscription
    subscription_tier = Column(String, default="free", nullable=False)  # free, pro, team, enterprise
    subscription_expires = Column(DateTime, nullable=True)
    
    # Settings
    preferences = Column(JSON, default={}, nullable=False)
    editor_settings = Column(JSON, default={}, nullable=False)
    
    # Statistics
    projects_created = Column(Integer, default=0, nullable=False)
    contributions_count = Column(Integer, default=0, nullable=False)
    helpful_answers_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    credits = relationship("ComputeCredits", back_populates="user", uselist=False)
    projects = relationship("Project", back_populates="owner")
    teams = relationship("TeamMember", back_populates="user")
    resource_usage = relationship("ResourceUsage", back_populates="user")
    container_sessions = relationship("ContainerSession", back_populates="user")
    usage_alerts = relationship("UsageAlert", back_populates="user")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_email_active', 'email', 'is_active'),
        Index('idx_user_subscription', 'subscription_tier', 'is_active'),
    )


class Team(Base):
    """Team/Organization model"""
    __tablename__ = "teams"
    
    id = Column(String, primary_key=True)
    
    # Basic info
    name = Column(String, unique=True, nullable=False, index=True)
    slug = Column(String, unique=True, nullable=False, index=True)
    description = Column(String, nullable=True)
    avatar_url = Column(String, nullable=True)
    website = Column(String, nullable=True)
    
    # Billing
    billing_email = Column(String, nullable=False)
    subscription_tier = Column(String, default="team", nullable=False)
    subscription_seats = Column(Integer, default=5, nullable=False)
    
    # Settings
    settings = Column(JSON, default={}, nullable=False)
    
    # Features
    private_npm_enabled = Column(Boolean, default=False, nullable=False)
    sso_enabled = Column(Boolean, default=False, nullable=False)
    audit_log_enabled = Column(Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    members = relationship("TeamMember", back_populates="team")
    projects = relationship("Project", back_populates="team")
    credit_pool = relationship("TeamCreditPool", back_populates="team", uselist=False)


class TeamMember(Base):
    """Team membership model"""
    __tablename__ = "team_members"
    
    id = Column(String, primary_key=True)
    
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id"), nullable=False)
    
    # Role and permissions
    role = Column(String, nullable=False)  # owner, admin, member, viewer
    permissions = Column(JSON, default=[], nullable=False)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    invited_by = Column(String, ForeignKey("users.id"), nullable=True)
    
    # Timestamps
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="teams", foreign_keys=[user_id])
    team = relationship("Team", back_populates="members")
    
    # Indexes
    __table_args__ = (
        Index('idx_team_member', 'team_id', 'user_id', unique=True),
        Index('idx_member_user', 'user_id', 'is_active'),
    )