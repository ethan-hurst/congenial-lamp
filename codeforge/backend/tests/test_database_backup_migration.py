"""
Unit tests for Database Backup and Migration Services
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta
import uuid

from src.services.database.backup import (
    DatabaseBackupService, BackupResult, RestoreResult
)
from src.services.database.migrations import (
    MigrationManager, MigrationResult, MigrationConflict
)
from src.models.database import (
    DatabaseInstance, DatabaseBranch, DatabaseBackup, DatabaseMigration,
    DBType, BackupType, BackupStatus, MigrationStatus
)
from src.models.project import Project
from src.models.user import User


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = Mock()
    db.query = Mock()
    db.add = Mock()
    db.commit = Mock()
    db.rollback = Mock()
    return db


@pytest.fixture
def mock_instance():
    """Mock database instance"""
    instance = DatabaseInstance()
    instance.id = "db-123"
    instance.project_id = "project-123"
    instance.db_type = DBType.POSTGRESQL
    instance.version = "15"
    instance.username = "testuser"
    instance.password_encrypted = "encrypted"
    instance.database_name = "testdb"
    instance.backup_retention_days = 7
    return instance


@pytest.fixture
def mock_branch():
    """Mock database branch"""
    branch = DatabaseBranch()
    branch.id = "branch-123"
    branch.instance_id = "db-123"
    branch.name = "main"
    branch.schema_version = 1
    return branch


@pytest.fixture
def backup_service():
    """Database backup service instance"""
    return DatabaseBackupService()


@pytest.fixture
def migration_manager():
    """Migration manager instance"""
    return MigrationManager()


class TestDatabaseBackupService:
    """Test cases for Database Backup Service"""
    
    @pytest.mark.asyncio
    async def test_create_backup_success(self, backup_service, mock_db, mock_instance, mock_branch):
        """Test successful backup creation"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project,   # Project lookup
            mock_branch     # Branch lookup
        ]
        
        with patch('asyncio.create_task') as mock_create_task:
            # Act
            result = await backup_service.create_backup(
                instance_id="db-123",
                branch="main",
                backup_type=BackupType.FULL,
                name="Test Backup",
                description="Test backup description",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result is not None
            assert result.instance_id == "db-123"
            assert result.branch_id == "branch-123"
            assert result.backup_type == BackupType.FULL
            assert result.status == BackupStatus.IN_PROGRESS
            assert result.name == "Test Backup"
            assert mock_db.add.called
            assert mock_db.commit.called
            assert mock_create_task.called
    
    @pytest.mark.asyncio
    async def test_create_backup_branch_not_found(self, backup_service, mock_db, mock_instance):
        """Test backup creation with non-existent branch"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project,   # Project lookup
            None           # Branch not found
        ]
        
        # Act & Assert
        with pytest.raises(ValueError, match="Branch .* not found"):
            await backup_service.create_backup(
                instance_id="db-123",
                branch="invalid-branch",
                backup_type=BackupType.FULL,
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_perform_backup_postgresql(self, backup_service, mock_db, mock_instance, mock_branch):
        """Test PostgreSQL backup execution"""
        # Arrange
        backup = DatabaseBackup()
        backup.id = "backup-123"
        backup.backup_type = BackupType.FULL
        
        mock_instance.db_type = DBType.POSTGRESQL
        
        with patch('aiodocker.Docker') as mock_docker_class:
            mock_docker = AsyncMock()
            mock_docker_class.return_value = mock_docker
            
            mock_container = AsyncMock()
            mock_docker.containers.get.return_value = mock_container
            
            # Mock exec results
            mock_exec = AsyncMock()
            mock_exec.start.return_value = b"1073741824"  # 1GB in bytes
            mock_container.exec.return_value = mock_exec
            
            with patch('src.services.database.backup.decrypt_string') as mock_decrypt:
                mock_decrypt.return_value = "password123"
                
                with patch.object(backup_service, '_backup_postgresql', new_callable=AsyncMock) as mock_backup:
                    mock_backup.return_value = BackupResult(
                        success=True,
                        backup_id="backups/db-123/backup-123.sql.gz",
                        size_gb=1.0
                    )
                    
                    # Act
                    await backup_service._perform_backup(
                        backup, mock_instance, mock_branch, mock_db
                    )
                    
                    # Assert
                    assert backup.status == BackupStatus.COMPLETED
                    assert backup.size_gb == 1.0
                    assert backup.completed_at is not None
                    assert backup.duration_seconds is not None
                    assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_restore_backup_success(self, backup_service, mock_db, mock_instance, mock_branch):
        """Test successful backup restore"""
        # Arrange
        backup = DatabaseBackup()
        backup.id = "backup-123"
        backup.instance_id = "db-123"
        backup.status = BackupStatus.COMPLETED
        backup.storage_path = "backups/db-123/backup-123.sql.gz"
        
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            backup,         # Backup lookup
            mock_instance,  # Instance lookup
            mock_project,   # Project lookup
            mock_branch     # Branch lookup
        ]
        
        with patch.object(backup_service, '_restore_postgresql', new_callable=AsyncMock) as mock_restore:
            mock_restore.return_value = RestoreResult(success=True)
            
            # Act
            result = await backup_service.restore_backup(
                backup_id="backup-123",
                target_instance="db-123",
                target_branch="main",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result.success is True
            assert result.restored_to == "db-123/main"
            assert backup.restore_count == 1
            assert backup.last_restored_at is not None
            assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_list_backups_success(self, backup_service, mock_db, mock_instance, mock_branch):
        """Test listing backups"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        backup1 = DatabaseBackup()
        backup1.id = "backup-1"
        backup1.name = "Backup 1"
        backup1.status = BackupStatus.COMPLETED
        
        backup2 = DatabaseBackup()
        backup2.id = "backup-2"
        backup2.name = "Backup 2"
        backup2.status = BackupStatus.IN_PROGRESS
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project,   # Project lookup
            mock_branch     # Branch lookup (for branch filter)
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            backup1, backup2
        ]
        
        # Act
        result = await backup_service.list_backups(
            instance_id="db-123",
            branch="main",
            user_id="user-123",
            db=mock_db
        )
        
        # Assert
        assert len(result) == 2
        assert result[0].id == "backup-1"
        assert result[1].id == "backup-2"
    
    @pytest.mark.asyncio
    async def test_schedule_backups(self, backup_service, mock_db, mock_instance):
        """Test scheduling automated backups"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project    # Project lookup
        ]
        
        with patch.object(backup_service, '_start_backup_scheduler', new_callable=AsyncMock) as mock_scheduler:
            # Act
            await backup_service.schedule_backups(
                instance_id="db-123",
                schedule="0 2 * * *",  # Daily at 2 AM
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert mock_instance.backup_schedule == "0 2 * * *"
            assert mock_instance.backup_enabled is True
            assert mock_db.commit.called
            assert mock_scheduler.called
    
    @pytest.mark.asyncio
    async def test_schedule_backups_invalid_cron(self, backup_service, mock_db):
        """Test scheduling with invalid cron expression"""
        # Act & Assert
        with pytest.raises(ValueError, match="Invalid cron expression"):
            await backup_service.schedule_backups(
                instance_id="db-123",
                schedule="invalid cron",
                user_id="user-123",
                db=mock_db
            )


class TestMigrationManager:
    """Test cases for Migration Manager"""
    
    @pytest.mark.asyncio
    async def test_apply_migration_success(self, migration_manager, mock_db, mock_instance, mock_branch):
        """Test successful migration application"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project,   # Project lookup
            mock_branch,    # Branch lookup
            None           # No existing migration
        ]
        
        migration_content = """-- Migration Version: 001
-- Name: Create users table
-- Description: Initial users table
-- Depends-On: 
-- Up:
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL
);
-- Down:
DROP TABLE users;"""
        
        with patch.object(migration_manager, '_execute_migration', new_callable=AsyncMock) as mock_execute:
            mock_execute.return_value = MigrationResult(
                success=True,
                version=1,
                execution_time_ms=100
            )
            
            # Act
            result = await migration_manager.apply_migration(
                instance_id="db-123",
                branch="main",
                migration_file=migration_content,
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result.success is True
            assert result.version == 1
            assert mock_db.add.called
            assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_apply_migration_duplicate_version(self, migration_manager, mock_db, mock_instance, mock_branch):
        """Test applying migration with duplicate version"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        existing_migration = DatabaseMigration()
        existing_migration.version = 1
        existing_migration.status = MigrationStatus.APPLIED
        existing_migration.checksum = "different_checksum"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,       # Instance lookup
            mock_project,        # Project lookup
            mock_branch,         # Branch lookup
            existing_migration   # Existing migration found
        ]
        
        migration_content = """-- Migration Version: 001
-- Name: Create users table
-- Up:
CREATE TABLE users (id INT);"""
        
        # Act & Assert
        with pytest.raises(ValueError, match="Migration .* already exists with different content"):
            await migration_manager.apply_migration(
                instance_id="db-123",
                branch="main",
                migration_file=migration_content,
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_rollback_migration_success(self, migration_manager, mock_db, mock_instance, mock_branch):
        """Test successful migration rollback"""
        # Arrange
        migration = DatabaseMigration()
        migration.id = "mig-123"
        migration.version = 2
        migration.status = MigrationStatus.APPLIED
        migration.down_sql = "DROP TABLE users;"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_branch,   # Branch lookup
            migration      # Migration lookup
        ]
        
        mock_db.query.return_value.filter.return_value.all.return_value = []  # No dependent migrations
        
        with patch.object(migration_manager, '_execute_rollback', new_callable=AsyncMock) as mock_rollback:
            mock_rollback.return_value = MigrationResult(
                success=True,
                version=2,
                execution_time_ms=50
            )
            
            # Act
            result = await migration_manager.rollback_migration(
                instance_id="db-123",
                branch="main",
                version=2,
                reason="Testing rollback",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result.success is True
            assert result.version == 2
            assert mock_rollback.called
    
    @pytest.mark.asyncio
    async def test_rollback_migration_no_down_script(self, migration_manager, mock_db, mock_branch):
        """Test rollback without down script fails"""
        # Arrange
        migration = DatabaseMigration()
        migration.version = 1
        migration.status = MigrationStatus.APPLIED
        migration.down_sql = None  # No rollback script
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_branch,   # Branch lookup
            migration      # Migration lookup
        ]
        
        # Act & Assert
        with pytest.raises(ValueError, match="does not have a rollback script"):
            await migration_manager.rollback_migration(
                instance_id="db-123",
                branch="main",
                version=1,
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_get_migration_history(self, migration_manager, mock_db, mock_branch):
        """Test getting migration history"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_instance = DatabaseInstance()
        mock_instance.project_id = "project-123"
        
        mig1 = DatabaseMigration()
        mig1.version = 1
        mig1.name = "Initial"
        mig1.status = MigrationStatus.APPLIED
        
        mig2 = DatabaseMigration()
        mig2.version = 2
        mig2.name = "Add users"
        mig2.status = MigrationStatus.APPLIED
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_branch,   # Branch lookup
            mock_instance, # Instance lookup
            mock_project   # Project lookup
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mig1, mig2
        ]
        
        # Act
        result = await migration_manager.get_migration_history(
            instance_id="db-123",
            branch="main",
            user_id="user-123",
            db=mock_db
        )
        
        # Assert
        assert len(result) == 2
        assert result[0].version == 1
        assert result[1].version == 2
    
    @pytest.mark.asyncio
    async def test_validate_migration_sequence(self, migration_manager, mock_db, mock_branch):
        """Test validating migration sequence"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_branch
        mock_db.query.return_value.filter.return_value.all.return_value = []  # No existing migrations
        
        migrations = [
            """-- Migration Version: 001
-- Name: Create users
-- Up:
CREATE TABLE users (id INT);""",
            """-- Migration Version: 002
-- Name: Add email
-- Depends-On: 1
-- Up:
ALTER TABLE users ADD email VARCHAR(255);"""
        ]
        
        with patch.object(migration_manager, '_get_applied_versions', new_callable=AsyncMock) as mock_applied:
            mock_applied.return_value = []
            
            # Act
            is_valid, conflicts = await migration_manager.validate_migration_sequence(
                instance_id="db-123",
                branch="main",
                migrations=migrations,
                db=mock_db
            )
            
            # Assert
            assert is_valid is True
            assert len(conflicts) == 0
    
    def test_migration_result_creation(self):
        """Test MigrationResult object creation"""
        result = MigrationResult(
            success=True,
            version=5,
            execution_time_ms=150
        )
        
        assert result.success is True
        assert result.version == 5
        assert result.execution_time_ms == 150
        assert result.error is None
    
    def test_backup_result_creation(self):
        """Test BackupResult object creation"""
        result = BackupResult(
            success=True,
            backup_id="backup-123",
            size_gb=2.5
        )
        
        assert result.success is True
        assert result.backup_id == "backup-123"
        assert result.size_gb == 2.5
        assert result.error is None