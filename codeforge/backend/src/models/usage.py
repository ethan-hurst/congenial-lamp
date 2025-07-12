"""
Resource usage tracking models for CodeForge
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey, Index, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class ResourceUsage(Base):
    """Aggregated resource usage for billing periods"""
    __tablename__ = "resource_usage"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Billing period
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=False)
    
    # Aggregated usage
    total_cpu_seconds = Column(Float, default=0.0, nullable=False)
    total_memory_gb_seconds = Column(Float, default=0.0, nullable=False)
    total_storage_gb_hours = Column(Float, default=0.0, nullable=False)
    total_bandwidth_gb = Column(Float, default=0.0, nullable=False)
    
    # GPU usage
    total_gpu_seconds = Column(Float, default=0.0, nullable=False)
    gpu_type = Column(String, nullable=True)
    
    # Credits consumed
    credits_consumed = Column(Integer, default=0, nullable=False)
    
    # Environment breakdown
    development_seconds = Column(Integer, default=0, nullable=False)
    staging_seconds = Column(Integer, default=0, nullable=False)
    production_seconds = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_updated = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="resource_usage")
    project = relationship("Project", back_populates="resource_usage")
    snapshots = relationship("UsageSnapshot", back_populates="resource_usage")
    
    # Indexes
    __table_args__ = (
        Index('idx_usage_user_period', 'user_id', 'period_start'),
        Index('idx_usage_project_period', 'project_id', 'period_start'),
    )


class UsageSnapshot(Base):
    """Real-time usage snapshots for monitoring"""
    __tablename__ = "usage_snapshots"
    
    id = Column(String, primary_key=True)
    session_id = Column(String, nullable=False, index=True)
    container_id = Column(String, nullable=False)
    resource_usage_id = Column(String, ForeignKey("resource_usage.id"), nullable=True)
    
    # Resource metrics at this moment
    cpu_percent = Column(Float, nullable=False)
    memory_mb = Column(Float, nullable=False)
    disk_read_mb = Column(Float, default=0.0, nullable=False)
    disk_write_mb = Column(Float, default=0.0, nullable=False)
    network_rx_mb = Column(Float, default=0.0, nullable=False)
    network_tx_mb = Column(Float, default=0.0, nullable=False)
    
    # GPU metrics (optional)
    gpu_percent = Column(Float, nullable=True)
    gpu_memory_mb = Column(Float, nullable=True)
    
    # State
    is_idle = Column(Boolean, default=False, nullable=False)
    
    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    resource_usage = relationship("ResourceUsage", back_populates="snapshots")
    
    # Indexes
    __table_args__ = (
        Index('idx_snapshot_session_time', 'session_id', 'timestamp'),
    )


class ContainerSession(Base):
    """Container execution sessions"""
    __tablename__ = "container_sessions"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False, index=True)
    
    # Container details
    container_id = Column(String, nullable=False, unique=True)
    environment_type = Column(String, nullable=False)  # development, staging, production
    image_name = Column(String, nullable=False)
    
    # Resource allocation
    cpu_limit = Column(Float, nullable=True)  # CPU cores
    memory_limit_mb = Column(Integer, nullable=True)
    gpu_type = Column(String, nullable=True)
    
    # Session lifecycle
    started_at = Column(DateTime, nullable=False, index=True)
    stopped_at = Column(DateTime, nullable=True)
    last_activity = Column(DateTime, nullable=False)
    
    # Auto-stop configuration
    idle_timeout_minutes = Column(Integer, default=5, nullable=False)
    auto_stop_enabled = Column(Boolean, default=True, nullable=False)
    
    # Credits
    estimated_credits_per_hour = Column(Integer, nullable=True)
    total_credits_consumed = Column(Integer, default=0, nullable=False)
    
    # State
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    termination_reason = Column(String, nullable=True)  # manual, idle_timeout, credit_exhausted
    
    # Metadata
    metadata = Column(JSON, nullable=True)  # Additional session info
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="container_sessions")
    project = relationship("Project", back_populates="container_sessions")
    
    # Indexes
    __table_args__ = (
        Index('idx_session_user_active', 'user_id', 'is_active'),
        Index('idx_session_project_active', 'project_id', 'is_active'),
    )


class UsageAlert(Base):
    """Alerts for usage thresholds and anomalies"""
    __tablename__ = "usage_alerts"
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    
    # Alert configuration
    alert_type = Column(String, nullable=False)  # credit_low, usage_spike, idle_resources
    threshold_value = Column(Float, nullable=False)
    comparison_operator = Column(String, nullable=False)  # gt, lt, eq
    
    # Alert state
    is_active = Column(Boolean, default=True, nullable=False)
    last_triggered = Column(DateTime, nullable=True)
    trigger_count = Column(Integer, default=0, nullable=False)
    
    # Notification preferences
    notify_email = Column(Boolean, default=True, nullable=False)
    notify_in_app = Column(Boolean, default=True, nullable=False)
    notify_webhook = Column(String, nullable=True)  # Webhook URL
    
    # Cooldown to prevent spam
    cooldown_minutes = Column(Integer, default=60, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="usage_alerts")