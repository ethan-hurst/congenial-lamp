"""
Unit tests for Database Provisioning Service
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
import uuid

from src.services.database.provisioner import DatabaseProvisioner
from src.models.database import (
    DatabaseInstance, DBType, DBSize, DBStatus,
    DatabaseBranch
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
def mock_user():
    """Mock user"""
    user = User()
    user.id = "user-123"
    user.email = "test@example.com"
    return user


@pytest.fixture
def mock_project():
    """Mock project"""
    project = Project()
    project.id = "project-123"
    project.owner_id = "user-123"
    project.name = "Test Project"
    return project


@pytest.fixture
def provisioner():
    """Database provisioner instance"""
    return DatabaseProvisioner()


class TestDatabaseProvisioner:
    """Test cases for Database Provisioner"""
    
    @pytest.mark.asyncio
    async def test_provision_database_success(self, provisioner, mock_db, mock_user, mock_project):
        """Test successful database provisioning"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        with patch('src.services.database.provisioner.encrypt_string') as mock_encrypt:
            mock_encrypt.return_value = "encrypted_password"
            
            with patch('asyncio.create_task') as mock_create_task:
                # Act
                result = await provisioner.provision_database(
                    project_id="project-123",
                    db_type=DBType.POSTGRESQL,
                    version="15",
                    size=DBSize.SMALL,
                    region="us-east-1",
                    name="Test Database",
                    user_id="user-123",
                    db=mock_db
                )
                
                # Assert
                assert result is not None
                assert result.project_id == "project-123"
                assert result.db_type == DBType.POSTGRESQL
                assert result.version == "15"
                assert result.size == DBSize.SMALL
                assert result.status == DBStatus.PROVISIONING
                assert result.created_by == "user-123"
                
                # Verify database operations
                assert mock_db.add.called
                assert mock_db.commit.called
                assert mock_create_task.called
    
    @pytest.mark.asyncio
    async def test_provision_database_project_not_found(self, provisioner, mock_db):
        """Test database provisioning with non-existent project"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Project .* not found or access denied"):
            await provisioner.provision_database(
                project_id="invalid-project",
                db_type=DBType.POSTGRESQL,
                version="15",
                size=DBSize.SMALL,
                region="us-east-1",
                name="Test Database",
                user_id="user-123",
                db=mock_db
            )
        
        # Verify rollback was called
        assert mock_db.rollback.called
    
    @pytest.mark.asyncio
    async def test_provision_database_limit_exceeded(self, provisioner, mock_db, mock_project):
        """Test database provisioning when limit is exceeded"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        mock_db.query.return_value.filter.return_value.count.return_value = 10  # Exceed limit
        
        # Act & Assert
        with pytest.raises(ValueError, match="Project has reached database limit"):
            await provisioner.provision_database(
                project_id="project-123",
                db_type=DBType.POSTGRESQL,
                version="15",
                size=DBSize.SMALL,
                region="us-east-1",
                name="Test Database",
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_get_connection_string_postgresql(self, provisioner, mock_db):
        """Test getting PostgreSQL connection string"""
        # Arrange
        instance = DatabaseInstance()
        instance.id = "db-123"
        instance.project_id = "project-123"
        instance.db_type = DBType.POSTGRESQL
        instance.host = "localhost"
        instance.port = 5432
        instance.username = "testuser"
        instance.password_encrypted = "encrypted_password"
        instance.database_name = "testdb"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            instance,  # First call returns instance
            mock_project  # Second call returns project
        ]
        
        with patch('src.services.database.provisioner.decrypt_string') as mock_decrypt:
            mock_decrypt.return_value = "decrypted_password"
            
            # Act
            result = await provisioner.get_connection_string(
                instance_id="db-123",
                branch="main",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result == "postgresql://testuser:decrypted_password@localhost:5432/testdb"
    
    @pytest.mark.asyncio
    async def test_get_connection_string_mysql(self, provisioner, mock_db):
        """Test getting MySQL connection string"""
        # Arrange
        instance = DatabaseInstance()
        instance.id = "db-123"
        instance.project_id = "project-123"
        instance.db_type = DBType.MYSQL
        instance.host = "localhost"
        instance.port = 3306
        instance.username = "testuser"
        instance.password_encrypted = "encrypted_password"
        instance.database_name = "testdb"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            instance,  # First call returns instance
            mock_project  # Second call returns project
        ]
        
        with patch('src.services.database.provisioner.decrypt_string') as mock_decrypt:
            mock_decrypt.return_value = "decrypted_password"
            
            # Act
            result = await provisioner.get_connection_string(
                instance_id="db-123",
                branch="main",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert result == "mysql://testuser:decrypted_password@localhost:3306/testdb"
    
    @pytest.mark.asyncio
    async def test_get_connection_string_not_found(self, provisioner, mock_db):
        """Test getting connection string for non-existent instance"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Act & Assert
        with pytest.raises(ValueError, match="Database instance .* not found"):
            await provisioner.get_connection_string(
                instance_id="invalid-id",
                branch="main",
                user_id="user-123",
                db=mock_db
            )
    
    @pytest.mark.asyncio
    async def test_delete_database_success(self, provisioner, mock_db, mock_project):
        """Test successful database deletion"""
        # Arrange
        instance = DatabaseInstance()
        instance.id = "db-123"
        instance.project_id = "project-123"
        instance.status = DBStatus.READY
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            instance,  # First call returns instance
            mock_project  # Second call returns project
        ]
        
        with patch.object(provisioner, '_delete_container', new_callable=AsyncMock) as mock_delete:
            # Act
            await provisioner.delete_database(
                instance_id="db-123",
                user_id="user-123",
                db=mock_db
            )
            
            # Assert
            assert instance.status == DBStatus.DELETING
            assert mock_delete.called
            assert mock_db.delete.called
            assert mock_db.commit.call_count == 2  # Once for status update, once for delete
    
    @pytest.mark.asyncio
    async def test_list_databases_success(self, provisioner, mock_db, mock_project):
        """Test listing databases for a project"""
        # Arrange
        mock_db.query.return_value.filter.return_value.first.return_value = mock_project
        
        db1 = DatabaseInstance()
        db1.id = "db-1"
        db1.name = "Database 1"
        db1.status = DBStatus.READY
        
        db2 = DatabaseInstance()
        db2.id = "db-2"
        db2.name = "Database 2"
        db2.status = DBStatus.PROVISIONING
        
        mock_db.query.return_value.filter.return_value.all.return_value = [db1, db2]
        
        # Act
        result = await provisioner.list_databases(
            project_id="project-123",
            user_id="user-123",
            db=mock_db
        )
        
        # Assert
        assert len(result) == 2
        assert result[0].id == "db-1"
        assert result[1].id == "db-2"
    
    @pytest.mark.asyncio
    async def test_get_database_metrics(self, provisioner, mock_db, mock_project):
        """Test getting database metrics"""
        # Arrange
        instance = DatabaseInstance()
        instance.id = "db-123"
        instance.project_id = "project-123"
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            instance,  # First call returns instance
            mock_project,  # Second call returns project
            None  # Third call returns no metrics
        ]
        
        # Act
        result = await provisioner.get_database_metrics(
            instance_id="db-123",
            user_id="user-123",
            db=mock_db
        )
        
        # Assert
        assert result["cpu_usage"] == 0
        assert result["memory_usage"] == 0
        assert result["disk_usage"] == 0
        assert result["connections"] == 0
        assert result["queries_per_second"] == 0
    
    @pytest.mark.asyncio
    async def test_provision_container_postgresql(self, provisioner, mock_db):
        """Test PostgreSQL container provisioning"""
        # Arrange
        instance = DatabaseInstance()
        instance.id = "db-123"
        instance.db_type = DBType.POSTGRESQL
        instance.version = "15"
        instance.memory_gb = 1.0
        instance.cpu_cores = 1.0
        instance.username = "testuser"
        instance.database_name = "testdb"
        instance.password_encrypted = "encrypted"
        
        with patch('aiodocker.Docker') as mock_docker_class:
            mock_docker = AsyncMock()
            mock_docker_class.return_value = mock_docker
            
            mock_container = AsyncMock()
            mock_docker.containers.create.return_value = mock_container
            
            mock_container.show.return_value = {
                "NetworkSettings": {
                    "Ports": {
                        "5432/tcp": [{"HostPort": "54321"}]
                    }
                }
            }
            
            with patch.object(provisioner, '_pull_image_if_needed', new_callable=AsyncMock):
                with patch.object(provisioner, '_wait_for_database', new_callable=AsyncMock):
                    with patch.object(provisioner, '_initialize_database', new_callable=AsyncMock):
                        # Act
                        await provisioner._provision_container(
                            instance, "password123", mock_db
                        )
                        
                        # Assert
                        assert mock_docker.containers.create.called
                        assert mock_container.start.called
                        assert instance.host == "localhost"
                        assert instance.port == 54321
                        assert instance.status == DBStatus.READY
    
    def test_size_config(self, provisioner):
        """Test database size configurations"""
        # Test each size has proper configuration
        for size in [DBSize.MICRO, DBSize.SMALL, DBSize.MEDIUM, DBSize.LARGE]:
            config = provisioner._size_config[size]
            assert "cpu" in config
            assert "memory_gb" in config
            assert "storage_gb" in config
            assert "max_connections" in config
            assert "cost_per_hour" in config
            
            # Ensure sizes increase appropriately
            if size == DBSize.MICRO:
                assert config["cpu"] <= 1
                assert config["memory_gb"] <= 1
            elif size == DBSize.LARGE:
                assert config["cpu"] >= 2
                assert config["memory_gb"] >= 4