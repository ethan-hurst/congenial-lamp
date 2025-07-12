"""
Tests for Clone Service
"""
import pytest
import tempfile
import shutil
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path
from datetime import datetime, timezone

from src.services.clone_service import (
    InstantCloneService, CloneStatus, CloneMetadata, CloneResult
)


class TestInstantCloneService:
    """Test suite for InstantCloneService"""

    @pytest.fixture
    def clone_service(self):
        """Create clone service instance"""
        return InstantCloneService()

    @pytest.fixture
    def temp_projects_dir(self):
        """Create temporary projects directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def sample_project(self, temp_projects_dir):
        """Create a sample project for testing"""
        project_id = "test-project-123"
        project_path = temp_projects_dir / project_id
        project_path.mkdir()
        
        # Create sample files
        (project_path / "main.py").write_text("print('Hello, world!')")
        (project_path / "requirements.txt").write_text("fastapi==0.68.0\nuvicorn==0.15.0")
        (project_path / "README.md").write_text("# Test Project\nThis is a test project.")
        
        # Create subdirectory
        (project_path / "src").mkdir()
        (project_path / "src" / "utils.py").write_text("def helper():\n    pass")
        
        return project_id, project_path

    @pytest.mark.asyncio
    async def test_clone_project_success(self, clone_service, temp_projects_dir, sample_project):
        """Test successful project cloning"""
        source_project_id, source_path = sample_project
        
        # Mock the projects path
        clone_service.projects_path = temp_projects_dir
        
        result = await clone_service.clone_project(
            source_project_id=source_project_id,
            user_id="test-user-123",
            clone_name="Cloned Test Project"
        )
        
        assert result.success is True
        assert result.new_project_id
        assert result.cloned_files > 0
        assert result.total_time_seconds > 0
        
        # Verify cloned project exists
        cloned_path = temp_projects_dir / result.new_project_id
        assert cloned_path.exists()
        assert (cloned_path / "main.py").exists()
        assert (cloned_path / "requirements.txt").exists()
        assert (cloned_path / "src" / "utils.py").exists()

    @pytest.mark.asyncio
    async def test_clone_project_nonexistent_source(self, clone_service, temp_projects_dir):
        """Test cloning non-existent project"""
        clone_service.projects_path = temp_projects_dir
        
        result = await clone_service.clone_project(
            source_project_id="nonexistent-project",
            user_id="test-user-123"
        )
        
        assert result.success is False
        assert "not found" in result.error_message

    @pytest.mark.asyncio
    async def test_validate_source_project_success(self, clone_service, temp_projects_dir, sample_project):
        """Test successful source project validation"""
        source_project_id, _ = sample_project
        clone_service.projects_path = temp_projects_dir
        
        # Should not raise exception
        await clone_service._validate_source_project(source_project_id)

    @pytest.mark.asyncio
    async def test_validate_source_project_not_found(self, clone_service, temp_projects_dir):
        """Test source project validation failure"""
        clone_service.projects_path = temp_projects_dir
        
        with pytest.raises(ValueError, match="not found"):
            await clone_service._validate_source_project("nonexistent")

    @pytest.mark.asyncio
    async def test_analyze_project(self, clone_service, temp_projects_dir, sample_project):
        """Test project analysis"""
        source_project_id, _ = sample_project
        clone_service.projects_path = temp_projects_dir
        
        analysis = await clone_service._analyze_project(source_project_id)
        
        assert analysis["file_count"] == 4  # main.py, requirements.txt, README.md, utils.py
        assert analysis["total_size"] > 0
        assert analysis["has_dependencies"] is True
        assert "py" in analysis["file_types"]
        assert "md" in analysis["file_types"]

    @pytest.mark.asyncio
    async def test_create_project_structure(self, clone_service, temp_projects_dir):
        """Test creating project structure"""
        target_path = temp_projects_dir / "new-project"
        
        await clone_service._create_project_structure(target_path, "New Project")
        
        assert target_path.exists()
        assert (target_path / "codeforge.json").exists()
        
        # Verify config content
        config_content = (target_path / "codeforge.json").read_text()
        assert "New Project" in config_content
        assert "cloned" in config_content

    @pytest.mark.asyncio
    async def test_clone_files_optimized(self, clone_service, temp_projects_dir, sample_project):
        """Test optimized file cloning"""
        source_project_id, _ = sample_project
        target_project_id = "cloned-project"
        clone_service.projects_path = temp_projects_dir
        
        # Create target directory
        target_path = temp_projects_dir / target_project_id
        target_path.mkdir()
        
        # Create metadata
        metadata = CloneMetadata(
            clone_id="test-clone",
            source_project_id=source_project_id,
            target_project_id=target_project_id,
            user_id="test-user",
            status=CloneStatus.COPYING_FILES,
            progress=0.0,
            start_time=datetime.now(timezone.utc),
            total_files=4,
            total_bytes=1000
        )
        
        await clone_service._clone_files_optimized(
            source_project_id,
            target_project_id,
            metadata
        )
        
        # Verify files were copied
        assert (target_path / "main.py").exists()
        assert (target_path / "requirements.txt").exists()
        assert (target_path / "src" / "utils.py").exists()
        assert metadata.files_copied > 0

    @pytest.mark.asyncio
    async def test_copy_small_file(self, clone_service, temp_projects_dir):
        """Test copying small files"""
        source_file = temp_projects_dir / "source.txt"
        target_file = temp_projects_dir / "target.txt"
        
        source_file.write_text("Hello, world!")
        
        await clone_service._copy_small_file(source_file, target_file)
        
        assert target_file.exists()
        assert target_file.read_text() == "Hello, world!"

    @pytest.mark.asyncio
    async def test_copy_large_file(self, clone_service, temp_projects_dir):
        """Test copying large files with chunking"""
        source_file = temp_projects_dir / "large_source.txt"
        target_file = temp_projects_dir / "large_target.txt"
        
        # Create a file larger than chunk size
        large_content = "x" * (clone_service.chunk_size * 2 + 100)
        source_file.write_text(large_content)
        
        await clone_service._copy_large_file(source_file, target_file)
        
        assert target_file.exists()
        assert target_file.read_text() == large_content

    @pytest.mark.asyncio
    async def test_setup_cloned_environment(self, clone_service, temp_projects_dir):
        """Test setting up cloned environment"""
        target_project_id = "test-target"
        target_path = temp_projects_dir / target_project_id
        target_path.mkdir()
        
        # Create requirements.txt
        (target_path / "requirements.txt").write_text("fastapi==0.68.0")
        
        clone_service.projects_path = temp_projects_dir
        
        source_info = {
            "name": "Source Project",
            "has_dependencies": True
        }
        
        metadata = CloneMetadata(
            clone_id="test",
            source_project_id="source",
            target_project_id=target_project_id,
            user_id="user",
            status=CloneStatus.SETTING_UP_ENVIRONMENT,
            progress=0.9,
            start_time=datetime.now(timezone.utc)
        )
        
        # Mock subprocess to avoid actual dependency installation
        with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock):
            await clone_service._setup_cloned_environment(
                target_project_id,
                source_info,
                include_dependencies=True,
                include_secrets=True,
                metadata=metadata
            )
        
        # Verify config was updated
        config_file = target_path / "codeforge.json"
        assert config_file.exists()
        
        # Verify .env file was created
        env_file = target_path / ".env"
        assert env_file.exists()

    @pytest.mark.asyncio
    async def test_install_dependencies_node(self, clone_service, temp_projects_dir):
        """Test installing Node.js dependencies"""
        project_path = temp_projects_dir / "node-project"
        project_path.mkdir()
        (project_path / "package.json").write_text('{"name": "test"}')
        
        with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock) as mock_subprocess:
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_subprocess.return_value = mock_process
            
            await clone_service._install_dependencies(project_path)
            
            mock_subprocess.assert_called_with(
                "npm install",
                cwd=project_path,
                stdout=pytest.mock.ANY,
                stderr=pytest.mock.ANY
            )

    @pytest.mark.asyncio
    async def test_install_dependencies_python(self, clone_service, temp_projects_dir):
        """Test installing Python dependencies"""
        project_path = temp_projects_dir / "python-project"
        project_path.mkdir()
        (project_path / "requirements.txt").write_text("fastapi==0.68.0")
        
        with patch('asyncio.create_subprocess_shell', new_callable=AsyncMock) as mock_subprocess:
            mock_process = Mock()
            mock_process.wait.return_value = 0
            mock_subprocess.return_value = mock_process
            
            await clone_service._install_dependencies(project_path)
            
            mock_subprocess.assert_called_with(
                "pip install -r requirements.txt",
                cwd=project_path,
                stdout=pytest.mock.ANY,
                stderr=pytest.mock.ANY
            )

    @pytest.mark.asyncio
    async def test_finalize_clone(self, clone_service, temp_projects_dir):
        """Test finalizing clone operation"""
        target_project_id = "final-project"
        target_path = temp_projects_dir / target_project_id
        target_path.mkdir()
        
        # Create a shell script
        script_path = target_path / "setup.sh"
        script_path.write_text("#!/bin/bash\necho 'Setup complete'")
        
        clone_service.projects_path = temp_projects_dir
        
        metadata = CloneMetadata(
            clone_id="test-clone",
            source_project_id="source",
            target_project_id=target_project_id,
            user_id="user",
            status=CloneStatus.FINALIZING,
            progress=0.95,
            start_time=datetime.now(timezone.utc),
            files_copied=10,
            bytes_copied=5000
        )
        
        await clone_service._finalize_clone(target_project_id, metadata)
        
        # Verify completion marker
        marker_path = target_path / ".clone_complete"
        assert marker_path.exists()
        
        marker_content = marker_path.read_text()
        assert "test-clone" in marker_content
        assert "10" in marker_content  # files_copied

    @pytest.mark.asyncio
    async def test_cleanup_failed_clone(self, clone_service, temp_projects_dir):
        """Test cleaning up failed clone"""
        target_project_id = "failed-project"
        target_path = temp_projects_dir / target_project_id
        target_path.mkdir()
        (target_path / "test.txt").write_text("test")
        
        clone_service.projects_path = temp_projects_dir
        
        with patch.object(clone_service, 'docker_client') as mock_docker:
            mock_container = Mock()
            mock_docker.containers.list.return_value = [mock_container]
            
            await clone_service._cleanup_failed_clone(target_project_id)
            
            # Verify directory was removed
            assert not target_path.exists()
            
            # Verify containers were cleaned up
            mock_container.remove.assert_called_with(force=True)

    def test_get_clone_status(self, clone_service):
        """Test getting clone status"""
        clone_id = "test-clone-123"
        metadata = CloneMetadata(
            clone_id=clone_id,
            source_project_id="source",
            target_project_id="target",
            user_id="user",
            status=CloneStatus.COPYING_FILES,
            progress=0.5,
            start_time=datetime.now(timezone.utc)
        )
        
        clone_service.clone_cache[clone_id] = metadata
        
        result = clone_service.get_clone_status(clone_id)
        
        assert result == metadata
        assert result.status == CloneStatus.COPYING_FILES
        assert result.progress == 0.5

    def test_get_clone_status_not_found(self, clone_service):
        """Test getting status for non-existent clone"""
        result = clone_service.get_clone_status("nonexistent")
        assert result is None

    def test_list_user_clones(self, clone_service):
        """Test listing user's clones"""
        user_id = "test-user-123"
        
        # Add multiple clones
        clone1 = CloneMetadata(
            clone_id="clone1",
            source_project_id="source1",
            target_project_id="target1",
            user_id=user_id,
            status=CloneStatus.COMPLETED,
            progress=1.0,
            start_time=datetime.now(timezone.utc)
        )
        
        clone2 = CloneMetadata(
            clone_id="clone2",
            source_project_id="source2",
            target_project_id="target2",
            user_id=user_id,
            status=CloneStatus.COPYING_FILES,
            progress=0.5,
            start_time=datetime.now(timezone.utc)
        )
        
        clone3 = CloneMetadata(
            clone_id="clone3",
            source_project_id="source3",
            target_project_id="target3",
            user_id="other-user",
            status=CloneStatus.COMPLETED,
            progress=1.0,
            start_time=datetime.now(timezone.utc)
        )
        
        clone_service.clone_cache = {
            "clone1": clone1,
            "clone2": clone2,
            "clone3": clone3
        }
        
        user_clones = clone_service.list_user_clones(user_id)
        
        assert len(user_clones) == 2
        assert all(clone.user_id == user_id for clone in user_clones)

    @pytest.mark.asyncio
    async def test_clone_project_with_containers(self, clone_service, temp_projects_dir, sample_project):
        """Test cloning project with containers"""
        source_project_id, _ = sample_project
        clone_service.projects_path = temp_projects_dir
        
        with patch.object(clone_service, '_clone_containers', new_callable=AsyncMock) as mock_clone_containers:
            result = await clone_service.clone_project(
                source_project_id=source_project_id,
                user_id="test-user-123",
                include_containers=True
            )
            
            assert result.success is True
            mock_clone_containers.assert_called_once()

    @pytest.mark.asyncio
    async def test_clone_project_preserve_state(self, clone_service, temp_projects_dir, sample_project):
        """Test cloning project with state preservation"""
        source_project_id, _ = sample_project
        clone_service.projects_path = temp_projects_dir
        
        with patch.object(clone_service, '_clone_containers', new_callable=AsyncMock):
            result = await clone_service.clone_project(
                source_project_id=source_project_id,
                user_id="test-user-123",
                preserve_state=True
            )
            
            assert result.success is True
            assert result.performance_metrics["preserved_state"] is True

    @pytest.mark.asyncio
    async def test_clone_project_performance_metrics(self, clone_service, temp_projects_dir, sample_project):
        """Test clone performance metrics calculation"""
        source_project_id, _ = sample_project
        clone_service.projects_path = temp_projects_dir
        
        result = await clone_service.clone_project(
            source_project_id=source_project_id,
            user_id="test-user-123"
        )
        
        assert result.success is True
        assert "files_per_second" in result.performance_metrics
        assert "bytes_per_second" in result.performance_metrics
        assert "compression_ratio" in result.performance_metrics
        assert result.performance_metrics["files_per_second"] > 0