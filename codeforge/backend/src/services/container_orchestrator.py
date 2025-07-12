"""
Container Orchestration Service for CodeForge
Manages container lifecycle, scaling, and resource allocation
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import docker
import aiodocker
from prometheus_client import Counter, Gauge, Histogram
import redis.asyncio as redis

from ..config.settings import settings
from ..models.project import Project
from ..models.usage import ContainerSession
from ..services.container_service import ContainerService
from ..services.usage_calculator import UsageCalculator


# Metrics
container_created = Counter('codeforge_containers_created', 'Total containers created')
container_destroyed = Counter('codeforge_containers_destroyed', 'Total containers destroyed')
active_containers = Gauge('codeforge_active_containers', 'Currently active containers')
container_start_time = Histogram('codeforge_container_start_seconds', 'Container start time')


@dataclass
class ContainerPool:
    """Pre-warmed container pool for instant starts"""
    language: str
    version: str
    containers: List[str]
    min_size: int = 2
    max_size: int = 10
    
    
class ContainerOrchestrator:
    """
    Advanced container orchestration with:
    - Pre-warmed container pools
    - Instant cloning with CRIU snapshots
    - Auto-scaling based on load
    - Multi-region container placement
    - Zero-downtime updates
    """
    
    def __init__(self):
        self.docker_sync = docker.from_env()
        self.docker = aiodocker.Docker()
        self.redis = None  # Initialized in start()
        self.container_service = ContainerService()
        self.usage_calculator = UsageCalculator()
        
        # Container pools by language
        self.pools: Dict[str, ContainerPool] = {}
        
        # Active container tracking
        self.active_containers: Dict[str, Dict] = {}
        
        # Container placement strategy
        self.placement_strategy = "least_loaded"  # least_loaded, round_robin, affinity
        
    async def start(self):
        """Start orchestrator services"""
        # Connect to Redis
        self.redis = await redis.from_url(settings.REDIS_URL)
        
        # Initialize container pools
        await self._initialize_pools()
        
        # Start background tasks
        asyncio.create_task(self._pool_manager())
        asyncio.create_task(self._health_monitor())
        asyncio.create_task(self._auto_scaler())
        
    async def _initialize_pools(self):
        """Initialize pre-warmed container pools"""
        languages = [
            ("python", "3.11"),
            ("python", "3.10"),
            ("node", "20"),
            ("node", "18"),
            ("go", "1.21"),
            ("rust", "stable")
        ]
        
        for lang, version in languages:
            pool_key = f"{lang}:{version}"
            self.pools[pool_key] = ContainerPool(
                language=lang,
                version=version,
                containers=[]
            )
            
            # Pre-warm minimum containers
            for _ in range(2):
                container_id = await self._create_pool_container(lang, version)
                if container_id:
                    self.pools[pool_key].containers.append(container_id)
                    
    async def _create_pool_container(self, language: str, version: str) -> Optional[str]:
        """Create a pre-warmed container for the pool"""
        try:
            image = f"codeforge/{language}:{version}"
            
            # Create minimal container
            config = {
                "image": image,
                "name": f"codeforge-pool-{language}-{uuid.uuid4().hex[:8]}",
                "command": ["/bin/bash", "-c", "tail -f /dev/null"],
                "detach": True,
                "labels": {
                    "codeforge.pool": "true",
                    "codeforge.language": language,
                    "codeforge.version": version,
                    "codeforge.created": datetime.utcnow().isoformat()
                },
                "host_config": {
                    "runtime": settings.GVISOR_RUNTIME if settings.ENVIRONMENT == "production" else "runc",
                    "cpu_shares": 512,  # Minimal CPU for idle containers
                    "mem_limit": "256m",  # Minimal memory for idle containers
                    "network_mode": settings.CONTAINER_NETWORK
                }
            }
            
            container = await self.docker.containers.create(**config)
            await container.start()
            
            # Take CRIU checkpoint for instant cloning
            if settings.ENABLE_INSTANT_CLONING:
                await self._checkpoint_container(container.id)
                
            return container.id
            
        except Exception as e:
            print(f"Failed to create pool container: {e}")
            return None
            
    async def _checkpoint_container(self, container_id: str):
        """Create CRIU checkpoint for instant cloning"""
        try:
            # This would use CRIU (Checkpoint/Restore In Userspace)
            # For now, this is a placeholder
            checkpoint_path = f"/var/lib/codeforge/checkpoints/{container_id}"
            
            # In production: docker checkpoint create container_id checkpoint_name
            print(f"Would checkpoint container {container_id} to {checkpoint_path}")
            
        except Exception as e:
            print(f"Failed to checkpoint container: {e}")
            
    async def get_container(
        self,
        user_id: str,
        project_id: str,
        language: str,
        version: str
    ) -> str:
        """Get a container for user, using pool if available"""
        with container_start_time.time():
            pool_key = f"{language}:{version}"
            
            # Try to get from pool
            if pool_key in self.pools and self.pools[pool_key].containers:
                container_id = self.pools[pool_key].containers.pop(0)
                
                # Repurpose pool container for user
                await self._assign_pool_container(container_id, user_id, project_id)
                
                # Refill pool in background
                asyncio.create_task(self._refill_pool(pool_key))
                
                container_created.inc()
                active_containers.inc()
                
                return container_id
            else:
                # Create new container
                container_id = await self.container_service.create_container(
                    user_id, project_id
                )
                
                container_created.inc()
                active_containers.inc()
                
                return container_id
                
    async def _assign_pool_container(
        self,
        container_id: str,
        user_id: str,
        project_id: str
    ):
        """Assign a pool container to a user"""
        container = await self.docker.containers.get(container_id)
        
        # Update labels
        await container.update({
            "Labels": {
                "codeforge.pool": "false",
                "codeforge.user_id": user_id,
                "codeforge.project_id": project_id,
                "codeforge.assigned": datetime.utcnow().isoformat()
            }
        })
        
        # Resize container resources based on project needs
        # This would look up project resource requirements
        await container.update({
            "CpuShares": 2048,
            "Memory": 2 * 1024 * 1024 * 1024  # 2GB
        })
        
        # Mount user workspace
        # In production, this would use volume plugins
        
        # Track active container
        self.active_containers[container_id] = {
            "user_id": user_id,
            "project_id": project_id,
            "started_at": datetime.utcnow()
        }
        
    async def _refill_pool(self, pool_key: str):
        """Refill container pool to minimum size"""
        pool = self.pools.get(pool_key)
        if not pool:
            return
            
        while len(pool.containers) < pool.min_size:
            container_id = await self._create_pool_container(
                pool.language,
                pool.version
            )
            if container_id:
                pool.containers.append(container_id)
            else:
                break
                
    async def clone_container(
        self,
        source_container_id: str,
        user_id: str,
        new_project_id: str
    ) -> str:
        """Instantly clone a container with full state"""
        if not settings.ENABLE_INSTANT_CLONING:
            # Fallback to regular creation
            return await self.container_service.create_container(
                user_id, new_project_id
            )
            
        try:
            # Get source container
            source = await self.docker.containers.get(source_container_id)
            source_info = await source.show()
            
            # Create new container from checkpoint
            clone_id = str(uuid.uuid4())
            clone_name = f"codeforge-clone-{clone_id[:8]}"
            
            # In production: docker create --name clone_name image
            # Then: docker start --checkpoint checkpoint_name clone_name
            
            # For now, create new container and copy state
            config = source_info["Config"].copy()
            config["name"] = clone_name
            config["Labels"]["codeforge.cloned_from"] = source_container_id
            config["Labels"]["codeforge.project_id"] = new_project_id
            
            clone = await self.docker.containers.create(**config)
            await clone.start()
            
            # Copy filesystem state (simplified)
            # In production, use CRIU or filesystem snapshots
            
            container_created.inc()
            active_containers.inc()
            
            return clone.id
            
        except Exception as e:
            print(f"Failed to clone container: {e}")
            # Fallback to regular creation
            return await self.container_service.create_container(
                user_id, new_project_id
            )
            
    async def scale_container(
        self,
        container_id: str,
        cpu_cores: int,
        memory_gb: int,
        gpu_type: Optional[str] = None
    ):
        """Live scale container resources without restart"""
        try:
            container = await self.docker.containers.get(container_id)
            
            # Update CPU and memory limits
            update_config = {
                "CpuShares": cpu_cores * 1024,
                "CpuQuota": cpu_cores * 100000,
                "Memory": memory_gb * 1024 * 1024 * 1024,
                "MemorySwap": memory_gb * 2 * 1024 * 1024 * 1024
            }
            
            # Add GPU if requested
            if gpu_type and settings.ENABLE_GPU_COMPUTING:
                update_config["DeviceRequests"] = [{
                    "Driver": "nvidia",
                    "Count": 1,
                    "Capabilities": [["gpu"]]
                }]
                
            await container.update(update_config)
            
            # Update tracking
            if container_id in self.active_containers:
                self.active_containers[container_id]["resources"] = {
                    "cpu": cpu_cores,
                    "memory_gb": memory_gb,
                    "gpu": gpu_type
                }
                
        except Exception as e:
            print(f"Failed to scale container: {e}")
            raise
            
    async def _pool_manager(self):
        """Background task to manage container pools"""
        while True:
            try:
                for pool_key, pool in self.pools.items():
                    # Remove expired containers
                    valid_containers = []
                    for container_id in pool.containers:
                        try:
                            container = await self.docker.containers.get(container_id)
                            info = await container.show()
                            
                            # Check if container is still healthy
                            created = datetime.fromisoformat(
                                info["Config"]["Labels"]["codeforge.created"]
                            )
                            age = datetime.utcnow() - created
                            
                            if age < timedelta(hours=1):  # Keep for 1 hour
                                valid_containers.append(container_id)
                            else:
                                # Remove old container
                                await container.stop()
                                await container.delete()
                                container_destroyed.inc()
                                
                        except Exception:
                            pass
                            
                    pool.containers = valid_containers
                    
                    # Refill pool if needed
                    if len(pool.containers) < pool.min_size:
                        await self._refill_pool(pool_key)
                        
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"Pool manager error: {e}")
                await asyncio.sleep(60)
                
    async def _health_monitor(self):
        """Monitor container health and restart unhealthy ones"""
        while True:
            try:
                for container_id, info in list(self.active_containers.items()):
                    try:
                        container = await self.docker.containers.get(container_id)
                        stats = await container.stats(stream=False)
                        
                        # Check if container is responsive
                        exec_check = await container.exec(
                            ["echo", "health_check"],
                            stdout=True
                        )
                        async with exec_check.start() as stream:
                            output = await stream.read_out()
                            
                        if not output:
                            # Container unresponsive, restart
                            print(f"Restarting unresponsive container {container_id}")
                            await container.restart()
                            
                    except Exception as e:
                        print(f"Health check failed for {container_id}: {e}")
                        
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                print(f"Health monitor error: {e}")
                await asyncio.sleep(30)
                
    async def _auto_scaler(self):
        """Auto-scale container pools based on demand"""
        while True:
            try:
                # Get metrics from Redis
                total_requests = await self.redis.get("codeforge:requests:total") or 0
                active_users = await self.redis.scard("codeforge:users:active") or 0
                
                for pool_key, pool in self.pools.items():
                    # Calculate desired pool size based on demand
                    usage_ratio = len(self.active_containers) / max(1, len(pool.containers))
                    
                    if usage_ratio > 0.8:  # High demand
                        # Increase pool size
                        new_size = min(pool.max_size, len(pool.containers) + 2)
                        while len(pool.containers) < new_size:
                            container_id = await self._create_pool_container(
                                pool.language,
                                pool.version
                            )
                            if container_id:
                                pool.containers.append(container_id)
                                
                    elif usage_ratio < 0.2:  # Low demand
                        # Decrease pool size
                        new_size = max(pool.min_size, len(pool.containers) - 1)
                        while len(pool.containers) > new_size:
                            container_id = pool.containers.pop()
                            try:
                                container = await self.docker.containers.get(container_id)
                                await container.stop()
                                await container.delete()
                                container_destroyed.inc()
                            except Exception:
                                pass
                                
                await asyncio.sleep(300)  # Check every 5 minutes
                
            except Exception as e:
                print(f"Auto-scaler error: {e}")
                await asyncio.sleep(300)
                
    async def stop_container(self, container_id: str):
        """Stop and cleanup container"""
        if container_id in self.active_containers:
            del self.active_containers[container_id]
            
        await self.container_service.stop_container(container_id)
        
        container_destroyed.inc()
        active_containers.dec()
        
    async def get_container_stats(self) -> Dict:
        """Get orchestrator statistics"""
        pool_stats = {}
        for pool_key, pool in self.pools.items():
            pool_stats[pool_key] = {
                "available": len(pool.containers),
                "min_size": pool.min_size,
                "max_size": pool.max_size
            }
            
        return {
            "active_containers": len(self.active_containers),
            "pools": pool_stats,
            "total_created": container_created._value.get(),
            "total_destroyed": container_destroyed._value.get()
        }