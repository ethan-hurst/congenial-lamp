"""
Database provisioning and management API endpoints
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import datetime

from ...database.connection import get_database_session
from ...auth.dependencies import get_current_user
from ...models.user import User
from ...models.database import (
    DBType, DBSize, DBStatus, BackupType, BackupStatus, 
    MergeStrategy, MigrationStatus
)
from ...services.database import (
    DatabaseProvisioner, DatabaseBranching, 
    DatabaseBackup, MigrationManager
)


router = APIRouter(prefix="/databases", tags=["databases"])


# Request/Response Models
class DatabaseProvisionRequest(BaseModel):
    """Request model for database provisioning"""
    name: str = Field(..., min_length=1, max_length=100)
    type: DBType
    version: str
    size: DBSize
    region: str = "us-east-1"


class DatabaseInstanceResponse(BaseModel):
    """Response model for database instance"""
    id: str
    project_id: str
    name: str
    db_type: DBType
    version: str
    size: DBSize
    region: str
    status: DBStatus
    host: Optional[str]
    port: Optional[int]
    database_name: str
    username: str
    connection_string: Optional[str]
    created_at: datetime
    backup_enabled: bool
    backup_schedule: Optional[str]
    
    class Config:
        from_attributes = True


class BranchCreateRequest(BaseModel):
    """Request model for branch creation"""
    source_branch: str
    new_branch: str
    use_cow: bool = True


class BranchResponse(BaseModel):
    """Response model for database branch"""
    id: str
    instance_id: str
    name: str
    parent_branch: Optional[str]
    is_default: bool
    created_at: datetime
    created_by: str
    use_cow: bool
    storage_used_gb: float
    schema_version: int
    
    class Config:
        from_attributes = True


class BackupCreateRequest(BaseModel):
    """Request model for backup creation"""
    branch: str
    backup_type: BackupType = BackupType.FULL
    name: Optional[str]
    description: Optional[str]


class BackupResponse(BaseModel):
    """Response model for database backup"""
    id: str
    instance_id: str
    branch_id: str
    name: str
    description: Optional[str]
    backup_type: BackupType
    status: BackupStatus
    size_gb: float
    started_at: datetime
    completed_at: Optional[datetime]
    expires_at: datetime
    
    class Config:
        from_attributes = True


class MigrationApplyRequest(BaseModel):
    """Request model for applying migration"""
    branch: str
    migration_file: str


class MigrationResponse(BaseModel):
    """Response model for database migration"""
    id: str
    version: int
    name: str
    description: Optional[str]
    status: MigrationStatus
    applied_at: Optional[datetime]
    applied_by: Optional[str]
    execution_time_ms: Optional[int]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class MergeBranchRequest(BaseModel):
    """Request model for branch merge"""
    source_branch: str
    target_branch: str
    strategy: MergeStrategy = MergeStrategy.FULL


class ConnectionStringResponse(BaseModel):
    """Response model for connection string"""
    connection_string: str
    branch: str


# Initialize services
provisioner = DatabaseProvisioner()
branching = DatabaseBranching()
backup_service = DatabaseBackup()
migration_manager = MigrationManager()


# Database provisioning endpoints
@router.post("", response_model=DatabaseInstanceResponse)
async def provision_database(
    project_id: str,
    request: DatabaseProvisionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Provision a new database instance
    """
    try:
        instance = await provisioner.provision_database(
            project_id=project_id,
            db_type=request.type,
            version=request.version,
            size=request.size,
            region=request.region,
            name=request.name,
            user_id=current_user.id,
            db=db
        )
        
        # Get connection string for response
        connection_string = await provisioner.get_connection_string(
            instance_id=instance.id,
            branch="main",
            user_id=current_user.id,
            db=db
        )
        
        response = DatabaseInstanceResponse(
            **instance.__dict__,
            connection_string=connection_string
        )
        
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=List[DatabaseInstanceResponse])
async def list_databases(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    List all databases for a project
    """
    try:
        databases = await provisioner.list_databases(
            project_id=project_id,
            user_id=current_user.id,
            db=db
        )
        
        return [
            DatabaseInstanceResponse(**db_inst.__dict__)
            for db_inst in databases
        ]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}/connection-string", response_model=ConnectionStringResponse)
async def get_connection_string(
    instance_id: str,
    branch: str = "main",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Get connection string for a database instance
    """
    try:
        connection_string = await provisioner.get_connection_string(
            instance_id=instance_id,
            branch=branch,
            user_id=current_user.id,
            db=db
        )
        
        return ConnectionStringResponse(
            connection_string=connection_string,
            branch=branch
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{instance_id}")
async def delete_database(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Delete a database instance
    """
    try:
        await provisioner.delete_database(
            instance_id=instance_id,
            user_id=current_user.id,
            db=db
        )
        
        return {"message": f"Database {instance_id} deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}/metrics")
async def get_database_metrics(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Get metrics for a database instance
    """
    try:
        metrics = await provisioner.get_database_metrics(
            instance_id=instance_id,
            user_id=current_user.id,
            db=db
        )
        
        return metrics
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Branch management endpoints
@router.post("/{instance_id}/branches", response_model=BranchResponse)
async def create_branch(
    instance_id: str,
    request: BranchCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a new database branch
    """
    try:
        branch = await branching.create_branch(
            instance_id=instance_id,
            source_branch=request.source_branch,
            new_branch=request.new_branch,
            use_cow=request.use_cow,
            user_id=current_user.id,
            db=db
        )
        
        return BranchResponse(**branch.__dict__)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}/branches", response_model=List[BranchResponse])
async def list_branches(
    instance_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    List all branches for a database instance
    """
    try:
        branches = await branching.list_branches(
            instance_id=instance_id,
            user_id=current_user.id,
            db=db
        )
        
        return [
            BranchResponse(**branch.__dict__)
            for branch in branches
        ]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{instance_id}/branches/merge")
async def merge_branches(
    instance_id: str,
    request: MergeBranchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Merge one branch into another
    """
    try:
        result = await branching.merge_branch(
            instance_id=instance_id,
            source_branch=request.source_branch,
            target_branch=request.target_branch,
            strategy=request.strategy,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "success": result.success,
            "merged_changes": result.merged_changes,
            "conflicts": [
                {
                    "table": c.table,
                    "type": c.conflict_type,
                    "details": c.details
                }
                for c in result.conflicts
            ]
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{instance_id}/branches/{branch_name}")
async def delete_branch(
    instance_id: str,
    branch_name: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Delete a database branch
    """
    try:
        await branching.delete_branch(
            instance_id=instance_id,
            branch_name=branch_name,
            user_id=current_user.id,
            db=db
        )
        
        return {"message": f"Branch '{branch_name}' deleted successfully"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}/branches/diff")
async def get_branch_diff(
    instance_id: str,
    branch1: str,
    branch2: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Get differences between two branches
    """
    try:
        diff = await branching.get_branch_diff(
            instance_id=instance_id,
            branch1=branch1,
            branch2=branch2,
            user_id=current_user.id,
            db=db
        )
        
        return diff
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Backup management endpoints
@router.post("/{instance_id}/backup", response_model=BackupResponse)
async def create_backup(
    instance_id: str,
    request: BackupCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Create a database backup
    """
    try:
        backup = await backup_service.create_backup(
            instance_id=instance_id,
            branch=request.branch,
            backup_type=request.backup_type,
            name=request.name,
            description=request.description,
            user_id=current_user.id,
            db=db
        )
        
        return BackupResponse(**backup.__dict__)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}/backup", response_model=List[BackupResponse])
async def list_backups(
    instance_id: str,
    branch: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    List backups for a database instance
    """
    try:
        backups = await backup_service.list_backups(
            instance_id=instance_id,
            branch=branch,
            user_id=current_user.id,
            db=db
        )
        
        return [
            BackupResponse(**backup.__dict__)
            for backup in backups
        ]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{instance_id}/restore")
async def restore_backup(
    instance_id: str,
    backup_id: str,
    target_branch: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Restore a backup to a target branch
    """
    try:
        result = await backup_service.restore_backup(
            backup_id=backup_id,
            target_instance=instance_id,
            target_branch=target_branch,
            user_id=current_user.id,
            db=db
        )
        
        return {
            "success": result.success,
            "restored_to": result.restored_to,
            "duration_seconds": result.duration_seconds,
            "error": result.error
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{instance_id}/backup/schedule")
async def schedule_backups(
    instance_id: str,
    schedule: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Schedule automated backups for a database instance
    """
    try:
        await backup_service.schedule_backups(
            instance_id=instance_id,
            schedule=schedule,
            user_id=current_user.id,
            db=db
        )
        
        return {"message": f"Backup scheduled with cron: {schedule}"}
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Migration management endpoints
@router.post("/{instance_id}/migrations", response_model=MigrationResponse)
async def apply_migration(
    instance_id: str,
    request: MigrationApplyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Apply a migration to a database branch
    """
    try:
        result = await migration_manager.apply_migration(
            instance_id=instance_id,
            branch=request.branch,
            migration_file=request.migration_file,
            user_id=current_user.id,
            db=db
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        # Get the migration record
        from ...models.database import DatabaseMigration, DatabaseBranch
        
        branch_obj = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == request.branch
        ).first()
        
        migration = db.query(DatabaseMigration).filter(
            DatabaseMigration.instance_id == instance_id,
            DatabaseMigration.branch_id == branch_obj.id,
            DatabaseMigration.version == result.version
        ).first()
        
        return MigrationResponse(**migration.__dict__)
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{instance_id}/migrations/upload")
async def upload_migration(
    instance_id: str,
    branch: str,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Upload and apply a migration file
    """
    try:
        # Read file content
        content = await file.read()
        migration_content = content.decode('utf-8')
        
        # Apply migration
        result = await migration_manager.apply_migration(
            instance_id=instance_id,
            branch=branch,
            migration_file=migration_content,
            user_id=current_user.id,
            db=db
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return {
            "success": True,
            "version": result.version,
            "execution_time_ms": result.execution_time_ms
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{instance_id}/migrations", response_model=List[MigrationResponse])
async def get_migration_history(
    instance_id: str,
    branch: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Get migration history for a branch
    """
    try:
        migrations = await migration_manager.get_migration_history(
            instance_id=instance_id,
            branch=branch,
            user_id=current_user.id,
            db=db
        )
        
        return [
            MigrationResponse(**migration.__dict__)
            for migration in migrations
        ]
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{instance_id}/migrations/{version}/rollback")
async def rollback_migration(
    instance_id: str,
    version: int,
    branch: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """
    Rollback a migration
    """
    try:
        result = await migration_manager.rollback_migration(
            instance_id=instance_id,
            branch=branch,
            version=version,
            reason=reason,
            user_id=current_user.id,
            db=db
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error)
        
        return {
            "success": True,
            "version": result.version,
            "execution_time_ms": result.execution_time_ms
        }
        
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))