"""
Unit tests for Database Branching Service
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

from src.services.database.branching import (
    DatabaseBranching, BranchConflict, MergeResult
)
from src.models.database import (
    DatabaseInstance, DatabaseBranch, DBType, DBStatus,
    MergeStrategy, DatabaseMigration, MigrationStatus
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
    instance.username = "testuser"
    instance.password_encrypted = "encrypted"
    return instance


@pytest.fixture
def mock_branch():
    """Mock database branch"""
    branch = DatabaseBranch()
    branch.id = "branch-123"
    branch.instance_id = "db-123"
    branch.name = "main"
    branch.is_default = True
    branch.schema_version = 1
    branch.data_hash = "hash123"
    return branch


@pytest.fixture
def branching():
    """Database branching service instance"""
    return DatabaseBranching()


class TestDatabaseBranching:
    """Test cases for Database Branching Service"""
    
    @pytest.mark.asyncio
    async def test_create_branch_success(self, branching, mock_db, mock_instance, mock_branch):
        """Test successful branch creation"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project,   # Project lookup
            mock_branch,    # Source branch lookup
            None           # New branch check
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        
        with patch.object(branching, '_create_cow_branch', new_callable=AsyncMock) as mock_cow:
            with patch.object(branching, '_copy_migration_history', new_callable=AsyncMock) as mock_copy:
                # Act
                result = await branching.create_branch(
                    instance_id="db-123",
                    source_branch="main",
                    new_branch="feature-1",
                    use_cow=True,
                    user_id="user-123",
                    db=mock_db
                )
                
                # Assert
                assert result is not None
                assert result.instance_id == "db-123"
                assert result.name == "feature-1"
                assert result.parent_branch == "main"
                assert result.use_cow is True
                assert mock_cow.called
                assert mock_copy.called
                assert mock_db.add.called
                assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_create_branch_limit_exceeded(self, branching, mock_db, mock_instance):
        """Test branch creation when limit is exceeded"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_instance
        mock_db.query.return_value.filter.return_value.count.return_value = 10  # At limit
        
        # Act & Assert
        with pytest.raises(ValueError, match="Branch limit .* reached"):
            await branching.create_branch(
                instance_id="db-123",
                source_branch="main",
                new_branch="feature-1",
                use_cow=True,
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_create_branch_duplicate_name(self, branching, mock_db, mock_instance, mock_branch):
        """Test branch creation with duplicate name"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        existing_branch = DatabaseBranch()
        existing_branch.name = "feature-1"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project,   # Project lookup
            mock_branch,    # Source branch lookup
            existing_branch # New branch check - already exists
        ]
        mock_db.query.return_value.filter.return_value.count.return_value = 1
        
        # Act & Assert
        with pytest.raises(ValueError, match="Branch .* already exists"):
            await branching.create_branch(
                instance_id="db-123",
                source_branch="main",
                new_branch="feature-1",
                use_cow=True,
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_list_branches_success(self, branching, mock_db, mock_instance):
        """Test listing branches"""
        # Arrange
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        branch1 = DatabaseBranch()
        branch1.id = "branch-1"
        branch1.name = "main"
        branch1.is_default = True
        
        branch2 = DatabaseBranch()
        branch2.id = "branch-2"
        branch2.name = "feature-1"
        branch2.is_default = False
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_instance,  # Instance lookup
            mock_project    # Project lookup
        ]
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            branch1, branch2
        ]
        
        # Act
        result = await branching.list_branches(
            instance_id="db-123",
            user_id="user-123",
            db=mock_db
        )
        
        # Assert
        assert len(result) == 2
        assert result[0].name == "main"
        assert result[0].is_default is True
        assert result[1].name == "feature-1"
    
    @pytest.mark.asyncio
    async def test_switch_branch_success(self, branching, mock_db, mock_branch):
        """Test switching branches"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_branch
        
        # Act
        result = await branching.switch_branch(
            instance_id="db-123",
            branch_name="main",
            user_id="user-123",
            db=mock_db
        )
        
        # Assert
        assert result == mock_branch
        assert mock_branch.last_accessed is not None
        assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_merge_branch_success(self, branching, mock_db):
        """Test successful branch merge"""
        # Arrange
        source_branch = DatabaseBranch()
        source_branch.id = "branch-source"
        source_branch.name = "feature-1"
        source_branch.schema_version = 2
        source_branch.data_hash = "hash456"
        source_branch.merged_into = None
        
        target_branch = DatabaseBranch()
        target_branch.id = "branch-target"
        target_branch.name = "main"
        target_branch.schema_version = 1
        target_branch.data_hash = "hash123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            source_branch,  # Source branch lookup
            target_branch   # Target branch lookup
        ]
        
        with patch.object(branching, '_merge_full', new_callable=AsyncMock) as mock_merge:
            mock_merge.return_value = MergeResult(success=True, merged_changes=5)
            
            # Act
            result = await branching.merge_branch(
                instance_id="db-123",
                source_branch="feature-1",
                target_branch="main",
                strategy=MergeStrategy.FULL,
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result.success is True
            assert result.merged_changes == 5
            assert source_branch.merged_into == "main"
            assert source_branch.merge_date is not None
            assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_merge_branch_already_merged(self, branching, mock_db):
        """Test merging an already merged branch"""
        # Arrange
        source_branch = DatabaseBranch()
        source_branch.merged_into = "main"
        
        target_branch = DatabaseBranch()
        target_branch.name = "main"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            source_branch,  # Source branch lookup
            target_branch   # Target branch lookup
        ]
        
        # Act & Assert
        with pytest.raises(ValueError, match="Branch .* is already merged"):
            await branching.merge_branch(
                instance_id="db-123",
                source_branch="feature-1",
                target_branch="main",
                strategy=MergeStrategy.FULL,
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_delete_branch_success(self, branching, mock_db, mock_instance):
        """Test successful branch deletion"""
        # Arrange
        branch = DatabaseBranch()
        branch.id = "branch-123"
        branch.name = "feature-1"
        branch.is_default = False
        
        mock_project = Project()
        mock_project.id = "project-123"
        mock_project.owner_id = "user-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            branch,         # Branch lookup
            mock_instance,  # Instance lookup
            mock_project    # Project lookup
        ]
        
        with patch.object(branching, '_delete_branch_database', new_callable=AsyncMock) as mock_delete:
            # Act
            await branching.delete_branch(
                instance_id="db-123",
                branch_name="feature-1",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert mock_delete.called
            assert mock_db.delete.called
            assert mock_db.commit.called
    
    @pytest.mark.asyncio
    async def test_delete_default_branch_fails(self, branching, mock_db):
        """Test deleting default branch fails"""
        # Arrange
        branch = DatabaseBranch()
        branch.is_default = True
        
        mock_db.query.return_value.filter.return_value.first.return_value = branch
        
        # Act & Assert
        with pytest.raises(ValueError, match="Cannot delete the default branch"):
            await branching.delete_branch(
                instance_id="db-123",
                branch_name="main",
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_get_branch_diff(self, branching, mock_db):
        """Test getting differences between branches"""
        # Arrange
        branch1 = DatabaseBranch()
        branch1.id = "branch-1"
        branch1.schema_version = 2
        branch1.data_hash = "hash123"
        branch1.storage_used_gb = 5.0
        
        branch2 = DatabaseBranch()
        branch2.id = "branch-2"
        branch2.schema_version = 3
        branch2.data_hash = "hash456"
        branch2.storage_used_gb = 7.5
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            branch1,  # First branch lookup
            branch2   # Second branch lookup
        ]
        
        # Mock migration diff
        with patch.object(branching, '_get_migration_diff', new_callable=AsyncMock) as mock_diff:
            mock_diff.return_value = {
                "only_in_branch1": [1],
                "only_in_branch2": [2, 3],
                "in_both": []
            }
            
            # Act
            result = await branching.get_branch_diff(
                instance_id="db-123",
                branch1="branch1",
                branch2="branch2",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result["schema_differences"]["branch1_version"] == 2
            assert result["schema_differences"]["branch2_version"] == 3
            assert result["schema_differences"]["versions_match"] is False
            assert result["data_differences"]["data_matches"] is False
            assert result["size_differences"]["difference_gb"] == 2.5
            assert len(result["migration_differences"]["only_in_branch2"]) == 2
    
    @pytest.mark.asyncio
    async def test_create_cow_branch_postgresql(self, branching, mock_db, mock_instance, mock_branch):
        """Test COW branch creation for PostgreSQL"""
        # Arrange
        mock_instance.db_type = DBType.POSTGRESQL
        mock_instance.username = "testuser"
        mock_instance.password_encrypted = "encrypted"
        
        new_branch = DatabaseBranch()
        new_branch.name = "feature-1"
        
        with patch('aiodocker.Docker') as mock_docker_class:
            mock_docker = AsyncMock()
            mock_docker_class.return_value = mock_docker
            
            mock_container = AsyncMock()
            mock_docker.containers.get.return_value = mock_container
            
            mock_exec = AsyncMock()
            mock_exec.start.return_value = b"CREATE DATABASE"
            mock_container.exec.return_value = mock_exec
            
            with patch('src.services.database.branching.decrypt_string') as mock_decrypt:
                mock_decrypt.return_value = "password123"
                
                # Act
                await branching._create_cow_branch(
                    mock_instance, mock_branch, new_branch, mock_db
                )
                
                # Assert
                assert mock_container.exec.called
                # Verify CREATE DATABASE command was executed
                exec_calls = mock_container.exec.call_args_list
                create_db_call = exec_calls[0]
                assert "CREATE DATABASE" in str(create_db_call)
                assert new_branch.storage_used_gb == 0.1
                assert new_branch.delta_size_gb == 0.0
    
    def test_branch_conflict_creation(self):
        """Test BranchConflict object creation"""
        conflict = BranchConflict(
            table="users",
            conflict_type="schema",
            details={"message": "Column type mismatch"}
        )
        
        assert conflict.table == "users"
        assert conflict.conflict_type == "schema"
        assert conflict.details["message"] == "Column type mismatch"
    
    def test_merge_result_creation(self):
        """Test MergeResult object creation"""
        conflicts = [
            BranchConflict("table1", "data", {}),
            BranchConflict("table2", "schema", {})
        ]
        
        result = MergeResult(
            success=False,
            conflicts=conflicts,
            merged_changes=0
        )
        
        assert result.success is False
        assert len(result.conflicts) == 2
        assert result.merged_changes == 0