"""
Database Provisioner Service
"""
import asyncio
import secrets
import uuid
from typing import Dict, Optional, Any, List
from datetime import datetime, timedelta
import aiodocker
import logging
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import json

from ...models.database import (
    DatabaseInstance, DBType, DBSize, DBStatus,
    DatabaseBranch, DatabaseMetrics
)
from ...models.project import Project
from ...database.connection import get_db
from ...config.settings import settings
from ..container_service import ContainerService
from ...utils.crypto import encrypt_string, decrypt_string


logger = logging.getLogger(__name__)


class DatabaseProvisioner:
    """
    Service for provisioning and managing database instances
    """
    
    def __init__(self):
        self.container_service = ContainerService()
        self._size_config = {
            DBSize.MICRO: {
                "cpu": 0.5,
                "memory_gb": 0.5,
                "storage_gb": 5,
                "max_connections": 50,
                "cost_per_hour": 0.01
            },
            DBSize.SMALL: {
                "cpu": 1,
                "memory_gb": 1,
                "storage_gb": 10,
                "max_connections": 100,
                "cost_per_hour": 0.05
            },
            DBSize.MEDIUM: {
                "cpu": 2,
                "memory_gb": 4,
                "storage_gb": 50,
                "max_connections": 200,
                "cost_per_hour": 0.20
            },
            DBSize.LARGE: {
                "cpu": 4,
                "memory_gb": 8,
                "storage_gb": 100,
                "max_connections": 500,
                "cost_per_hour": 0.80
            }
        }
        
        self._db_images = {
            DBType.POSTGRESQL: {
                "15": "postgres:15-alpine",
                "14": "postgres:14-alpine",
                "13": "postgres:13-alpine"
            },
            DBType.MYSQL: {
                "8.0": "mysql:8.0",
                "5.7": "mysql:5.7"
            }
        }
    
    async def provision_database(
        self,
        project_id: str,
        db_type: DBType,
        version: str,
        size: DBSize,
        region: str,
        name: str,
        user_id: str,
        db: Session
    ) -> DatabaseInstance:
        """
        Provision a new database instance
        
        Args:
            project_id: ID of the project
            db_type: Type of database (PostgreSQL, MySQL)
            version: Database version
            size: Instance size
            region: Deployment region
            name: Name of the database
            user_id: ID of the user creating the database
            db: Database session
            
        Returns:
            DatabaseInstance: Created database instance
        """
        try:
            # Validate project exists and user has access
            project = db.query(Project).filter(
                Project.id == project_id,
                Project.owner_id == user_id
            ).first()
            
            if not project:
                raise ValueError(f"Project {project_id} not found or access denied")
            
            # Check database limit for project
            existing_dbs = db.query(DatabaseInstance).filter(
                DatabaseInstance.project_id == project_id,
                DatabaseInstance.status != DBStatus.DELETING
            ).count()
            
            if existing_dbs >= settings.MAX_DATABASES_PER_PROJECT:
                raise ValueError(f"Project has reached database limit ({settings.MAX_DATABASES_PER_PROJECT})")
            
            # Generate unique identifiers
            instance_id = f"db-{uuid.uuid4().hex[:12]}"
            db_name = f"codeforge_{project_id.replace('-', '_')}"
            username = f"user_{uuid.uuid4().hex[:8]}"
            password = secrets.token_urlsafe(16)
            
            # Get size configuration
            size_config = self._size_config[size]
            
            # Create database instance record
            db_instance = DatabaseInstance(
                id=instance_id,
                project_id=project_id,
                name=name,
                db_type=db_type,
                version=version,
                size=size,
                region=region,
                status=DBStatus.PROVISIONING,
                database_name=db_name,
                username=username,
                password_encrypted=encrypt_string(password),
                storage_gb=size_config["storage_gb"],
                cpu_cores=size_config["cpu"],
                memory_gb=size_config["memory_gb"],
                connection_pool_size=size_config["max_connections"],
                created_by=user_id,
                backup_schedule="0 2 * * *",  # Daily at 2 AM
                config={
                    "max_connections": size_config["max_connections"],
                    "shared_buffers": f"{int(size_config['memory_gb'] * 256)}MB",
                    "effective_cache_size": f"{int(size_config['memory_gb'] * 768)}MB"
                }
            )
            
            db.add(db_instance)
            db.commit()
            
            # Create default branch
            default_branch = DatabaseBranch(
                id=f"branch-{uuid.uuid4().hex[:12]}",
                instance_id=instance_id,
                name="main",
                is_default=True,
                created_by=user_id,
                use_cow=True
            )
            
            db.add(default_branch)
            db.commit()
            
            # Provision the actual database container asynchronously
            asyncio.create_task(self._provision_container(
                db_instance, password, db
            ))
            
            return db_instance
            
        except Exception as e:
            logger.error(f"Failed to provision database: {str(e)}")
            db.rollback()
            raise
    
    async def _provision_container(
        self,
        instance: DatabaseInstance,
        password: str,
        db: Session
    ):
        """
        Provision the actual database container
        """
        try:
            # Get the appropriate Docker image
            if instance.version not in self._db_images[instance.db_type]:
                raise ValueError(f"Unsupported database version: {instance.version}")
            
            image = self._db_images[instance.db_type][instance.version]
            
            # Prepare environment variables
            env_vars = self._get_db_env_vars(instance, password)
            
            # Create container configuration
            container_config = {
                "Image": image,
                "Env": [f"{k}={v}" for k, v in env_vars.items()],
                "ExposedPorts": {
                    f"{self._get_default_port(instance.db_type)}/tcp": {}
                },
                "HostConfig": {
                    "Memory": int(instance.memory_gb * 1024 * 1024 * 1024),
                    "CpuQuota": int(instance.cpu_cores * 100000),
                    "CpuPeriod": 100000,
                    "Binds": [
                        f"{instance.id}-data:/var/lib/{self._get_data_dir(instance.db_type)}"
                    ],
                    "PortBindings": {
                        f"{self._get_default_port(instance.db_type)}/tcp": [
                            {"HostPort": "0"}  # Let Docker assign a random port
                        ]
                    },
                    "RestartPolicy": {
                        "Name": "unless-stopped"
                    }
                },
                "Labels": {
                    "codeforge.database": "true",
                    "codeforge.instance_id": instance.id,
                    "codeforge.project_id": instance.project_id,
                    "codeforge.db_type": instance.db_type.value
                }
            }
            
            # Create and start the container
            docker = aiodocker.Docker()
            try:
                # Pull the image if needed
                await self._pull_image_if_needed(docker, image)
                
                # Create the container
                container = await docker.containers.create(
                    config=container_config,
                    name=f"codeforge-db-{instance.id}"
                )
                
                # Start the container
                await container.start()
                
                # Get container info to find the assigned port
                container_info = await container.show()
                port_info = container_info["NetworkSettings"]["Ports"]
                default_port = self._get_default_port(instance.db_type)
                host_port = port_info[f"{default_port}/tcp"][0]["HostPort"]
                
                # Update instance with connection details
                instance.host = "localhost"  # In production, this would be the actual host
                instance.port = int(host_port)
                instance.status = DBStatus.READY
                
                db.add(instance)
                db.commit()
                
                # Wait for database to be ready
                await self._wait_for_database(instance, password)
                
                # Initialize database schema
                await self._initialize_database(instance, password)
                
                logger.info(f"Successfully provisioned database {instance.id}")
                
            finally:
                await docker.close()
                
        except Exception as e:
            logger.error(f"Failed to provision container for database {instance.id}: {str(e)}")
            instance.status = DBStatus.ERROR
            db.add(instance)
            db.commit()
            raise
    
    def _get_db_env_vars(self, instance: DatabaseInstance, password: str) -> Dict[str, str]:
        """Get environment variables for database container"""
        if instance.db_type == DBType.POSTGRESQL:
            return {
                "POSTGRES_USER": instance.username,
                "POSTGRES_PASSWORD": password,
                "POSTGRES_DB": instance.database_name,
                "POSTGRES_INITDB_ARGS": "--encoding=UTF-8 --lc-collate=en_US.utf8 --lc-ctype=en_US.utf8"
            }
        elif instance.db_type == DBType.MYSQL:
            return {
                "MYSQL_ROOT_PASSWORD": password,
                "MYSQL_DATABASE": instance.database_name,
                "MYSQL_USER": instance.username,
                "MYSQL_PASSWORD": password
            }
        else:
            raise ValueError(f"Unsupported database type: {instance.db_type}")
    
    def _get_default_port(self, db_type: DBType) -> int:
        """Get default port for database type"""
        return 5432 if db_type == DBType.POSTGRESQL else 3306
    
    def _get_data_dir(self, db_type: DBType) -> str:
        """Get data directory for database type"""
        return "postgresql/data" if db_type == DBType.POSTGRESQL else "mysql"
    
    async def _pull_image_if_needed(self, docker: aiodocker.Docker, image: str):
        """Pull Docker image if not present"""
        try:
            await docker.images.inspect(image)
        except aiodocker.exceptions.DockerError:
            logger.info(f"Pulling image {image}...")
            await docker.images.pull(image)
    
    async def _wait_for_database(self, instance: DatabaseInstance, password: str, timeout: int = 60):
        """Wait for database to be ready"""
        import asyncpg
        import aiomysql
        
        start_time = datetime.now()
        
        while (datetime.now() - start_time).seconds < timeout:
            try:
                if instance.db_type == DBType.POSTGRESQL:
                    conn = await asyncpg.connect(
                        host=instance.host,
                        port=instance.port,
                        user=instance.username,
                        password=password,
                        database=instance.database_name
                    )
                    await conn.close()
                    return
                elif instance.db_type == DBType.MYSQL:
                    conn = await aiomysql.connect(
                        host=instance.host,
                        port=instance.port,
                        user=instance.username,
                        password=password,
                        db=instance.database_name
                    )
                    conn.close()
                    return
            except Exception:
                await asyncio.sleep(2)
        
        raise TimeoutError(f"Database {instance.id} did not become ready in {timeout} seconds")
    
    async def _initialize_database(self, instance: DatabaseInstance, password: str):
        """Initialize database with CodeForge schema"""
        # This would create any necessary tables, extensions, etc.
        # For now, we'll just log
        logger.info(f"Initializing database schema for {instance.id}")
    
    async def get_connection_string(
        self,
        instance_id: str,
        branch: str = "main",
        user_id: str = None,
        db: Session = None
    ) -> str:
        """
        Get connection string for a database instance
        
        Args:
            instance_id: Database instance ID
            branch: Branch name (default: main)
            user_id: User ID for access check
            db: Database session
            
        Returns:
            str: Connection string
        """
        if not db:
            db = get_db()
            
        # Get instance and verify access
        instance = db.query(DatabaseInstance).filter(
            DatabaseInstance.id == instance_id
        ).first()
        
        if not instance:
            raise ValueError(f"Database instance {instance_id} not found")
        
        if user_id:
            # Verify user has access to the project
            project = db.query(Project).filter(
                Project.id == instance.project_id,
                Project.owner_id == user_id
            ).first()
            
            if not project:
                raise ValueError("Access denied")
        
        # Decrypt password
        password = decrypt_string(instance.password_encrypted)
        
        # Build connection string based on database type
        if instance.db_type == DBType.POSTGRESQL:
            return (
                f"postgresql://{instance.username}:{password}@"
                f"{instance.host}:{instance.port}/{instance.database_name}"
            )
        elif instance.db_type == DBType.MYSQL:
            return (
                f"mysql://{instance.username}:{password}@"
                f"{instance.host}:{instance.port}/{instance.database_name}"
            )
        else:
            raise ValueError(f"Unsupported database type: {instance.db_type}")
    
    async def delete_database(
        self,
        instance_id: str,
        user_id: str,
        db: Session
    ) -> None:
        """
        Delete a database instance
        
        Args:
            instance_id: Database instance ID
            user_id: User ID for access check
            db: Database session
        """
        try:
            # Get instance and verify ownership
            instance = db.query(DatabaseInstance).filter(
                DatabaseInstance.id == instance_id
            ).first()
            
            if not instance:
                raise ValueError(f"Database instance {instance_id} not found")
            
            # Verify user owns the project
            project = db.query(Project).filter(
                Project.id == instance.project_id,
                Project.owner_id == user_id
            ).first()
            
            if not project:
                raise ValueError("Access denied")
            
            # Mark as deleting
            instance.status = DBStatus.DELETING
            db.commit()
            
            # Delete the container
            await self._delete_container(instance)
            
            # Delete from database
            db.delete(instance)
            db.commit()
            
            logger.info(f"Successfully deleted database {instance_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete database {instance_id}: {str(e)}")
            db.rollback()
            raise
    
    async def _delete_container(self, instance: DatabaseInstance):
        """Delete the database container"""
        docker = aiodocker.Docker()
        try:
            container_name = f"codeforge-db-{instance.id}"
            try:
                container = await docker.containers.get(container_name)
                await container.stop()
                await container.delete()
            except aiodocker.exceptions.DockerError:
                logger.warning(f"Container {container_name} not found")
                
            # Delete the volume
            try:
                volume = await docker.volumes.get(f"{instance.id}-data")
                await volume.delete()
            except aiodocker.exceptions.DockerError:
                logger.warning(f"Volume {instance.id}-data not found")
                
        finally:
            await docker.close()
    
    async def list_databases(
        self,
        project_id: str,
        user_id: str,
        db: Session
    ) -> List[DatabaseInstance]:
        """
        List all databases for a project
        
        Args:
            project_id: Project ID
            user_id: User ID for access check
            db: Database session
            
        Returns:
            List[DatabaseInstance]: List of database instances
        """
        # Verify user has access to project
        project = db.query(Project).filter(
            Project.id == project_id,
            Project.owner_id == user_id
        ).first()
        
        if not project:
            raise ValueError("Project not found or access denied")
        
        # Get all databases for project
        databases = db.query(DatabaseInstance).filter(
            DatabaseInstance.project_id == project_id,
            DatabaseInstance.status != DBStatus.DELETING
        ).all()
        
        return databases
    
    async def get_database_metrics(
        self,
        instance_id: str,
        user_id: str,
        db: Session
    ) -> Dict[str, Any]:
        """
        Get metrics for a database instance
        
        Args:
            instance_id: Database instance ID
            user_id: User ID for access check
            db: Database session
            
        Returns:
            Dict[str, Any]: Database metrics
        """
        # Verify access
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
        
        # Get latest metrics
        latest_metrics = db.query(DatabaseMetrics).filter(
            DatabaseMetrics.instance_id == instance_id
        ).order_by(DatabaseMetrics.recorded_at.desc()).first()
        
        if not latest_metrics:
            return {
                "cpu_usage": 0,
                "memory_usage": 0,
                "disk_usage": 0,
                "connections": 0,
                "queries_per_second": 0
            }
        
        return {
            "cpu_usage": latest_metrics.cpu_usage_percent,
            "memory_usage": latest_metrics.memory_usage_percent,
            "disk_usage": latest_metrics.disk_usage_percent,
            "connections": latest_metrics.active_connections,
            "queries_per_second": latest_metrics.queries_per_second,
            "database_size_gb": latest_metrics.database_size_gb,
            "cache_hit_ratio": latest_metrics.cache_hit_ratio
        }