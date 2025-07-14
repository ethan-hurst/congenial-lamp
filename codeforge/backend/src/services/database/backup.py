"""
Database Backup Service - Automated backup and restore functionality
"""
import asyncio
import uuid
import os
import gzip
import hashlib
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import aiodocker
import aioboto3
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_
from croniter import croniter
import aiofiles

from ...models.database import (
    DatabaseInstance, DatabaseBranch, DatabaseBackup,
    BackupType, BackupStatus, DBType
)
from ...models.project import Project
from ...database.connection import get_db
from ...config.settings import settings
from ...utils.crypto import decrypt_string, encrypt_string, generate_secure_token
from ..storage.storage_adapter import StorageAdapter


logger = logging.getLogger(__name__)


class BackupResult:
    """Result of a backup operation"""
    def __init__(self, success: bool, backup_id: str = None, size_gb: float = 0, error: str = None):
        self.success = success
        self.backup_id = backup_id
        self.size_gb = size_gb
        self.error = error


class RestoreResult:
    """Result of a restore operation"""
    def __init__(self, success: bool, restored_to: str = None, duration_seconds: int = 0, error: str = None):
        self.success = success
        self.restored_to = restored_to
        self.duration_seconds = duration_seconds
        self.error = error


class DatabaseBackupService:
    """
    Service for managing database backups and restores
    """
    
    def __init__(self):
        self.storage = StorageAdapter()
        self._backup_tasks = {}  # Track scheduled backup tasks
    
    async def create_backup(
        self,
        instance_id: str,
        branch: str,
        backup_type: BackupType,
        name: str = None,
        description: str = None,
        user_id: str = None,
        db: Session = None
    ) -> DatabaseBackup:
        """
        Create a database backup
        
        Args:
            instance_id: Database instance ID
            branch: Branch name to backup
            backup_type: Type of backup (full or incremental)
            name: Optional backup name
            description: Optional backup description
            user_id: User creating the backup
            db: Database session
            
        Returns:
            DatabaseBackup: Created backup record
        """
        if not db:
            db = get_db()
            
        try:
            # Get instance and branch
            instance = db.query(DatabaseInstance).filter(
                DatabaseInstance.id == instance_id
            ).first()
            
            if not instance:
                raise ValueError(f"Database instance {instance_id} not found")
            
            # Verify user access
            if user_id:
                project = db.query(Project).filter(
                    Project.id == instance.project_id,
                    Project.owner_id == user_id
                ).first()
                
                if not project:
                    raise ValueError("Access denied")
            
            # Get branch
            branch_obj = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id,
                DatabaseBranch.name == branch
            ).first()
            
            if not branch_obj:
                raise ValueError(f"Branch '{branch}' not found")
            
            # Generate backup ID and name
            backup_id = f"backup-{uuid.uuid4().hex[:12]}"
            if not name:
                name = f"{instance.name}-{branch}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
            
            # Calculate expiration date
            expires_at = datetime.utcnow() + timedelta(days=instance.backup_retention_days)
            
            # Create backup record
            backup = DatabaseBackup(
                id=backup_id,
                instance_id=instance_id,
                branch_id=branch_obj.id,
                name=name,
                description=description,
                backup_type=backup_type,
                status=BackupStatus.IN_PROGRESS,
                storage_provider=self._get_storage_provider(),
                storage_region=settings.AWS_REGION if settings.STORAGE_TYPE == "s3" else "local",
                expires_at=expires_at,
                schema_version=branch_obj.schema_version,
                database_version=instance.version
            )
            
            db.add(backup)
            db.commit()
            
            # Start backup process asynchronously
            asyncio.create_task(self._perform_backup(backup, instance, branch_obj, db))
            
            logger.info(f"Started backup {backup_id} for instance {instance_id} branch {branch}")
            
            return backup
            
        except Exception as e:
            logger.error(f"Failed to create backup: {str(e)}")
            db.rollback()
            raise
    
    def _get_storage_provider(self) -> str:
        """Get the storage provider based on configuration"""
        storage_type = settings.STORAGE_TYPE
        if storage_type == "s3":
            return "s3"
        elif storage_type == "gcs":
            return "gcs"
        elif storage_type == "azure":
            return "azure"
        else:
            return "local"
    
    async def _perform_backup(
        self,
        backup: DatabaseBackup,
        instance: DatabaseInstance,
        branch: DatabaseBranch,
        db: Session
    ):
        """Perform the actual backup operation"""
        start_time = datetime.utcnow()
        
        try:
            docker = aiodocker.Docker()
            
            # Find the database container
            container_name = f"codeforge-db-{instance.id}"
            container = await docker.containers.get(container_name)
            
            password = decrypt_string(instance.password_encrypted)
            
            # Create backup based on database type
            if instance.db_type == DBType.POSTGRESQL:
                backup_result = await self._backup_postgresql(
                    container, instance, branch, backup, password
                )
            elif instance.db_type == DBType.MYSQL:
                backup_result = await self._backup_mysql(
                    container, instance, branch, backup, password
                )
            else:
                raise ValueError(f"Unsupported database type: {instance.db_type}")
            
            if backup_result.success:
                # Update backup record
                backup.status = BackupStatus.COMPLETED
                backup.size_gb = backup_result.size_gb
                backup.completed_at = datetime.utcnow()
                backup.duration_seconds = int((backup.completed_at - start_time).total_seconds())
                backup.storage_path = backup_result.backup_id
                
                # Generate encryption key for this backup
                backup.encryption_key_id = generate_secure_token(16)
                
                db.add(backup)
                db.commit()
                
                logger.info(f"Backup {backup.id} completed successfully")
            else:
                raise Exception(backup_result.error)
                
        except Exception as e:
            logger.error(f"Backup {backup.id} failed: {str(e)}")
            backup.status = BackupStatus.FAILED
            db.add(backup)
            db.commit()
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def _backup_postgresql(
        self,
        container: Any,
        instance: DatabaseInstance,
        branch: DatabaseBranch,
        backup: DatabaseBackup,
        password: str
    ) -> BackupResult:
        """Backup PostgreSQL database"""
        try:
            # Generate backup filename
            backup_file = f"/tmp/{backup.id}.sql"
            compressed_file = f"{backup_file}.gz"
            
            # Create pg_dump command
            dump_cmd = [
                "pg_dump",
                "-U", instance.username,
                "-d", branch.name,
                "--clean",
                "--if-exists",
                "--no-owner",
                "--no-privileges",
                "-f", backup_file
            ]
            
            if backup.backup_type == BackupType.FULL:
                dump_cmd.extend(["--verbose", "--no-unlogged-table-data"])
            
            # Execute dump
            exec_result = await container.exec(
                dump_cmd,
                environment={"PGPASSWORD": password}
            )
            
            output = await exec_result.start(detach=False)
            
            # Compress the backup
            compress_cmd = ["gzip", "-9", backup_file]
            exec_result = await container.exec(compress_cmd)
            await exec_result.start(detach=False)
            
            # Get file size
            size_cmd = ["stat", "-c", "%s", compressed_file]
            exec_result = await container.exec(size_cmd)
            size_output = await exec_result.start(detach=False)
            size_bytes = int(size_output.strip())
            size_gb = size_bytes / (1024 * 1024 * 1024)
            
            # Read the compressed file
            read_cmd = ["cat", compressed_file]
            exec_result = await container.exec(read_cmd)
            backup_data = await exec_result.start(detach=False)
            
            # Upload to storage
            storage_path = f"backups/{instance.id}/{backup.id}.sql.gz"
            await self.storage.upload_file(
                file_data=backup_data.encode() if isinstance(backup_data, str) else backup_data,
                key=storage_path,
                metadata={
                    "instance_id": instance.id,
                    "branch": branch.name,
                    "backup_type": backup.backup_type.value,
                    "database_type": instance.db_type.value
                }
            )
            
            # Clean up temp files
            cleanup_cmd = ["rm", "-f", compressed_file]
            exec_result = await container.exec(cleanup_cmd)
            await exec_result.start(detach=False)
            
            return BackupResult(
                success=True,
                backup_id=storage_path,
                size_gb=size_gb
            )
            
        except Exception as e:
            logger.error(f"PostgreSQL backup failed: {str(e)}")
            return BackupResult(success=False, error=str(e))
    
    async def _backup_mysql(
        self,
        container: Any,
        instance: DatabaseInstance,
        branch: DatabaseBranch,
        backup: DatabaseBackup,
        password: str
    ) -> BackupResult:
        """Backup MySQL database"""
        try:
            # Generate backup filename
            backup_file = f"/tmp/{backup.id}.sql"
            compressed_file = f"{backup_file}.gz"
            
            # Create mysqldump command
            dump_cmd = [
                "mysqldump",
                "-u", instance.username,
                f"-p{password}",
                branch.name,
                "--single-transaction",
                "--routines",
                "--triggers",
                "--events"
            ]
            
            if backup.backup_type == BackupType.FULL:
                dump_cmd.extend(["--all-databases", "--flush-logs"])
            
            # Execute dump and compress in one step
            full_cmd = dump_cmd + ["|", "gzip", "-9", ">", compressed_file]
            exec_result = await container.exec(
                ["sh", "-c", " ".join(full_cmd)]
            )
            
            await exec_result.start(detach=False)
            
            # Get file size
            size_cmd = ["stat", "-c", "%s", compressed_file]
            exec_result = await container.exec(size_cmd)
            size_output = await exec_result.start(detach=False)
            size_bytes = int(size_output.strip())
            size_gb = size_bytes / (1024 * 1024 * 1024)
            
            # Read the compressed file
            read_cmd = ["cat", compressed_file]
            exec_result = await container.exec(read_cmd)
            backup_data = await exec_result.start(detach=False)
            
            # Upload to storage
            storage_path = f"backups/{instance.id}/{backup.id}.sql.gz"
            await self.storage.upload_file(
                file_data=backup_data.encode() if isinstance(backup_data, str) else backup_data,
                key=storage_path,
                metadata={
                    "instance_id": instance.id,
                    "branch": branch.name,
                    "backup_type": backup.backup_type.value,
                    "database_type": instance.db_type.value
                }
            )
            
            # Clean up temp files
            cleanup_cmd = ["rm", "-f", compressed_file]
            exec_result = await container.exec(cleanup_cmd)
            await exec_result.start(detach=False)
            
            return BackupResult(
                success=True,
                backup_id=storage_path,
                size_gb=size_gb
            )
            
        except Exception as e:
            logger.error(f"MySQL backup failed: {str(e)}")
            return BackupResult(success=False, error=str(e))
    
    async def restore_backup(
        self,
        backup_id: str,
        target_instance: str,
        target_branch: str,
        user_id: str = None,
        db: Session = None
    ) -> RestoreResult:
        """
        Restore a backup to a target instance and branch
        
        Args:
            backup_id: Backup ID to restore
            target_instance: Target instance ID
            target_branch: Target branch name
            user_id: User performing the restore
            db: Database session
            
        Returns:
            RestoreResult: Result of the restore operation
        """
        if not db:
            db = get_db()
            
        start_time = datetime.utcnow()
        
        try:
            # Get backup record
            backup = db.query(DatabaseBackup).filter(
                DatabaseBackup.id == backup_id
            ).first()
            
            if not backup:
                raise ValueError(f"Backup {backup_id} not found")
            
            if backup.status != BackupStatus.COMPLETED:
                raise ValueError(f"Backup is not in completed state")
            
            # Get target instance
            target_inst = db.query(DatabaseInstance).filter(
                DatabaseInstance.id == target_instance
            ).first()
            
            if not target_inst:
                raise ValueError(f"Target instance {target_instance} not found")
            
            # Verify user access
            if user_id:
                project = db.query(Project).filter(
                    Project.id == target_inst.project_id,
                    Project.owner_id == user_id
                ).first()
                
                if not project:
                    raise ValueError("Access denied")
            
            # Get target branch
            target_branch_obj = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == target_instance,
                DatabaseBranch.name == target_branch
            ).first()
            
            if not target_branch_obj:
                raise ValueError(f"Target branch '{target_branch}' not found")
            
            # Update backup status
            backup.status = BackupStatus.RESTORING
            db.commit()
            
            # Perform restore
            if target_inst.db_type == DBType.POSTGRESQL:
                result = await self._restore_postgresql(
                    backup, target_inst, target_branch_obj, db
                )
            elif target_inst.db_type == DBType.MYSQL:
                result = await self._restore_mysql(
                    backup, target_inst, target_branch_obj, db
                )
            else:
                raise ValueError(f"Unsupported database type: {target_inst.db_type}")
            
            if result.success:
                # Update backup record
                backup.status = BackupStatus.COMPLETED
                backup.restore_count += 1
                backup.last_restored_at = datetime.utcnow()
                db.commit()
                
                duration = int((datetime.utcnow() - start_time).total_seconds())
                
                logger.info(f"Backup {backup_id} restored successfully to {target_instance}/{target_branch}")
                
                return RestoreResult(
                    success=True,
                    restored_to=f"{target_instance}/{target_branch}",
                    duration_seconds=duration
                )
            else:
                raise Exception(result.error)
                
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            if 'backup' in locals() and backup:
                backup.status = BackupStatus.COMPLETED
                db.commit()
            return RestoreResult(success=False, error=str(e))
    
    async def _restore_postgresql(
        self,
        backup: DatabaseBackup,
        target_instance: DatabaseInstance,
        target_branch: DatabaseBranch,
        db: Session
    ) -> RestoreResult:
        """Restore PostgreSQL backup"""
        try:
            docker = aiodocker.Docker()
            
            # Find the database container
            container_name = f"codeforge-db-{target_instance.id}"
            container = await docker.containers.get(container_name)
            
            password = decrypt_string(target_instance.password_encrypted)
            
            # Download backup from storage
            backup_data = await self.storage.download_file(backup.storage_path)
            
            # Write backup to container
            backup_file = f"/tmp/restore-{backup.id}.sql.gz"
            
            # Create file in container
            create_cmd = ["sh", "-c", f"cat > {backup_file}"]
            exec_result = await container.exec(create_cmd, stdin=backup_data)
            await exec_result.start(detach=False)
            
            # Decompress backup
            decompress_cmd = ["gunzip", backup_file]
            exec_result = await container.exec(decompress_cmd)
            await exec_result.start(detach=False)
            
            # Drop existing connections to target database
            drop_conn_cmd = [
                "psql",
                "-U", target_instance.username,
                "-c", f"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '{target_branch.name}' AND pid <> pg_backend_pid();"
            ]
            
            exec_result = await container.exec(
                drop_conn_cmd,
                environment={"PGPASSWORD": password}
            )
            await exec_result.start(detach=False)
            
            # Restore the backup
            restore_file = backup_file.replace('.gz', '')
            restore_cmd = [
                "psql",
                "-U", target_instance.username,
                "-d", target_branch.name,
                "-f", restore_file
            ]
            
            exec_result = await container.exec(
                restore_cmd,
                environment={"PGPASSWORD": password}
            )
            
            output = await exec_result.start(detach=False)
            
            # Clean up temp files
            cleanup_cmd = ["rm", "-f", restore_file]
            exec_result = await container.exec(cleanup_cmd)
            await exec_result.start(detach=False)
            
            return RestoreResult(success=True)
            
        except Exception as e:
            logger.error(f"PostgreSQL restore failed: {str(e)}")
            return RestoreResult(success=False, error=str(e))
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def _restore_mysql(
        self,
        backup: DatabaseBackup,
        target_instance: DatabaseInstance,
        target_branch: DatabaseBranch,
        db: Session
    ) -> RestoreResult:
        """Restore MySQL backup"""
        try:
            docker = aiodocker.Docker()
            
            # Find the database container
            container_name = f"codeforge-db-{target_instance.id}"
            container = await docker.containers.get(container_name)
            
            password = decrypt_string(target_instance.password_encrypted)
            
            # Download backup from storage
            backup_data = await self.storage.download_file(backup.storage_path)
            
            # Write backup to container
            backup_file = f"/tmp/restore-{backup.id}.sql.gz"
            
            # Create file in container
            create_cmd = ["sh", "-c", f"cat > {backup_file}"]
            exec_result = await container.exec(create_cmd, stdin=backup_data)
            await exec_result.start(detach=False)
            
            # Restore the backup (decompress and restore in one step)
            restore_cmd = [
                "sh", "-c",
                f"gunzip -c {backup_file} | mysql -u {target_instance.username} -p{password} {target_branch.name}"
            ]
            
            exec_result = await container.exec(restore_cmd)
            output = await exec_result.start(detach=False)
            
            # Clean up temp files
            cleanup_cmd = ["rm", "-f", backup_file]
            exec_result = await container.exec(cleanup_cmd)
            await exec_result.start(detach=False)
            
            return RestoreResult(success=True)
            
        except Exception as e:
            logger.error(f"MySQL restore failed: {str(e)}")
            return RestoreResult(success=False, error=str(e))
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def schedule_backups(
        self,
        instance_id: str,
        schedule: str,
        user_id: str = None,
        db: Session = None
    ) -> None:
        """
        Schedule automated backups for a database instance
        
        Args:
            instance_id: Database instance ID
            schedule: Cron schedule expression
            user_id: User scheduling the backups
            db: Database session
        """
        if not db:
            db = get_db()
            
        try:
            # Validate cron expression
            if not croniter.is_valid(schedule):
                raise ValueError(f"Invalid cron expression: {schedule}")
            
            # Get instance
            instance = db.query(DatabaseInstance).filter(
                DatabaseInstance.id == instance_id
            ).first()
            
            if not instance:
                raise ValueError(f"Database instance {instance_id} not found")
            
            # Verify user access
            if user_id:
                project = db.query(Project).filter(
                    Project.id == instance.project_id,
                    Project.owner_id == user_id
                ).first()
                
                if not project:
                    raise ValueError("Access denied")
            
            # Update backup schedule
            instance.backup_schedule = schedule
            instance.backup_enabled = True
            db.commit()
            
            # Start or restart the backup scheduler
            await self._start_backup_scheduler(instance)
            
            logger.info(f"Scheduled backups for instance {instance_id} with schedule: {schedule}")
            
        except Exception as e:
            logger.error(f"Failed to schedule backups: {str(e)}")
            db.rollback()
            raise
    
    async def _start_backup_scheduler(self, instance: DatabaseInstance):
        """Start the backup scheduler for an instance"""
        # Cancel existing task if any
        if instance.id in self._backup_tasks:
            self._backup_tasks[instance.id].cancel()
        
        # Create new scheduler task
        task = asyncio.create_task(self._backup_scheduler_loop(instance))
        self._backup_tasks[instance.id] = task
    
    async def _backup_scheduler_loop(self, instance: DatabaseInstance):
        """Backup scheduler loop for an instance"""
        try:
            cron = croniter(instance.backup_schedule)
            
            while instance.backup_enabled:
                # Calculate next backup time
                next_backup = cron.get_next(datetime)
                wait_seconds = (next_backup - datetime.now()).total_seconds()
                
                if wait_seconds > 0:
                    await asyncio.sleep(wait_seconds)
                
                # Create backup
                try:
                    db = get_db()
                    
                    # Get default branch
                    default_branch = db.query(DatabaseBranch).filter(
                        DatabaseBranch.instance_id == instance.id,
                        DatabaseBranch.is_default == True
                    ).first()
                    
                    if default_branch:
                        await self.create_backup(
                            instance_id=instance.id,
                            branch=default_branch.name,
                            backup_type=BackupType.FULL,
                            name=f"scheduled-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
                            description="Automated scheduled backup",
                            db=db
                        )
                        
                except Exception as e:
                    logger.error(f"Scheduled backup failed for instance {instance.id}: {str(e)}")
                finally:
                    if 'db' in locals():
                        db.close()
                        
        except asyncio.CancelledError:
            logger.info(f"Backup scheduler stopped for instance {instance.id}")
        except Exception as e:
            logger.error(f"Backup scheduler error for instance {instance.id}: {str(e)}")
    
    async def list_backups(
        self,
        instance_id: str,
        branch: str = None,
        user_id: str = None,
        db: Session = None
    ) -> List[DatabaseBackup]:
        """
        List backups for a database instance
        
        Args:
            instance_id: Database instance ID
            branch: Optional branch name filter
            user_id: User ID for access check
            db: Database session
            
        Returns:
            List[DatabaseBackup]: List of backups
        """
        if not db:
            db = get_db()
            
        # Verify access
        if user_id:
            instance = db.query(DatabaseInstance).filter(
                DatabaseInstance.id == instance_id
            ).first()
            
            if not instance:
                raise ValueError(f"Database instance {instance_id} not found")
            
            project = db.query(Project).filter(
                Project.id == instance.project_id,
                Project.owner_id == user_id
            ).first()
            
            if not project:
                raise ValueError("Access denied")
        
        # Build query
        query = db.query(DatabaseBackup).filter(
            DatabaseBackup.instance_id == instance_id
        )
        
        if branch:
            branch_obj = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id,
                DatabaseBranch.name == branch
            ).first()
            
            if branch_obj:
                query = query.filter(DatabaseBackup.branch_id == branch_obj.id)
        
        # Get backups ordered by creation date
        backups = query.order_by(
            DatabaseBackup.started_at.desc()
        ).all()
        
        return backups
    
    async def delete_backup(
        self,
        backup_id: str,
        user_id: str = None,
        db: Session = None
    ) -> None:
        """
        Delete a backup
        
        Args:
            backup_id: Backup ID to delete
            user_id: User ID for access check
            db: Database session
        """
        if not db:
            db = get_db()
            
        try:
            # Get backup
            backup = db.query(DatabaseBackup).filter(
                DatabaseBackup.id == backup_id
            ).first()
            
            if not backup:
                raise ValueError(f"Backup {backup_id} not found")
            
            # Verify access
            if user_id:
                instance = db.query(DatabaseInstance).filter(
                    DatabaseInstance.id == backup.instance_id
                ).first()
                
                project = db.query(Project).filter(
                    Project.id == instance.project_id,
                    Project.owner_id == user_id
                ).first()
                
                if not project:
                    raise ValueError("Access denied")
            
            # Delete from storage
            if backup.storage_path:
                await self.storage.delete_file(backup.storage_path)
            
            # Delete record
            db.delete(backup)
            db.commit()
            
            logger.info(f"Deleted backup {backup_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete backup: {str(e)}")
            db.rollback()
            raise
    
    async def cleanup_expired_backups(self, db: Session = None):
        """Clean up expired backups"""
        if not db:
            db = get_db()
            
        try:
            # Find expired backups
            expired_backups = db.query(DatabaseBackup).filter(
                DatabaseBackup.expires_at < datetime.utcnow(),
                DatabaseBackup.status == BackupStatus.COMPLETED
            ).all()
            
            for backup in expired_backups:
                try:
                    await self.delete_backup(backup.id, db=db)
                except Exception as e:
                    logger.error(f"Failed to clean up backup {backup.id}: {str(e)}")
                    
            logger.info(f"Cleaned up {len(expired_backups)} expired backups")
            
        except Exception as e:
            logger.error(f"Failed to clean up expired backups: {str(e)}")


# Create service instance
DatabaseBackup = DatabaseBackupService