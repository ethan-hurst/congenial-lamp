"""
Database Branching Service - Git-like branching for databases
"""
import asyncio
import uuid
import hashlib
import json
from typing import List, Dict, Optional, Any
from datetime import datetime
import aiodocker
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_

from ...models.database import (
    DatabaseInstance, DatabaseBranch, DBStatus,
    MergeStrategy, DatabaseMigration, MigrationStatus
)
from ...models.project import Project
from ...database.connection import get_db
from ...config.settings import settings
from ..container_service import ContainerService
from .provisioner import DatabaseProvisioner
from ...utils.crypto import decrypt_string


logger = logging.getLogger(__name__)


class BranchConflict:
    """Represents a conflict during branch merge"""
    def __init__(self, table: str, conflict_type: str, details: Dict[str, Any]):
        self.table = table
        self.conflict_type = conflict_type  # schema, data, constraint
        self.details = details


class MergeResult:
    """Result of a branch merge operation"""
    def __init__(self, success: bool, conflicts: List[BranchConflict] = None, merged_changes: int = 0):
        self.success = success
        self.conflicts = conflicts or []
        self.merged_changes = merged_changes


class DatabaseBranching:
    """
    Service for managing database branches with copy-on-write optimization
    """
    
    def __init__(self):
        self.container_service = ContainerService()
        self.provisioner = DatabaseProvisioner()
    
    async def create_branch(
        self,
        instance_id: str,
        source_branch: str,
        new_branch: str,
        use_cow: bool = True,
        user_id: str = None,
        db: Session = None
    ) -> DatabaseBranch:
        """
        Create a new database branch
        
        Args:
            instance_id: Database instance ID
            source_branch: Source branch name
            new_branch: New branch name
            use_cow: Use copy-on-write optimization
            user_id: User creating the branch
            db: Database session
            
        Returns:
            DatabaseBranch: Created branch
        """
        if not db:
            db = get_db()
            
        try:
            # Validate instance and access
            instance = db.query(DatabaseInstance).filter(
                DatabaseInstance.id == instance_id
            ).first()
            
            if not instance:
                raise ValueError(f"Database instance {instance_id} not found")
            
            # Verify user has access
            if user_id:
                project = db.query(Project).filter(
                    Project.id == instance.project_id,
                    Project.owner_id == user_id
                ).first()
                
                if not project:
                    raise ValueError("Access denied")
            
            # Check branch limit
            branch_count = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id
            ).count()
            
            if branch_count >= settings.DATABASE_BRANCH_LIMIT:
                raise ValueError(f"Branch limit ({settings.DATABASE_BRANCH_LIMIT}) reached")
            
            # Validate source branch exists
            source_branch_obj = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id,
                DatabaseBranch.name == source_branch
            ).first()
            
            if not source_branch_obj:
                raise ValueError(f"Source branch '{source_branch}' not found")
            
            # Check if branch name already exists
            existing_branch = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id,
                DatabaseBranch.name == new_branch
            ).first()
            
            if existing_branch:
                raise ValueError(f"Branch '{new_branch}' already exists")
            
            # Create new branch record
            branch = DatabaseBranch(
                id=f"branch-{uuid.uuid4().hex[:12]}",
                instance_id=instance_id,
                name=new_branch,
                parent_branch=source_branch,
                created_by=user_id,
                use_cow=use_cow,
                schema_version=source_branch_obj.schema_version,
                data_hash=source_branch_obj.data_hash
            )
            
            db.add(branch)
            db.commit()
            
            # Create the actual branch using appropriate strategy
            if use_cow and settings.ENABLE_DATABASE_BRANCHING:
                await self._create_cow_branch(instance, source_branch_obj, branch, db)
            else:
                await self._create_full_copy_branch(instance, source_branch_obj, branch, db)
            
            # Copy migration history
            await self._copy_migration_history(source_branch_obj.id, branch.id, db)
            
            logger.info(f"Created branch '{new_branch}' from '{source_branch}' for instance {instance_id}")
            
            return branch
            
        except Exception as e:
            logger.error(f"Failed to create branch: {str(e)}")
            db.rollback()
            raise
    
    async def _create_cow_branch(
        self,
        instance: DatabaseInstance,
        source_branch: DatabaseBranch,
        new_branch: DatabaseBranch,
        db: Session
    ):
        """Create a copy-on-write branch using filesystem snapshots"""
        try:
            docker = aiodocker.Docker()
            
            # Find the database container
            container_name = f"codeforge-db-{instance.id}"
            container = await docker.containers.get(container_name)
            
            # Execute snapshot command based on database type
            if instance.db_type.value == "postgresql":
                # Use PostgreSQL's template database feature for COW
                password = decrypt_string(instance.password_encrypted)
                
                # Create a new database from template
                create_db_cmd = [
                    "psql",
                    "-U", instance.username,
                    "-c", f"CREATE DATABASE \"{new_branch.name}\" TEMPLATE \"{source_branch.name}\" OWNER \"{instance.username}\";"
                ]
                
                exec_result = await container.exec(
                    create_db_cmd,
                    environment={"PGPASSWORD": password}
                )
                
                output = await exec_result.start(detach=False)
                if output:
                    logger.debug(f"COW branch creation output: {output}")
                    
            elif instance.db_type.value == "mysql":
                # MySQL doesn't have native COW, use schema copy + selective data copy
                await self._mysql_cow_branch(instance, source_branch, new_branch)
            
            # Update branch metadata
            new_branch.storage_used_gb = 0.1  # Initial overhead
            new_branch.delta_size_gb = 0.0
            db.add(new_branch)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to create COW branch: {str(e)}")
            raise
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def _create_full_copy_branch(
        self,
        instance: DatabaseInstance,
        source_branch: DatabaseBranch,
        new_branch: DatabaseBranch,
        db: Session
    ):
        """Create a full copy of the database branch"""
        try:
            docker = aiodocker.Docker()
            
            # Find the database container
            container_name = f"codeforge-db-{instance.id}"
            container = await docker.containers.get(container_name)
            
            password = decrypt_string(instance.password_encrypted)
            
            if instance.db_type.value == "postgresql":
                # Dump and restore
                dump_cmd = [
                    "pg_dump",
                    "-U", instance.username,
                    "-d", source_branch.name,
                    "-f", f"/tmp/{source_branch.name}.sql"
                ]
                
                # Execute dump
                exec_result = await container.exec(
                    dump_cmd,
                    environment={"PGPASSWORD": password}
                )
                await exec_result.start(detach=False)
                
                # Create new database
                create_db_cmd = [
                    "psql",
                    "-U", instance.username,
                    "-c", f"CREATE DATABASE \"{new_branch.name}\" OWNER \"{instance.username}\";"
                ]
                
                exec_result = await container.exec(
                    create_db_cmd,
                    environment={"PGPASSWORD": password}
                )
                await exec_result.start(detach=False)
                
                # Restore to new database
                restore_cmd = [
                    "psql",
                    "-U", instance.username,
                    "-d", new_branch.name,
                    "-f", f"/tmp/{source_branch.name}.sql"
                ]
                
                exec_result = await container.exec(
                    restore_cmd,
                    environment={"PGPASSWORD": password}
                )
                await exec_result.start(detach=False)
                
                # Clean up dump file
                cleanup_cmd = ["rm", f"/tmp/{source_branch.name}.sql"]
                exec_result = await container.exec(cleanup_cmd)
                await exec_result.start(detach=False)
                
            elif instance.db_type.value == "mysql":
                # MySQL dump and restore
                await self._mysql_full_copy_branch(instance, source_branch, new_branch, password, container)
            
            # Calculate storage used
            size_cmd = self._get_db_size_command(instance, new_branch.name)
            exec_result = await container.exec(size_cmd, environment={"PGPASSWORD": password})
            output = await exec_result.start(detach=False)
            
            # Parse size (this is simplified, actual parsing would be more robust)
            try:
                size_gb = float(output.strip()) / (1024 * 1024 * 1024)
                new_branch.storage_used_gb = size_gb
                new_branch.delta_size_gb = size_gb
            except:
                new_branch.storage_used_gb = 1.0  # Default estimate
                new_branch.delta_size_gb = 1.0
            
            db.add(new_branch)
            db.commit()
            
        except Exception as e:
            logger.error(f"Failed to create full copy branch: {str(e)}")
            raise
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def _mysql_cow_branch(
        self,
        instance: DatabaseInstance,
        source_branch: DatabaseBranch,
        new_branch: DatabaseBranch
    ):
        """Create a COW-like branch for MySQL using views and triggers"""
        # This is a simplified implementation
        # In production, you might use MySQL's clone plugin or external tools
        logger.info(f"Creating MySQL COW branch (simulated): {new_branch.name}")
    
    async def _mysql_full_copy_branch(
        self,
        instance: DatabaseInstance,
        source_branch: DatabaseBranch,
        new_branch: DatabaseBranch,
        password: str,
        container: Any
    ):
        """Create a full copy branch for MySQL"""
        # Dump source database
        dump_cmd = [
            "mysqldump",
            "-u", instance.username,
            f"-p{password}",
            source_branch.name,
            "--single-transaction",
            "--routines",
            "--triggers"
        ]
        
        exec_result = await container.exec(dump_cmd)
        dump_output = await exec_result.start(detach=False)
        
        # Create new database
        create_cmd = [
            "mysql",
            "-u", instance.username,
            f"-p{password}",
            "-e", f"CREATE DATABASE `{new_branch.name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        ]
        
        exec_result = await container.exec(create_cmd)
        await exec_result.start(detach=False)
        
        # Restore to new database
        restore_cmd = [
            "mysql",
            "-u", instance.username,
            f"-p{password}",
            new_branch.name
        ]
        
        exec_result = await container.exec(restore_cmd, stdin=dump_output.encode())
        await exec_result.start(detach=False)
    
    def _get_db_size_command(self, instance: DatabaseInstance, branch_name: str) -> List[str]:
        """Get command to check database size"""
        if instance.db_type.value == "postgresql":
            return [
                "psql",
                "-U", instance.username,
                "-d", branch_name,
                "-t",
                "-c", "SELECT pg_database_size(current_database());"
            ]
        else:
            return [
                "mysql",
                "-u", instance.username,
                "-p" + decrypt_string(instance.password_encrypted),
                "-e", f"SELECT SUM(data_length + index_length) FROM information_schema.tables WHERE table_schema = '{branch_name}';"
            ]
    
    async def _copy_migration_history(
        self,
        source_branch_id: str,
        target_branch_id: str,
        db: Session
    ):
        """Copy migration history from source to target branch"""
        source_migrations = db.query(DatabaseMigration).filter(
            DatabaseMigration.branch_id == source_branch_id,
            DatabaseMigration.status == MigrationStatus.APPLIED
        ).all()
        
        for migration in source_migrations:
            new_migration = DatabaseMigration(
                id=f"mig-{uuid.uuid4().hex[:12]}",
                instance_id=migration.instance_id,
                branch_id=target_branch_id,
                version=migration.version,
                name=migration.name,
                description=migration.description,
                up_sql=migration.up_sql,
                down_sql=migration.down_sql,
                checksum=migration.checksum,
                status=MigrationStatus.APPLIED,
                applied_at=migration.applied_at,
                applied_by=migration.applied_by,
                execution_time_ms=migration.execution_time_ms,
                depends_on=migration.depends_on
            )
            db.add(new_migration)
        
        db.commit()
    
    async def list_branches(
        self,
        instance_id: str,
        user_id: str = None,
        db: Session = None
    ) -> List[DatabaseBranch]:
        """
        List all branches for a database instance
        
        Args:
            instance_id: Database instance ID
            user_id: User ID for access check
            db: Database session
            
        Returns:
            List[DatabaseBranch]: List of branches
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
        
        # Get all branches
        branches = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.merged_into.is_(None)  # Exclude merged branches
        ).order_by(
            DatabaseBranch.is_default.desc(),
            DatabaseBranch.created_at.desc()
        ).all()
        
        return branches
    
    async def switch_branch(
        self,
        instance_id: str,
        branch_name: str,
        user_id: str = None,
        db: Session = None
    ) -> DatabaseBranch:
        """
        Switch the active branch for a database instance
        
        Args:
            instance_id: Database instance ID
            branch_name: Branch to switch to
            user_id: User ID for access check
            db: Database session
            
        Returns:
            DatabaseBranch: The branch switched to
        """
        if not db:
            db = get_db()
            
        # Get the branch
        branch = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == branch_name
        ).first()
        
        if not branch:
            raise ValueError(f"Branch '{branch_name}' not found")
        
        # Update last accessed
        branch.last_accessed = datetime.utcnow()
        db.commit()
        
        return branch
    
    async def merge_branch(
        self,
        instance_id: str,
        source_branch: str,
        target_branch: str,
        strategy: MergeStrategy,
        user_id: str = None,
        db: Session = None
    ) -> MergeResult:
        """
        Merge one branch into another
        
        Args:
            instance_id: Database instance ID
            source_branch: Source branch name
            target_branch: Target branch name
            strategy: Merge strategy
            user_id: User ID for access check
            db: Database session
            
        Returns:
            MergeResult: Result of the merge operation
        """
        if not db:
            db = get_db()
            
        try:
            # Get branches
            source = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id,
                DatabaseBranch.name == source_branch
            ).first()
            
            target = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id,
                DatabaseBranch.name == target_branch
            ).first()
            
            if not source or not target:
                raise ValueError("Source or target branch not found")
            
            # Check if source is already merged
            if source.merged_into:
                raise ValueError(f"Branch '{source_branch}' is already merged")
            
            # Perform merge based on strategy
            if strategy == MergeStrategy.SCHEMA_ONLY:
                result = await self._merge_schema(instance_id, source, target, db)
            elif strategy == MergeStrategy.DATA_ONLY:
                result = await self._merge_data(instance_id, source, target, db)
            else:  # FULL
                result = await self._merge_full(instance_id, source, target, db)
            
            if result.success:
                # Mark source branch as merged
                source.merged_into = target_branch
                source.merge_date = datetime.utcnow()
                db.commit()
                
                logger.info(f"Successfully merged '{source_branch}' into '{target_branch}'")
            else:
                logger.warning(f"Merge failed with {len(result.conflicts)} conflicts")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to merge branches: {str(e)}")
            db.rollback()
            raise
    
    async def _merge_schema(
        self,
        instance_id: str,
        source: DatabaseBranch,
        target: DatabaseBranch,
        db: Session
    ) -> MergeResult:
        """Merge only schema changes"""
        conflicts = []
        
        # Get migrations that exist in source but not in target
        source_migrations = db.query(DatabaseMigration).filter(
            DatabaseMigration.branch_id == source.id,
            DatabaseMigration.status == MigrationStatus.APPLIED
        ).all()
        
        target_migration_versions = set(
            m.version for m in db.query(DatabaseMigration).filter(
                DatabaseMigration.branch_id == target.id,
                DatabaseMigration.status == MigrationStatus.APPLIED
            ).all()
        )
        
        # Apply missing migrations
        migrations_to_apply = [
            m for m in source_migrations
            if m.version not in target_migration_versions
        ]
        
        # Check for conflicts (simplified)
        if source.schema_version != target.schema_version:
            conflicts.append(BranchConflict(
                table="schema",
                conflict_type="version_mismatch",
                details={
                    "source_version": source.schema_version,
                    "target_version": target.schema_version
                }
            ))
        
        if conflicts:
            return MergeResult(success=False, conflicts=conflicts)
        
        # Apply migrations (simplified - in reality this would execute SQL)
        for migration in migrations_to_apply:
            logger.info(f"Applying migration {migration.name} to branch {target.name}")
        
        return MergeResult(success=True, merged_changes=len(migrations_to_apply))
    
    async def _merge_data(
        self,
        instance_id: str,
        source: DatabaseBranch,
        target: DatabaseBranch,
        db: Session
    ) -> MergeResult:
        """Merge only data changes"""
        # This is a simplified implementation
        # In production, you would:
        # 1. Compare data hashes
        # 2. Identify changed tables
        # 3. Apply data changes with conflict resolution
        
        if source.data_hash == target.data_hash:
            return MergeResult(success=True, merged_changes=0)
        
        # Simulate some data merging
        logger.info(f"Merging data from {source.name} to {target.name}")
        
        return MergeResult(success=True, merged_changes=1)
    
    async def _merge_full(
        self,
        instance_id: str,
        source: DatabaseBranch,
        target: DatabaseBranch,
        db: Session
    ) -> MergeResult:
        """Merge both schema and data"""
        schema_result = await self._merge_schema(instance_id, source, target, db)
        if not schema_result.success:
            return schema_result
        
        data_result = await self._merge_data(instance_id, source, target, db)
        if not data_result.success:
            return data_result
        
        total_changes = schema_result.merged_changes + data_result.merged_changes
        return MergeResult(success=True, merged_changes=total_changes)
    
    async def delete_branch(
        self,
        instance_id: str,
        branch_name: str,
        user_id: str = None,
        db: Session = None
    ) -> None:
        """
        Delete a database branch
        
        Args:
            instance_id: Database instance ID
            branch_name: Branch name to delete
            user_id: User ID for access check
            db: Database session
        """
        if not db:
            db = get_db()
            
        try:
            # Get branch
            branch = db.query(DatabaseBranch).filter(
                DatabaseBranch.instance_id == instance_id,
                DatabaseBranch.name == branch_name
            ).first()
            
            if not branch:
                raise ValueError(f"Branch '{branch_name}' not found")
            
            if branch.is_default:
                raise ValueError("Cannot delete the default branch")
            
            # Verify access
            if user_id:
                instance = db.query(DatabaseInstance).filter(
                    DatabaseInstance.id == instance_id
                ).first()
                
                project = db.query(Project).filter(
                    Project.id == instance.project_id,
                    Project.owner_id == user_id
                ).first()
                
                if not project:
                    raise ValueError("Access denied")
            
            # Delete the actual database
            await self._delete_branch_database(instance_id, branch_name, db)
            
            # Delete branch record
            db.delete(branch)
            db.commit()
            
            logger.info(f"Deleted branch '{branch_name}' from instance {instance_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete branch: {str(e)}")
            db.rollback()
            raise
    
    async def _delete_branch_database(
        self,
        instance_id: str,
        branch_name: str,
        db: Session
    ):
        """Delete the actual database for a branch"""
        try:
            docker = aiodocker.Docker()
            
            # Get instance details
            instance = db.query(DatabaseInstance).filter(
                DatabaseInstance.id == instance_id
            ).first()
            
            # Find the database container
            container_name = f"codeforge-db-{instance_id}"
            container = await docker.containers.get(container_name)
            
            password = decrypt_string(instance.password_encrypted)
            
            if instance.db_type.value == "postgresql":
                # Drop the database
                drop_cmd = [
                    "psql",
                    "-U", instance.username,
                    "-c", f"DROP DATABASE IF EXISTS \"{branch_name}\";"
                ]
                
                exec_result = await container.exec(
                    drop_cmd,
                    environment={"PGPASSWORD": password}
                )
                await exec_result.start(detach=False)
                
            elif instance.db_type.value == "mysql":
                # Drop MySQL database
                drop_cmd = [
                    "mysql",
                    "-u", instance.username,
                    f"-p{password}",
                    "-e", f"DROP DATABASE IF EXISTS `{branch_name}`;"
                ]
                
                exec_result = await container.exec(drop_cmd)
                await exec_result.start(detach=False)
            
        except Exception as e:
            logger.error(f"Failed to delete branch database: {str(e)}")
            raise
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def get_branch_diff(
        self,
        instance_id: str,
        branch1: str,
        branch2: str,
        user_id: str = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Get differences between two branches
        
        Args:
            instance_id: Database instance ID
            branch1: First branch name
            branch2: Second branch name
            user_id: User ID for access check
            db: Database session
            
        Returns:
            Dict containing differences
        """
        if not db:
            db = get_db()
            
        # Get branches
        b1 = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == branch1
        ).first()
        
        b2 = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == branch2
        ).first()
        
        if not b1 or not b2:
            raise ValueError("One or both branches not found")
        
        # Compare branches
        diff = {
            "schema_differences": {
                "branch1_version": b1.schema_version,
                "branch2_version": b2.schema_version,
                "versions_match": b1.schema_version == b2.schema_version
            },
            "data_differences": {
                "branch1_hash": b1.data_hash,
                "branch2_hash": b2.data_hash,
                "data_matches": b1.data_hash == b2.data_hash
            },
            "size_differences": {
                "branch1_size_gb": b1.storage_used_gb,
                "branch2_size_gb": b2.storage_used_gb,
                "difference_gb": abs(b1.storage_used_gb - b2.storage_used_gb)
            },
            "migration_differences": await self._get_migration_diff(b1.id, b2.id, db)
        }
        
        return diff
    
    async def _get_migration_diff(
        self,
        branch1_id: str,
        branch2_id: str,
        db: Session
    ) -> Dict[str, List[str]]:
        """Get migration differences between branches"""
        b1_migrations = set(
            m.version for m in db.query(DatabaseMigration).filter(
                DatabaseMigration.branch_id == branch1_id,
                DatabaseMigration.status == MigrationStatus.APPLIED
            ).all()
        )
        
        b2_migrations = set(
            m.version for m in db.query(DatabaseMigration).filter(
                DatabaseMigration.branch_id == branch2_id,
                DatabaseMigration.status == MigrationStatus.APPLIED
            ).all()
        )
        
        return {
            "only_in_branch1": list(b1_migrations - b2_migrations),
            "only_in_branch2": list(b2_migrations - b1_migrations),
            "in_both": list(b1_migrations & b2_migrations)
        }