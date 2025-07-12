"""
Credit system data models for CodeForge
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, DateTime, JSON, Boolean, Enum as SQLEnum, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class CreditEarningType(str, Enum):
    """Types of activities that earn credits"""
    PR_MERGE = "pr_merge"
    HELPFUL_ANSWER = "helpful_answer"
    TEMPLATE_USE = "template_use"
    BUG_FIX = "bug_fix"
    REFERRAL = "referral"
    DOCUMENTATION = "documentation"
    CODE_REVIEW = "code_review"
    HACKATHON_WIN = "hackathon_win"


class ComputeCredits(Base):
    """User's credit balance and statistics"""
    __tablename__ = "compute_credits"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    
    # Current balance
    balance = Column(Integer, default=0, nullable=False)
    
    # Lifetime statistics
    lifetime_earned = Column(Integer, default=0, nullable=False)
    lifetime_spent = Column(Integer, default=0, nullable=False)
    lifetime_gifted_sent = Column(Integer, default=0, nullable=False)
    lifetime_gifted_received = Column(Integer, default=0, nullable=False)
    
    # Monthly allocation and rollover
    monthly_allocation = Column(Integer, default=100, nullable=False)
    rollover_credits = Column(Integer, default=0, nullable=False)
    last_rollover_date = Column(DateTime, nullable=True)
    
    # Team pool association (optional)
    team_pool_id = Column(String, ForeignKey("team_credit_pools.id"), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="credits")
    transactions = relationship("CreditTransaction", back_populates="user_credits")
    team_pool = relationship("TeamCreditPool", back_populates="members")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_credits_user_balance', 'user_id', 'balance'),
        Index('idx_credits_team_pool', 'team_pool_id'),
    )


class CreditTransaction(Base):
    """Audit trail for all credit transactions"""
    __tablename__ = "credit_transactions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Transaction details
    amount = Column(Integer, nullable=False)  # Positive for credit, negative for debit
    transaction_type = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    
    # Optional metadata
    metadata = Column(JSON, nullable=True)
    reference_id = Column(String, nullable=True, index=True)  # e.g., PR ID, session ID
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user_credits = relationship("ComputeCredits", back_populates="transactions")
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_transaction_user_date', 'user_id', 'created_at'),
        Index('idx_transaction_type_date', 'transaction_type', 'created_at'),
    )


class TeamCreditPool(Base):
    """Shared credit pool for teams/organizations"""
    __tablename__ = "team_credit_pools"
    
    id = Column(String, primary_key=True)
    team_id = Column(String, ForeignKey("teams.id"), unique=True, nullable=False)
    
    # Pool details
    balance = Column(Integer, default=0, nullable=False)
    monthly_allocation = Column(Integer, default=0, nullable=False)
    
    # Spending limits
    member_daily_limit = Column(Integer, nullable=True)  # Per member daily limit
    member_monthly_limit = Column(Integer, nullable=True)  # Per member monthly limit
    require_approval_above = Column(Integer, nullable=True)  # Require approval for large usage
    
    # Statistics
    total_contributed = Column(Integer, default=0, nullable=False)
    total_consumed = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    team = relationship("Team", back_populates="credit_pool")
    members = relationship("ComputeCredits", back_populates="team_pool")
    
    
class CreditPrice(Base):
    """Dynamic pricing for credits based on volume"""
    __tablename__ = "credit_prices"
    
    id = Column(String, primary_key=True)
    
    # Pricing tiers
    min_quantity = Column(Integer, nullable=False, unique=True)
    max_quantity = Column(Integer, nullable=True)
    price_per_credit_cents = Column(Integer, nullable=False)  # Price in cents (USD)
    
    # Discounts
    discount_percentage = Column(Integer, default=0, nullable=False)
    
    # Special pricing
    is_student_pricing = Column(Boolean, default=False, nullable=False)
    is_nonprofit_pricing = Column(Boolean, default=False, nullable=False)
    
    # Active status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index('idx_price_quantity', 'min_quantity', 'is_active'),
    )