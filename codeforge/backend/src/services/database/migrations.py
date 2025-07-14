"""
Database Migration Manager - Schema version control and migration execution
"""
import asyncio
import uuid
import hashlib
import re
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime
import aiodocker
import logging
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import aiofiles
from pathlib import Path

from ...models.database import (
    DatabaseInstance, DatabaseBranch, DatabaseMigration,
    MigrationStatus, DBType
)
from ...models.project import Project
from ...database.connection import get_db
from ...config.settings import settings
from ...utils.crypto import decrypt_string
from ..storage.storage_adapter import StorageAdapter


logger = logging.getLogger(__name__)


class MigrationResult:
    """Result of a migration operation"""
    def __init__(self, success: bool, version: int = None, 
                 execution_time_ms: int = 0, error: str = None):
        self.success = success
        self.version = version
        self.execution_time_ms = execution_time_ms
        self.error = error


class MigrationConflict:
    """Represents a migration conflict"""
    def __init__(self, version: int, existing_checksum: str, 
                 new_checksum: str, description: str):
        self.version = version
        self.existing_checksum = existing_checksum
        self.new_checksum = new_checksum
        self.description = description


class MigrationManager:
    """
    Service for managing database migrations
    """
    
    def __init__(self):
        self.storage = StorageAdapter()
        self._migration_lock = asyncio.Lock()
    
    async def apply_migration(
        self,
        instance_id: str,
        branch: str,
        migration_file: str,
        user_id: str = None,
        db: Session = None
    ) -> MigrationResult:
        """
        Apply a migration to a database branch
        
        Args:
            instance_id: Database instance ID
            branch: Branch name
            migration_file: Path to migration file or migration content
            user_id: User applying the migration
            db: Database session
            
        Returns:
            MigrationResult: Result of the migration
        """
        if not db:
            db = get_db()
            
        async with self._migration_lock:
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
                
                # Parse migration file
                migration_data = await self._parse_migration(migration_file)
                
                # Check for existing migration with same version
                existing = db.query(DatabaseMigration).filter(
                    DatabaseMigration.instance_id == instance_id,
                    DatabaseMigration.branch_id == branch_obj.id,
                    DatabaseMigration.version == migration_data['version']
                ).first()
                
                if existing:
                    if existing.status == MigrationStatus.APPLIED:
                        # Check if it's the same migration
                        if existing.checksum == migration_data['checksum']:
                            logger.info(f"Migration {migration_data['version']} already applied")
                            return MigrationResult(
                                success=True,
                                version=migration_data['version'],
                                execution_time_ms=0
                            )
                        else:
                            raise ValueError(
                                f"Migration {migration_data['version']} already exists with different content"
                            )
                    elif existing.status == MigrationStatus.FAILED:
                        # Update existing failed migration
                        migration = existing
                        migration.retry_count += 1
                    else:
                        migration = existing
                else:
                    # Create new migration record
                    migration = DatabaseMigration(
                        id=f"mig-{uuid.uuid4().hex[:12]}",
                        instance_id=instance_id,
                        branch_id=branch_obj.id,
                        version=migration_data['version'],
                        name=migration_data['name'],
                        description=migration_data.get('description'),
                        up_sql=migration_data['up'],
                        down_sql=migration_data.get('down'),
                        checksum=migration_data['checksum'],
                        status=MigrationStatus.PENDING,
                        depends_on=migration_data.get('depends_on', [])
                    )
                    db.add(migration)
                
                db.commit()
                
                # Check dependencies
                if migration.depends_on:
                    missing_deps = await self._check_dependencies(
                        instance_id, branch_obj.id, migration.depends_on, db
                    )
                    
                    if missing_deps:
                        raise ValueError(
                            f"Missing dependencies: {', '.join(map(str, missing_deps))}"
                        )
                
                # Execute migration
                result = await self._execute_migration(
                    instance, branch_obj, migration, user_id, db
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to apply migration: {str(e)}")
                db.rollback()
                raise
    
    async def _parse_migration(self, migration_file: str) -> Dict[str, Any]:
        """Parse migration file or content"""
        content = migration_file
        
        # Check if it's a file path
        if '\n' not in migration_file and (
            migration_file.endswith('.sql') or 
            Path(migration_file).exists()
        ):
            async with aiofiles.open(migration_file, 'r') as f:
                content = await f.read()
        
        # Parse migration format
        # Expected format:
        # -- Migration Version: 001
        # -- Name: Create users table
        # -- Description: Initial users table
        # -- Depends-On: 
        # -- Up:
        # CREATE TABLE users (...);
        # -- Down:
        # DROP TABLE users;
        
        metadata = {}
        sections = {'up': [], 'down': []}
        current_section = None
        
        for line in content.splitlines():
            line = line.strip()
            
            # Parse metadata
            if line.startswith('-- Migration Version:'):
                metadata['version'] = int(line.split(':', 1)[1].strip())
            elif line.startswith('-- Name:'):
                metadata['name'] = line.split(':', 1)[1].strip()
            elif line.startswith('-- Description:'):
                metadata['description'] = line.split(':', 1)[1].strip()
            elif line.startswith('-- Depends-On:'):
                deps_str = line.split(':', 1)[1].strip()
                metadata['depends_on'] = [
                    int(d.strip()) for d in deps_str.split(',') if d.strip()
                ]
            elif line == '-- Up:':
                current_section = 'up'
            elif line == '-- Down:':
                current_section = 'down'
            elif current_section and not line.startswith('--'):
                sections[current_section].append(line)
        
        # Join sections
        metadata['up'] = '\n'.join(sections['up']).strip()
        metadata['down'] = '\n'.join(sections['down']).strip() if sections['down'] else None
        
        # Generate checksum
        metadata['checksum'] = hashlib.sha256(
            (metadata['up'] + (metadata.get('down') or '')).encode()
        ).hexdigest()
        
        # Validate required fields
        if 'version' not in metadata:
            raise ValueError("Migration version not specified")
        if 'name' not in metadata:
            raise ValueError("Migration name not specified")
        if not metadata['up']:
            raise ValueError("Migration up script is empty")
        
        return metadata
    
    async def _check_dependencies(
        self,
        instance_id: str,
        branch_id: str,
        dependencies: List[int],
        db: Session
    ) -> List[int]:
        """Check if all dependencies are applied"""
        applied_versions = set(
            m.version for m in db.query(DatabaseMigration).filter(
                DatabaseMigration.instance_id == instance_id,
                DatabaseMigration.branch_id == branch_id,
                DatabaseMigration.status == MigrationStatus.APPLIED
            ).all()
        )
        
        missing = [dep for dep in dependencies if dep not in applied_versions]
        return missing
    
    async def _execute_migration(
        self,
        instance: DatabaseInstance,
        branch: DatabaseBranch,
        migration: DatabaseMigration,
        user_id: str,
        db: Session
    ) -> MigrationResult:
        """Execute the migration SQL"""
        start_time = datetime.utcnow()
        
        try:
            docker = aiodocker.Docker()
            
            # Find the database container
            container_name = f"codeforge-db-{instance.id}"
            container = await docker.containers.get(container_name)
            
            password = decrypt_string(instance.password_encrypted)
            
            # Execute migration based on database type
            if instance.db_type == DBType.POSTGRESQL:
                result = await self._execute_postgresql_migration(
                    container, instance, branch, migration, password
                )
            elif instance.db_type == DBType.MYSQL:
                result = await self._execute_mysql_migration(
                    container, instance, branch, migration, password
                )
            else:
                raise ValueError(f"Unsupported database type: {instance.db_type}")
            
            if result.success:
                # Update migration record
                migration.status = MigrationStatus.APPLIED
                migration.applied_at = datetime.utcnow()
                migration.applied_by = user_id
                migration.execution_time_ms = int(
                    (migration.applied_at - start_time).total_seconds() * 1000
                )
                
                # Update branch schema version
                branch.schema_version = migration.version
                
                db.commit()
                
                logger.info(f"Successfully applied migration {migration.version} to {branch.name}")
                
                return MigrationResult(
                    success=True,
                    version=migration.version,
                    execution_time_ms=migration.execution_time_ms
                )
            else:
                raise Exception(result.error)
                
        except Exception as e:
            logger.error(f"Migration execution failed: {str(e)}")
            
            # Update migration record
            migration.status = MigrationStatus.FAILED
            migration.error_message = str(e)
            migration.error_details = {"timestamp": datetime.utcnow().isoformat()}
            db.commit()
            
            return MigrationResult(success=False, error=str(e))
            
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def _execute_postgresql_migration(
        self,
        container: Any,
        instance: DatabaseInstance,
        branch: DatabaseBranch,
        migration: DatabaseMigration,
        password: str
    ) -> MigrationResult:
        """Execute PostgreSQL migration"""
        try:
            # Write migration to temp file
            migration_file = f"/tmp/migration-{migration.id}.sql"
            
            # Create migration file
            create_cmd = ["sh", "-c", f"cat > {migration_file} << 'EOF'\n{migration.up_sql}\nEOF"]
            exec_result = await container.exec(create_cmd)
            await exec_result.start(detach=False)
            
            # Execute migration
            exec_cmd = [
                "psql",
                "-U", instance.username,
                "-d", branch.name,
                "-v", "ON_ERROR_STOP=1",
                "-f", migration_file
            ]
            
            exec_result = await container.exec(
                exec_cmd,
                environment={"PGPASSWORD": password}
            )
            
            output = await exec_result.start(detach=False)
            
            # Clean up
            cleanup_cmd = ["rm", "-f", migration_file]
            exec_result = await container.exec(cleanup_cmd)
            await exec_result.start(detach=False)
            
            # Check for errors in output
            if "ERROR:" in output:
                raise Exception(f"Migration failed: {output}")
            
            return MigrationResult(success=True)
            
        except Exception as e:
            logger.error(f"PostgreSQL migration failed: {str(e)}")
            return MigrationResult(success=False, error=str(e))
    
    async def _execute_mysql_migration(
        self,
        container: Any,
        instance: DatabaseInstance,
        branch: DatabaseBranch,
        migration: DatabaseMigration,
        password: str
    ) -> MigrationResult:
        """Execute MySQL migration"""
        try:
            # MySQL doesn't support transactions for DDL, so we need to be careful
            # Execute migration
            exec_cmd = [
                "mysql",
                "-u", instance.username,
                f"-p{password}",
                branch.name,
                "-e", migration.up_sql
            ]
            
            exec_result = await container.exec(exec_cmd)
            output = await exec_result.start(detach=False)
            
            # Check for errors
            if "ERROR" in output:
                raise Exception(f"Migration failed: {output}")
            
            return MigrationResult(success=True)
            
        except Exception as e:
            logger.error(f"MySQL migration failed: {str(e)}")
            return MigrationResult(success=False, error=str(e))
    
    async def rollback_migration(
        self,
        instance_id: str,
        branch: str,
        version: int,
        reason: str = None,
        user_id: str = None,
        db: Session = None
    ) -> MigrationResult:
        """
        Rollback a migration
        
        Args:
            instance_id: Database instance ID
            branch: Branch name
            version: Migration version to rollback
            reason: Reason for rollback
            user_id: User performing rollback
            db: Database session
            
        Returns:
            MigrationResult: Result of the rollback
        """
        if not db:
            db = get_db()
            
        async with self._migration_lock:
            try:
                # Get migration
                branch_obj = db.query(DatabaseBranch).filter(
                    DatabaseBranch.instance_id == instance_id,
                    DatabaseBranch.name == branch
                ).first()
                
                if not branch_obj:
                    raise ValueError(f"Branch '{branch}' not found")
                
                migration = db.query(DatabaseMigration).filter(
                    DatabaseMigration.instance_id == instance_id,
                    DatabaseMigration.branch_id == branch_obj.id,
                    DatabaseMigration.version == version
                ).first()
                
                if not migration:
                    raise ValueError(f"Migration version {version} not found")
                
                if migration.status != MigrationStatus.APPLIED:
                    raise ValueError(f"Migration {version} is not in applied state")
                
                if not migration.down_sql:
                    raise ValueError(f"Migration {version} does not have a rollback script")
                
                # Check if any later migrations depend on this one
                dependent_migrations = db.query(DatabaseMigration).filter(
                    DatabaseMigration.instance_id == instance_id,
                    DatabaseMigration.branch_id == branch_obj.id,
                    DatabaseMigration.status == MigrationStatus.APPLIED,
                    DatabaseMigration.version > version
                ).all()
                
                for dep in dependent_migrations:
                    if migration.version in (dep.depends_on or []):
                        raise ValueError(
                            f"Cannot rollback migration {version}: "
                            f"migration {dep.version} depends on it"
                        )
                
                # Get instance
                instance = db.query(DatabaseInstance).filter(
                    DatabaseInstance.id == instance_id
                ).first()
                
                # Execute rollback
                result = await self._execute_rollback(
                    instance, branch_obj, migration, user_id, reason, db
                )
                
                return result
                
            except Exception as e:
                logger.error(f"Failed to rollback migration: {str(e)}")
                db.rollback()
                raise
    
    async def _execute_rollback(
        self,
        instance: DatabaseInstance,
        branch: DatabaseBranch,
        migration: DatabaseMigration,
        user_id: str,
        reason: str,
        db: Session
    ) -> MigrationResult:
        """Execute migration rollback"""
        start_time = datetime.utcnow()
        
        try:
            docker = aiodocker.Docker()
            
            # Find the database container
            container_name = f"codeforge-db-{instance.id}"
            container = await docker.containers.get(container_name)
            
            password = decrypt_string(instance.password_encrypted)
            
            # Execute rollback based on database type
            if instance.db_type == DBType.POSTGRESQL:
                # Write rollback script to temp file
                rollback_file = f"/tmp/rollback-{migration.id}.sql"
                
                create_cmd = ["sh", "-c", f"cat > {rollback_file} << 'EOF'\n{migration.down_sql}\nEOF"]
                exec_result = await container.exec(create_cmd)
                await exec_result.start(detach=False)
                
                # Execute rollback
                exec_cmd = [
                    "psql",
                    "-U", instance.username,
                    "-d", branch.name,
                    "-v", "ON_ERROR_STOP=1",
                    "-f", rollback_file
                ]
                
                exec_result = await container.exec(
                    exec_cmd,
                    environment={"PGPASSWORD": password}
                )
                
                output = await exec_result.start(detach=False)
                
                # Clean up
                cleanup_cmd = ["rm", "-f", rollback_file]
                exec_result = await container.exec(cleanup_cmd)
                await exec_result.start(detach=False)
                
            elif instance.db_type == DBType.MYSQL:
                # Execute rollback for MySQL
                exec_cmd = [
                    "mysql",
                    "-u", instance.username,
                    f"-p{password}",
                    branch.name,
                    "-e", migration.down_sql
                ]
                
                exec_result = await container.exec(exec_cmd)
                output = await exec_result.start(detach=False)
            
            # Update migration record
            migration.status = MigrationStatus.ROLLED_BACK
            migration.rolled_back_at = datetime.utcnow()
            migration.rolled_back_by = user_id
            migration.rollback_reason = reason
            
            # Update branch schema version to previous
            prev_migration = db.query(DatabaseMigration).filter(
                DatabaseMigration.instance_id == instance.id,
                DatabaseMigration.branch_id == branch.id,
                DatabaseMigration.status == MigrationStatus.APPLIED,
                DatabaseMigration.version < migration.version
            ).order_by(DatabaseMigration.version.desc()).first()
            
            branch.schema_version = prev_migration.version if prev_migration else 0
            
            db.commit()
            
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            
            logger.info(f"Successfully rolled back migration {migration.version}")
            
            return MigrationResult(
                success=True,
                version=migration.version,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Rollback execution failed: {str(e)}")
            return MigrationResult(success=False, error=str(e))
        finally:
            if 'docker' in locals():
                await docker.close()
    
    async def get_migration_history(
        self,
        instance_id: str,
        branch: str,
        user_id: str = None,
        db: Session = None
    ) -> List[DatabaseMigration]:
        """
        Get migration history for a branch
        
        Args:
            instance_id: Database instance ID
            branch: Branch name
            user_id: User ID for access check
            db: Database session
            
        Returns:
            List[DatabaseMigration]: Migration history
        """
        if not db:
            db = get_db()
            
        # Get branch
        branch_obj = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == branch
        ).first()
        
        if not branch_obj:
            raise ValueError(f"Branch '{branch}' not found")
        
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
        
        # Get migrations ordered by version
        migrations = db.query(DatabaseMigration).filter(
            DatabaseMigration.instance_id == instance_id,
            DatabaseMigration.branch_id == branch_obj.id
        ).order_by(DatabaseMigration.version).all()
        
        return migrations
    
    async def validate_migration_sequence(
        self,
        instance_id: str,
        branch: str,
        migrations: List[str],
        db: Session = None
    ) -> Tuple[bool, List[MigrationConflict]]:
        """
        Validate a sequence of migrations
        
        Args:
            instance_id: Database instance ID
            branch: Branch name
            migrations: List of migration files/content
            db: Database session
            
        Returns:
            Tuple[bool, List[MigrationConflict]]: (is_valid, conflicts)
        """
        if not db:
            db = get_db()
            
        conflicts = []
        parsed_migrations = []
        
        # Parse all migrations
        for migration in migrations:
            try:
                parsed = await self._parse_migration(migration)
                parsed_migrations.append(parsed)
            except Exception as e:
                logger.error(f"Failed to parse migration: {str(e)}")
                conflicts.append(MigrationConflict(
                    version=0,
                    existing_checksum="",
                    new_checksum="",
                    description=f"Parse error: {str(e)}"
                ))
        
        if conflicts:
            return False, conflicts
        
        # Check for version conflicts and dependency issues
        version_map = {}
        for parsed in parsed_migrations:
            version = parsed['version']
            
            # Check for duplicate versions
            if version in version_map:
                conflicts.append(MigrationConflict(
                    version=version,
                    existing_checksum=version_map[version]['checksum'],
                    new_checksum=parsed['checksum'],
                    description="Duplicate version number"
                ))
            else:
                version_map[version] = parsed
        
        # Check dependencies
        for parsed in parsed_migrations:
            for dep in parsed.get('depends_on', []):
                if dep not in version_map and dep not in await self._get_applied_versions(
                    instance_id, branch, db
                ):
                    conflicts.append(MigrationConflict(
                        version=parsed['version'],
                        existing_checksum="",
                        new_checksum=parsed['checksum'],
                        description=f"Missing dependency: {dep}"
                    ))
        
        # Check against existing migrations
        branch_obj = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == branch
        ).first()
        
        if branch_obj:
            existing_migrations = db.query(DatabaseMigration).filter(
                DatabaseMigration.instance_id == instance_id,
                DatabaseMigration.branch_id == branch_obj.id
            ).all()
            
            existing_map = {m.version: m for m in existing_migrations}
            
            for parsed in parsed_migrations:
                version = parsed['version']
                if version in existing_map:
                    existing = existing_map[version]
                    if existing.checksum != parsed['checksum']:
                        conflicts.append(MigrationConflict(
                            version=version,
                            existing_checksum=existing.checksum,
                            new_checksum=parsed['checksum'],
                            description="Migration content changed"
                        ))
        
        return len(conflicts) == 0, conflicts
    
    async def _get_applied_versions(
        self,
        instance_id: str,
        branch: str,
        db: Session
    ) -> List[int]:
        """Get list of applied migration versions"""
        branch_obj = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == branch
        ).first()
        
        if not branch_obj:
            return []
        
        versions = [
            m.version for m in db.query(DatabaseMigration).filter(
                DatabaseMigration.instance_id == instance_id,
                DatabaseMigration.branch_id == branch_obj.id,
                DatabaseMigration.status == MigrationStatus.APPLIED
            ).all()
        ]
        
        return versions
    
    async def generate_migration(
        self,
        instance_id: str,
        branch: str,
        name: str,
        changes: Dict[str, Any],
        user_id: str = None,
        db: Session = None
    ) -> str:
        """
        Generate a migration based on schema changes
        
        Args:
            instance_id: Database instance ID
            branch: Branch name
            name: Migration name
            changes: Dictionary of schema changes
            user_id: User generating migration
            db: Database session
            
        Returns:
            str: Generated migration content
        """
        if not db:
            db = get_db()
            
        # Get instance details
        instance = db.query(DatabaseInstance).filter(
            DatabaseInstance.id == instance_id
        ).first()
        
        if not instance:
            raise ValueError(f"Database instance {instance_id} not found")
        
        # Get next version number
        branch_obj = db.query(DatabaseBranch).filter(
            DatabaseBranch.instance_id == instance_id,
            DatabaseBranch.name == branch
        ).first()
        
        if branch_obj:
            max_version = db.query(DatabaseMigration).filter(
                DatabaseMigration.instance_id == instance_id,
                DatabaseMigration.branch_id == branch_obj.id
            ).count()
            next_version = max_version + 1
        else:
            next_version = 1
        
        # Generate migration based on database type
        if instance.db_type == DBType.POSTGRESQL:
            up_sql, down_sql = self._generate_postgresql_migration(changes)
        elif instance.db_type == DBType.MYSQL:
            up_sql, down_sql = self._generate_mysql_migration(changes)
        else:
            raise ValueError(f"Unsupported database type: {instance.db_type}")
        
        # Format migration file
        migration_content = f"""-- Migration Version: {next_version:03d}
-- Name: {name}
-- Description: Auto-generated migration
-- Depends-On: {branch_obj.schema_version if branch_obj else ''}
-- Up:
{up_sql}
-- Down:
{down_sql}
"""
        
        return migration_content
    
    def _generate_postgresql_migration(
        self,
        changes: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Generate PostgreSQL migration SQL"""
        up_statements = []
        down_statements = []
        
        # Handle table creation
        if 'create_tables' in changes:
            for table in changes['create_tables']:
                up_statements.append(f"CREATE TABLE {table['name']} (")
                columns = []
                for col in table['columns']:
                    columns.append(f"    {col['name']} {col['type']}")
                up_statements.append(',\n'.join(columns))
                up_statements.append(");")
                
                down_statements.append(f"DROP TABLE IF EXISTS {table['name']};")
        
        # Handle column additions
        if 'add_columns' in changes:
            for change in changes['add_columns']:
                up_statements.append(
                    f"ALTER TABLE {change['table']} ADD COLUMN "
                    f"{change['column']} {change['type']};"
                )
                down_statements.append(
                    f"ALTER TABLE {change['table']} DROP COLUMN {change['column']};"
                )
        
        # Handle index creation
        if 'create_indexes' in changes:
            for index in changes['create_indexes']:
                up_statements.append(
                    f"CREATE INDEX {index['name']} ON "
                    f"{index['table']} ({', '.join(index['columns'])});"
                )
                down_statements.append(f"DROP INDEX IF EXISTS {index['name']};")
        
        up_sql = '\n'.join(up_statements)
        down_sql = '\n'.join(reversed(down_statements))
        
        return up_sql, down_sql
    
    def _generate_mysql_migration(
        self,
        changes: Dict[str, Any]
    ) -> Tuple[str, str]:
        """Generate MySQL migration SQL"""
        # Similar to PostgreSQL but with MySQL syntax
        up_statements = []
        down_statements = []
        
        # Handle table creation
        if 'create_tables' in changes:
            for table in changes['create_tables']:
                up_statements.append(f"CREATE TABLE `{table['name']}` (")
                columns = []
                for col in table['columns']:
                    columns.append(f"    `{col['name']}` {col['type']}")
                up_statements.append(',\n'.join(columns))
                up_statements.append(") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;")
                
                down_statements.append(f"DROP TABLE IF EXISTS `{table['name']}`;")
        
        # Handle column additions
        if 'add_columns' in changes:
            for change in changes['add_columns']:
                up_statements.append(
                    f"ALTER TABLE `{change['table']}` ADD COLUMN "
                    f"`{change['column']}` {change['type']};"
                )
                down_statements.append(
                    f"ALTER TABLE `{change['table']}` DROP COLUMN `{change['column']}`;"
                )
        
        up_sql = '\n'.join(up_statements)
        down_sql = '\n'.join(reversed(down_statements))
        
        return up_sql, down_sql