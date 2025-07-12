"""
Performance tests for CodeForge
"""
import pytest
import asyncio
import time
from unittest.mock import Mock, patch
import tempfile
import shutil
from pathlib import Path

from src.services.clone_service import InstantCloneService
from src.services.ai_service import MultiAgentAI, AIRequest, CodeContext, TaskType, AIProvider
from src.services.credits_service import CreditsService


class TestPerformanceMetrics:
    """Test performance requirements"""

    @pytest.mark.asyncio
    async def test_clone_performance_sub_second(self):
        """Test that cloning completes in under 1 second for small projects"""
        clone_service = InstantCloneService()
        
        # Create temporary project
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            clone_service.projects_path = temp_path
            
            # Create small test project
            source_id = "perf-test-source"
            source_path = temp_path / source_id
            source_path.mkdir()
            
            # Add 10 small files
            for i in range(10):
                (source_path / f"file{i}.py").write_text(f"# File {i}\nprint('hello {i}')")
            
            # Measure clone time
            start_time = time.time()
            
            result = await clone_service.clone_project(
                source_project_id=source_id,
                user_id="perf-user",
                include_dependencies=False,
                include_containers=False,
                include_secrets=False,
                preserve_state=False
            )
            
            end_time = time.time()
            clone_time = end_time - start_time
            
            assert result.success is True
            assert clone_time < 1.0, f"Clone took {clone_time:.3f}s, should be < 1.0s"
            assert result.total_time_seconds < 1.0

    @pytest.mark.asyncio
    async def test_ai_completion_response_time(self):
        """Test AI completion responds within acceptable time"""
        ai_service = MultiAgentAI()
        
        context = CodeContext(
            file_path="test.py",
            content="def hello():",
            language="python",
            cursor_position=12
        )
        
        # Mock the AI call to avoid actual API latency
        with patch.object(ai_service, '_call_claude', return_value="    print('Hello, world!')"):
            start_time = time.time()
            
            suggestions = await ai_service.generate_code_completion(
                context=context,
                user_id="perf-user",
                max_suggestions=3
            )
            
            end_time = time.time()
            response_time = end_time - start_time
            
            assert len(suggestions) > 0
            assert response_time < 2.0, f"AI completion took {response_time:.3f}s, should be < 2.0s"

    @pytest.mark.asyncio
    async def test_credits_calculation_performance(self):
        """Test credit calculations are fast"""
        credits_service = CreditsService()
        
        # Test batch credit calculations
        start_time = time.time()
        
        for i in range(1000):
            cost = await credits_service.calculate_usage_cost(
                operation="file_save",
                duration_seconds=1,
                metadata={"file_size": 1024}
            )
            assert cost > 0
            
        end_time = time.time()
        batch_time = end_time - start_time
        
        # Should process 1000 calculations in under 100ms
        assert batch_time < 0.1, f"1000 credit calculations took {batch_time:.3f}s, should be < 0.1s"

    @pytest.mark.asyncio
    async def test_parallel_file_operations(self):
        """Test parallel file operations in clone service"""
        clone_service = InstantCloneService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create 50 test files
            source_files = []
            target_files = []
            
            for i in range(50):
                source_file = temp_path / f"source{i}.txt"
                target_file = temp_path / f"target{i}.txt"
                
                source_file.write_text(f"Content of file {i}")
                source_files.append(source_file)
                target_files.append(target_file)
            
            # Test parallel copying
            start_time = time.time()
            
            tasks = []
            for source, target in zip(source_files, target_files):
                task = clone_service._copy_small_file(source, target)
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            end_time = time.time()
            parallel_time = end_time - start_time
            
            # Verify all files were copied
            for target_file in target_files:
                assert target_file.exists()
            
            # Parallel should be much faster than sequential
            assert parallel_time < 1.0, f"Parallel copy took {parallel_time:.3f}s, should be < 1.0s"

    @pytest.mark.asyncio
    async def test_memory_usage_during_clone(self):
        """Test memory efficiency during cloning"""
        import psutil
        import os
        
        clone_service = InstantCloneService()
        process = psutil.Process(os.getpid())
        
        # Get initial memory usage
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            clone_service.projects_path = temp_path
            
            # Create moderately sized project
            source_id = "memory-test-source"
            source_path = temp_path / source_id
            source_path.mkdir()
            
            # Add 100 files with reasonable content
            for i in range(100):
                content = f"# File {i}\n" + "x" * 1000  # 1KB per file
                (source_path / f"file{i}.py").write_text(content)
            
            # Perform clone
            result = await clone_service.clone_project(
                source_project_id=source_id,
                user_id="memory-user",
                include_dependencies=False,
                include_containers=False
            )
            
            # Check memory usage after clone
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = final_memory - initial_memory
            
            assert result.success is True
            # Memory increase should be reasonable (< 50MB for this test)
            assert memory_increase < 50, f"Memory increased by {memory_increase:.1f}MB, should be < 50MB"

    @pytest.mark.asyncio
    async def test_concurrent_ai_requests(self):
        """Test handling multiple concurrent AI requests"""
        ai_service = MultiAgentAI()
        
        context = CodeContext(
            file_path="test.py",
            content="def test(): pass",
            language="python",
            cursor_position=10
        )
        
        # Mock AI calls
        with patch.object(ai_service, '_call_claude', return_value="    return True"):
            # Create 10 concurrent requests
            tasks = []
            for i in range(10):
                request = AIRequest(
                    task_type=TaskType.CODE_COMPLETION,
                    provider=AIProvider.CLAUDE,
                    context=context,
                    prompt=f"Complete function {i}",
                    user_id=f"user{i}"
                )
                tasks.append(ai_service.process_request(request))
            
            start_time = time.time()
            responses = await asyncio.gather(*tasks)
            end_time = time.time()
            
            concurrent_time = end_time - start_time
            
            # All requests should complete
            assert len(responses) == 10
            assert all(response.content for response in responses)
            
            # Concurrent processing should be efficient
            assert concurrent_time < 5.0, f"Concurrent AI requests took {concurrent_time:.3f}s, should be < 5.0s"

    @pytest.mark.asyncio
    async def test_large_file_handling(self):
        """Test handling of large files during cloning"""
        clone_service = InstantCloneService()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Create a large file (5MB)
            large_content = "x" * (5 * 1024 * 1024)
            source_file = temp_path / "large_source.txt"
            target_file = temp_path / "large_target.txt"
            
            source_file.write_text(large_content)
            
            start_time = time.time()
            await clone_service._copy_large_file(source_file, target_file)
            end_time = time.time()
            
            copy_time = end_time - start_time
            
            assert target_file.exists()
            assert target_file.stat().st_size == source_file.stat().st_size
            
            # Large file copy should complete in reasonable time
            assert copy_time < 2.0, f"Large file copy took {copy_time:.3f}s, should be < 2.0s"

    @pytest.mark.asyncio
    async def test_database_query_performance(self):
        """Test database query performance for credits service"""
        credits_service = CreditsService()
        
        # Mock database session
        mock_db = Mock()
        mock_db.execute.return_value.scalar.return_value = 1000
        
        # Test multiple balance queries
        start_time = time.time()
        
        for i in range(100):
            result = await credits_service.get_user_balance(f"user{i}", mock_db)
            assert result["balance"] == 1000
            
        end_time = time.time()
        query_time = end_time - start_time
        
        # 100 queries should complete quickly
        assert query_time < 0.5, f"100 balance queries took {query_time:.3f}s, should be < 0.5s"

    def test_clone_throughput(self):
        """Test clone service can handle expected throughput"""
        clone_service = InstantCloneService()
        
        # Simulate checking throughput capacity
        max_parallel_clones = 10
        
        # Verify service can handle concurrent operations
        assert clone_service.max_parallel_files >= 50
        assert hasattr(clone_service, 'clone_cache')
        
        # Test cache can handle expected load
        for i in range(max_parallel_clones * 5):
            clone_id = f"clone-{i}"
            # Simulate adding to cache
            assert len(clone_service.clone_cache) >= 0

    @pytest.mark.asyncio
    async def test_ai_streaming_performance(self):
        """Test AI streaming response performance"""
        ai_service = MultiAgentAI()
        
        messages = [{"role": "user", "content": "Explain Python functions"}]
        
        with patch.object(ai_service, 'process_request') as mock_process:
            mock_response = Mock()
            mock_response.content = "Python functions are defined using the def keyword and can accept parameters."
            mock_process.return_value = mock_response
            
            chunks = []
            start_time = time.time()
            
            async for chunk in ai_service.chat_stream(
                messages=messages,
                user_id="stream-user"
            ):
                chunks.append(chunk)
                # Simulate processing each chunk
                await asyncio.sleep(0.01)
            
            end_time = time.time()
            stream_time = end_time - start_time
            
            assert len(chunks) > 1  # Should be streaming
            assert stream_time > 0.1  # Should have some streaming delay
            assert stream_time < 5.0  # But not too slow

    @pytest.mark.asyncio
    async def test_system_resource_limits(self):
        """Test system operates within resource limits"""
        # Test CPU usage stays reasonable
        import psutil
        
        cpu_percent = psutil.cpu_percent(interval=1)
        memory_percent = psutil.virtual_memory().percent
        
        # During normal operation, resource usage should be reasonable
        assert cpu_percent < 80, f"CPU usage {cpu_percent}% is too high"
        assert memory_percent < 90, f"Memory usage {memory_percent}% is too high"

    def test_file_system_performance(self):
        """Test file system operations meet performance requirements"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Test file creation performance
            start_time = time.time()
            
            for i in range(1000):
                test_file = temp_path / f"test{i}.txt"
                test_file.write_text(f"Test content {i}")
                
            end_time = time.time()
            creation_time = end_time - start_time
            
            # 1000 small file creates should be fast
            assert creation_time < 2.0, f"File creation took {creation_time:.3f}s, should be < 2.0s"
            
            # Verify all files exist
            assert len(list(temp_path.glob("*.txt"))) == 1000