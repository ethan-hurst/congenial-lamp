"""
Database provisioning and management models
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Enum, Text, JSON, Float
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum
from typing import Optional, Dict, Any

from ..database.connection import Base


class DBType(str, enum.Enum):
    """Database types supported"""
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    

class DBSize(str, enum.Enum):
    """Database instance sizes"""
    MICRO = "micro"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class DBStatus(str, enum.Enum):
    """Database instance status"""
    PROVISIONING = "provisioning"
    READY = "ready"
    UPDATING = "updating"
    DELETING = "deleting"
    ERROR = "error"
    SUSPENDED = "suspended"


class BackupType(str, enum.Enum):
    """Backup types"""
    FULL = "full"
    INCREMENTAL = "incremental"


class BackupStatus(str, enum.Enum):
    """Backup status"""
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RESTORING = "restoring"


class MergeStrategy(str, enum.Enum):
    """Branch merge strategies"""
    SCHEMA_ONLY = "schema_only"
    DATA_ONLY = "data_only"
    FULL = "full"


class MigrationStatus(str, enum.Enum):
    """Migration status"""
    PENDING = "pending"
    APPLIED = "applied"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DatabaseInstance(Base):
    """Database instance model"""
    __tablename__ = "database_instances"
    
    id = Column(String, primary_key=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    db_type = Column(Enum(DBType), nullable=False)
    version = Column(String, nullable=False)
    size = Column(Enum(DBSize), nullable=False)
    region = Column(String, nullable=False)
    status = Column(Enum(DBStatus), default=DBStatus.PROVISIONING)
    
    # Connection details (encrypted in production)
    host = Column(String)
    port = Column(Integer)
    database_name = Column(String)
    username = Column(String)
    password_encrypted = Column(String)  # Should be encrypted
    connection_pool_size = Column(Integer, default=20)
    
    # Resource tracking
    storage_gb = Column(Float, default=10.0)
    cpu_cores = Column(Float, default=1.0)
    memory_gb = Column(Float, default=1.0)
    iops = Column(Integer, default=3000)
    
    # Backup configuration
    backup_enabled = Column(Boolean, default=True)
    backup_retention_days = Column(Integer, default=7)
    backup_schedule = Column(String)  # Cron expression
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    created_by = Column(String, ForeignKey("users.id"))
    
    # Configuration
    config = Column(JSON, default={})
    tags = Column(JSON, default={})
    
    # Relationships
    project = relationship("Project", back_populates="databases")
    branches = relationship("DatabaseBranch", back_populates="instance", cascade="all, delete-orphan")
    backups = relationship("DatabaseBackup", back_populates="instance", cascade="all, delete-orphan")
    migrations = relationship("DatabaseMigration", back_populates="instance", cascade="all, delete-orphan")
    creator = relationship("User", foreign_keys=[created_by])


class DatabaseBranch(Base):
    """Database branch model"""
    __tablename__ = "database_branches"
    
    id = Column(String, primary_key=True)
    instance_id = Column(String, ForeignKey("database_instances.id"), nullable=False)
    name = Column(String, nullable=False)
    parent_branch = Column(String)  # Parent branch name
    is_default = Column(Boolean, default=False)
    
    # Branch metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(String, ForeignKey("users.id"))
    last_accessed = Column(DateTime(timezone=True))
    
    # Storage optimization
    use_cow = Column(Boolean, default=True)  # Copy-on-write
    storage_used_gb = Column(Float, default=0.0)
    delta_size_gb = Column(Float, default=0.0)  # Size difference from parent
    
    # Branch state
    is_locked = Column(Boolean, default=False)
    lock_reason = Column(String)
    schema_version = Column(Integer, default=1)
    data_hash = Column(String)  # Hash of data for comparison
    
    # Merge tracking
    merged_into = Column(String)  # Branch this was merged into
    merge_date = Column(DateTime(timezone=True))
    merge_conflicts = Column(JSON)
    
    # Relationships
    instance = relationship("DatabaseInstance", back_populates="branches")
    creator = relationship("User", foreign_keys=[created_by])
    migrations = relationship("DatabaseMigration", foreign_keys="DatabaseMigration.branch_id")


class DatabaseBackup(Base):
    """Database backup model"""
    __tablename__ = "database_backups"
    
    id = Column(String, primary_key=True)
    instance_id = Column(String, ForeignKey("database_instances.id"), nullable=False)
    branch_id = Column(String, ForeignKey("database_branches.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Backup details
    backup_type = Column(Enum(BackupType), nullable=False)
    status = Column(Enum(BackupStatus), default=BackupStatus.IN_PROGRESS)
    size_gb = Column(Float, default=0.0)
    compression_ratio = Column(Float, default=1.0)
    
    # Storage location
    storage_provider = Column(String, default="s3")  # s3, gcs, azure
    storage_path = Column(String)
    storage_region = Column(String)
    encryption_key_id = Column(String)
    
    # Timing
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    
    # Restore tracking
    restore_count = Column(Integer, default=0)
    last_restored_at = Column(DateTime(timezone=True))
    
    # Metadata
    schema_version = Column(Integer)
    database_version = Column(String)
    metadata = Column(JSON, default={})
    
    # Relationships
    instance = relationship("DatabaseInstance", back_populates="backups")
    branch = relationship("DatabaseBranch")
    

class DatabaseMigration(Base):
    """Database migration tracking model"""
    __tablename__ = "database_migrations"
    
    id = Column(String, primary_key=True)
    instance_id = Column(String, ForeignKey("database_instances.id"), nullable=False)
    branch_id = Column(String, ForeignKey("database_branches.id"), nullable=False)
    version = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text)
    
    # Migration content
    up_sql = Column(Text, nullable=False)
    down_sql = Column(Text)
    checksum = Column(String)  # Hash of migration content
    
    # Execution details
    status = Column(Enum(MigrationStatus), default=MigrationStatus.PENDING)
    applied_at = Column(DateTime(timezone=True))
    applied_by = Column(String, ForeignKey("users.id"))
    execution_time_ms = Column(Integer)
    
    # Error tracking
    error_message = Column(Text)
    error_details = Column(JSON)
    retry_count = Column(Integer, default=0)
    
    # Rollback info
    rolled_back_at = Column(DateTime(timezone=True))
    rolled_back_by = Column(String, ForeignKey("users.id"))
    rollback_reason = Column(Text)
    
    # Dependencies
    depends_on = Column(JSON, default=[])  # List of migration IDs
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    tags = Column(JSON, default={})
    
    # Relationships
    instance = relationship("DatabaseInstance", back_populates="migrations")
    branch = relationship("DatabaseBranch", foreign_keys=[branch_id])
    applier = relationship("User", foreign_keys=[applied_by])
    rollbacker = relationship("User", foreign_keys=[rolled_back_by])


class DatabaseMetrics(Base):
    """Database metrics and monitoring data"""
    __tablename__ = "database_metrics"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_id = Column(String, ForeignKey("database_instances.id"), nullable=False)
    branch_id = Column(String, ForeignKey("database_branches.id"))
    
    # Performance metrics
    queries_per_second = Column(Float)
    avg_query_time_ms = Column(Float)
    slow_queries_count = Column(Integer)
    active_connections = Column(Integer)
    
    # Resource usage
    cpu_usage_percent = Column(Float)
    memory_usage_percent = Column(Float)
    disk_usage_percent = Column(Float)
    disk_io_read_mbps = Column(Float)
    disk_io_write_mbps = Column(Float)
    
    # Database specific
    table_count = Column(Integer)
    total_rows = Column(Integer)
    database_size_gb = Column(Float)
    index_hit_ratio = Column(Float)
    cache_hit_ratio = Column(Float)
    
    # Replication metrics (if applicable)
    replication_lag_seconds = Column(Float)
    replication_status = Column(String)
    
    # Timestamp
    recorded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    instance = relationship("DatabaseInstance")
    branch = relationship("DatabaseBranch")