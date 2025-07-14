"""
Edge Deployment Service for global deployment to 300+ edge locations
"""
import asyncio
import aiohttp
import zipfile
import hashlib
import tempfile
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from sqlalchemy.orm import Session
import json
import random

from ...models.infrastructure import EdgeDeployment, EdgeDeploymentStatus
from ...config.settings import settings
from ..credits_service import CreditsService


logger = logging.getLogger(__name__)


class EdgeLocation:
    """Edge location information"""
    
    def __init__(self, code: str, name: str, country: str, continent: str, lat: float, lng: float):
        self.code = code
        self.name = name
        self.country = country
        self.continent = continent
        self.lat = lat
        self.lng = lng
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "country": self.country,
            "continent": self.continent,
            "coordinates": {"lat": self.lat, "lng": self.lng}
        }


class EdgeLocationManager:
    """Manages edge locations and deployment strategies"""
    
    def __init__(self):
        self.locations = self._initialize_edge_locations()
    
    def _initialize_edge_locations(self) -> Dict[str, EdgeLocation]:
        """Initialize edge locations database"""
        # Sample of 300+ edge locations (simplified for demo)
        locations_data = [
            # North America
            ("us-east-1", "N. Virginia", "US", "North America", 38.13, -78.45),
            ("us-east-2", "Ohio", "US", "North America", 40.41, -82.9),
            ("us-west-1", "N. California", "US", "North America", 37.35, -121.96),
            ("us-west-2", "Oregon", "US", "North America", 45.85, -119.7),
            ("ca-central-1", "Canada Central", "CA", "North America", 56.13, -106.35),
            
            # Europe
            ("eu-west-1", "Ireland", "IE", "Europe", 53.41, -8.24),
            ("eu-west-2", "London", "GB", "Europe", 51.51, -0.126),
            ("eu-west-3", "Paris", "FR", "Europe", 48.86, 2.35),
            ("eu-central-1", "Frankfurt", "DE", "Europe", 50.11, 8.68),
            ("eu-north-1", "Stockholm", "SE", "Europe", 59.33, 18.06),
            
            # Asia Pacific
            ("ap-southeast-1", "Singapore", "SG", "Asia Pacific", 1.29, 103.85),
            ("ap-southeast-2", "Sydney", "AU", "Asia Pacific", -33.86, 151.21),
            ("ap-northeast-1", "Tokyo", "JP", "Asia Pacific", 35.68, 139.69),
            ("ap-northeast-2", "Seoul", "KR", "Asia Pacific", 37.57, 126.98),
            ("ap-south-1", "Mumbai", "IN", "Asia Pacific", 19.08, 72.88),
            
            # South America
            ("sa-east-1", "São Paulo", "BR", "South America", -23.55, -46.64),
            
            # Africa
            ("af-south-1", "Cape Town", "ZA", "Africa", -33.92, 18.42),
            
            # Middle East
            ("me-south-1", "Bahrain", "BH", "Middle East", 26.07, 50.55),
        ]
        
        # Generate additional locations for demo (up to 300+)
        base_locations = {}
        for code, name, country, continent, lat, lng in locations_data:
            base_locations[code] = EdgeLocation(code, name, country, continent, lat, lng)
        
        # Add more locations by creating variants
        additional_locations = {}
        location_counter = len(base_locations)
        
        for i in range(300 - len(base_locations)):
            base_code = random.choice(list(base_locations.keys()))
            base_location = base_locations[base_code]
            
            variant_code = f"{base_code}-{i+1}"
            variant_name = f"{base_location.name} Edge {i+1}"
            
            # Slightly vary coordinates
            lat_offset = random.uniform(-2, 2)
            lng_offset = random.uniform(-2, 2)
            
            additional_locations[variant_code] = EdgeLocation(
                variant_code,
                variant_name,
                base_location.country,
                base_location.continent,
                base_location.lat + lat_offset,
                base_location.lng + lng_offset
            )
        
        base_locations.update(additional_locations)
        return base_locations
    
    def get_optimal_locations(
        self,
        target_regions: List[str] = None,
        max_locations: int = 10
    ) -> List[EdgeLocation]:
        """Get optimal edge locations for deployment"""
        if target_regions:
            # Filter by target regions
            filtered_locations = [
                loc for loc in self.locations.values()
                if loc.continent in target_regions
            ]
        else:
            # Use all locations
            filtered_locations = list(self.locations.values())
        
        # For demonstration, return a diverse set of locations
        if len(filtered_locations) > max_locations:
            # Ensure geographic diversity
            continents = {}
            for loc in filtered_locations:
                if loc.continent not in continents:
                    continents[loc.continent] = []
                continents[loc.continent].append(loc)
            
            selected = []
            locations_per_continent = max_locations // len(continents)
            
            for continent_locations in continents.values():
                selected.extend(continent_locations[:locations_per_continent])
            
            # Fill remaining slots
            remaining = max_locations - len(selected)
            if remaining > 0:
                all_remaining = [loc for loc in filtered_locations if loc not in selected]
                selected.extend(all_remaining[:remaining])
            
            return selected[:max_locations]
        
        return filtered_locations
    
    def get_location_by_code(self, code: str) -> Optional[EdgeLocation]:
        """Get edge location by code"""
        return self.locations.get(code)
    
    def get_all_locations(self) -> List[EdgeLocation]:
        """Get all edge locations"""
        return list(self.locations.values())


class EdgeRuntime:
    """Edge runtime environment management"""
    
    SUPPORTED_RUNTIMES = {
        "nodejs": ["16", "18", "20"],
        "python": ["3.9", "3.10", "3.11"],
        "deno": ["1.30", "1.35", "1.40"],
        "wasm": ["1.0"],
        "rust": ["1.70", "1.75"],
        "go": ["1.19", "1.20", "1.21"]
    }
    
    @classmethod
    def validate_runtime(cls, runtime: str, version: str) -> bool:
        """Validate runtime and version combination"""
        return runtime in cls.SUPPORTED_RUNTIMES and version in cls.SUPPORTED_RUNTIMES[runtime]
    
    @classmethod
    def get_default_version(cls, runtime: str) -> Optional[str]:
        """Get default version for runtime"""
        versions = cls.SUPPORTED_RUNTIMES.get(runtime)
        return versions[-1] if versions else None


class EdgeDeploymentService:
    """
    Service for managing edge deployments and global distribution
    """
    
    def __init__(self, db: Session, credits_service: Optional[CreditsService] = None):
        self.db = db
        self.credits_service = credits_service or CreditsService(db)
        self.location_manager = EdgeLocationManager()
    
    async def create_edge_deployment(
        self,
        project_id: str,
        user_id: str,
        name: str,
        code_bundle: bytes,
        runtime: str = "nodejs",
        runtime_version: str = "18",
        configuration: Optional[Dict[str, Any]] = None
    ) -> EdgeDeployment:
        """
        Create a new edge deployment
        """
        # Validate runtime
        if not EdgeRuntime.validate_runtime(runtime, runtime_version):
            raise ValueError(f"Unsupported runtime: {runtime} {runtime_version}")
        
        # Default configuration
        default_config = {
            "memory_limit": 512,
            "timeout": 30,
            "environment_variables": {},
            "target_regions": ["North America", "Europe", "Asia Pacific"],
            "deployment_strategy": "rolling",
            "max_edge_locations": 20
        }
        
        if configuration:
            default_config.update(configuration)
        
        # Generate code checksum
        code_checksum = hashlib.sha256(code_bundle).hexdigest()
        
        # Store code bundle (in production, this would go to object storage)
        code_bundle_url = await self._store_code_bundle(code_bundle, code_checksum)
        
        # Select optimal edge locations
        edge_locations = self.location_manager.get_optimal_locations(
            target_regions=default_config["target_regions"],
            max_locations=default_config["max_edge_locations"]
        )
        
        # Create edge deployment record
        edge_deployment = EdgeDeployment(
            project_id=project_id,
            user_id=user_id,
            name=name,
            version="1.0.0",
            runtime=runtime,
            runtime_version=runtime_version,
            memory_limit=default_config["memory_limit"],
            timeout=default_config["timeout"],
            code_bundle_url=code_bundle_url,
            code_checksum=code_checksum,
            environment_variables=default_config["environment_variables"],
            edge_locations=[loc.to_dict() for loc in edge_locations],
            deployment_strategy=default_config["deployment_strategy"],
            status=EdgeDeploymentStatus.PENDING
        )
        
        self.db.add(edge_deployment)
        self.db.commit()
        
        # Start deployment process
        asyncio.create_task(self._deploy_to_edge_locations(edge_deployment.id))
        
        return edge_deployment
    
    async def _store_code_bundle(self, code_bundle: bytes, checksum: str) -> str:
        """Store code bundle and return URL"""
        # In production, this would upload to S3, GCS, or similar
        # For demo, we'll simulate storage
        filename = f"edge-{checksum[:16]}.zip"
        storage_url = f"https://edge-storage.codeforge.dev/bundles/{filename}"
        
        # Simulate upload delay
        await asyncio.sleep(1)
        
        return storage_url
    
    async def _deploy_to_edge_locations(self, deployment_id: str):
        """Deploy code to edge locations"""
        deployment = self.db.query(EdgeDeployment).filter(EdgeDeployment.id == deployment_id).first()
        if not deployment:
            return
        
        try:
            deployment.status = EdgeDeploymentStatus.DEPLOYING
            self.db.commit()
            
            # Simulate deployment to edge locations
            total_locations = len(deployment.edge_locations)
            
            if deployment.deployment_strategy == "rolling":
                # Deploy to locations one by one
                for i, location in enumerate(deployment.edge_locations):
                    await self._deploy_to_location(deployment, location)
                    
                    # Update progress
                    progress = (i + 1) / total_locations
                    logger.info(f"Deployed to {location['name']} ({progress*100:.1f}%)")
                    
                    # Small delay between deployments
                    await asyncio.sleep(0.5)
            
            elif deployment.deployment_strategy == "blue_green":
                # Deploy to all locations simultaneously (blue environment)
                deploy_tasks = [
                    self._deploy_to_location(deployment, location)
                    for location in deployment.edge_locations
                ]
                await asyncio.gather(*deploy_tasks)
                
                # Switch traffic (green environment)
                await asyncio.sleep(2)
            
            elif deployment.deployment_strategy == "canary":
                # Deploy to a subset first (canary)
                canary_locations = deployment.edge_locations[:2]
                remaining_locations = deployment.edge_locations[2:]
                
                # Deploy canary
                for location in canary_locations:
                    await self._deploy_to_location(deployment, location)
                
                # Wait and check health
                await asyncio.sleep(5)
                
                # Deploy to remaining locations
                for location in remaining_locations:
                    await self._deploy_to_location(deployment, location)
            
            # Generate deployment URL
            deployment.deployment_url = f"https://{deployment.name}-{deployment.id[:8]}.edge.codeforge.dev"
            deployment.status = EdgeDeploymentStatus.ACTIVE
            deployment.last_deployed_at = datetime.utcnow()
            
            self.db.commit()
            
            logger.info(f"Edge deployment {deployment_id} completed successfully")
            
        except Exception as e:
            logger.error(f"Edge deployment failed for {deployment_id}: {e}")
            deployment.status = EdgeDeploymentStatus.FAILED
            self.db.commit()
    
    async def _deploy_to_location(self, deployment: EdgeDeployment, location: Dict[str, Any]):
        """Deploy to a specific edge location"""
        try:
            # Simulate deployment to edge location
            logger.info(f"Deploying to {location['name']}")
            
            # Simulate network latency based on location
            base_delay = 0.1
            if location.get("continent") == "Asia Pacific":
                base_delay = 0.3
            elif location.get("continent") == "South America":
                base_delay = 0.4
            elif location.get("continent") == "Africa":
                base_delay = 0.5
            
            await asyncio.sleep(base_delay + random.uniform(0.1, 0.3))
            
            # In a real implementation, this would:
            # 1. Download code bundle from storage
            # 2. Extract and prepare runtime environment
            # 3. Deploy to edge infrastructure
            # 4. Configure routing and health checks
            
        except Exception as e:
            logger.error(f"Failed to deploy to {location['name']}: {e}")
            raise
    
    async def update_edge_deployment(
        self,
        deployment_id: str,
        code_bundle: Optional[bytes] = None,
        configuration: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update edge deployment
        """
        deployment = self.db.query(EdgeDeployment).filter(EdgeDeployment.id == deployment_id).first()
        if not deployment:
            raise ValueError("Edge deployment not found")
        
        try:
            deployment.status = EdgeDeploymentStatus.UPDATING
            self.db.commit()
            
            # Update code bundle if provided
            if code_bundle:
                code_checksum = hashlib.sha256(code_bundle).hexdigest()
                code_bundle_url = await self._store_code_bundle(code_bundle, code_checksum)
                
                deployment.code_bundle_url = code_bundle_url
                deployment.code_checksum = code_checksum
                
                # Increment version
                version_parts = deployment.version.split('.')
                version_parts[-1] = str(int(version_parts[-1]) + 1)
                deployment.version = '.'.join(version_parts)
            
            # Update configuration
            if configuration:
                for key, value in configuration.items():
                    if hasattr(deployment, key):
                        setattr(deployment, key, value)
            
            # Redeploy to edge locations
            await self._deploy_to_edge_locations(deployment_id)
            
            return True
            
        except Exception as e:
            logger.error(f"Edge deployment update failed: {e}")
            deployment.status = EdgeDeploymentStatus.FAILED
            self.db.commit()
            return False
    
    async def delete_edge_deployment(self, deployment_id: str, user_id: str) -> bool:
        """
        Delete edge deployment
        """
        deployment = self.db.query(EdgeDeployment).filter(
            EdgeDeployment.id == deployment_id,
            EdgeDeployment.user_id == user_id
        ).first()
        
        if not deployment:
            raise ValueError("Edge deployment not found")
        
        try:
            # Stop deployment on all edge locations
            await self._cleanup_edge_deployment(deployment)
            
            # Delete from database
            self.db.delete(deployment)
            self.db.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete edge deployment: {e}")
            return False
    
    async def _cleanup_edge_deployment(self, deployment: EdgeDeployment):
        """Cleanup deployment from all edge locations"""
        try:
            # Simulate cleanup
            for location in deployment.edge_locations:
                logger.info(f"Cleaning up from {location['name']}")
                await asyncio.sleep(0.1)
            
            # In a real implementation, this would:
            # 1. Remove code from edge locations
            # 2. Update routing rules
            # 3. Clean up storage
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
    
    async def scale_edge_deployment(
        self,
        deployment_id: str,
        target_locations: List[str] = None,
        scale_factor: float = 1.0
    ) -> bool:
        """
        Scale edge deployment up or down
        """
        deployment = self.db.query(EdgeDeployment).filter(EdgeDeployment.id == deployment_id).first()
        if not deployment:
            raise ValueError("Edge deployment not found")
        
        try:
            current_location_count = len(deployment.edge_locations)
            target_count = int(current_location_count * scale_factor)
            
            if target_count > current_location_count:
                # Scale up - add more edge locations
                additional_locations = self.location_manager.get_optimal_locations(
                    max_locations=target_count - current_location_count
                )
                
                for location in additional_locations:
                    await self._deploy_to_location(deployment, location.to_dict())
                    deployment.edge_locations.append(location.to_dict())
                
            elif target_count < current_location_count:
                # Scale down - remove edge locations
                locations_to_remove = deployment.edge_locations[target_count:]
                deployment.edge_locations = deployment.edge_locations[:target_count]
                
                # Cleanup removed locations
                for location in locations_to_remove:
                    logger.info(f"Removing deployment from {location['name']}")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Scaling failed: {e}")
            return False
    
    async def get_edge_deployment_status(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get comprehensive edge deployment status
        """
        deployment = self.db.query(EdgeDeployment).filter(EdgeDeployment.id == deployment_id).first()
        if not deployment:
            raise ValueError("Edge deployment not found")
        
        # Calculate deployment health
        total_locations = len(deployment.edge_locations)
        healthy_locations = total_locations  # Simplified - assume all healthy
        
        # Get performance metrics
        performance_metrics = await self._get_performance_metrics(deployment)
        
        return {
            "deployment": {
                "id": deployment.id,
                "name": deployment.name,
                "version": deployment.version,
                "status": deployment.status.value,
                "deployment_url": deployment.deployment_url,
                "created_at": deployment.created_at.isoformat(),
                "last_deployed_at": deployment.last_deployed_at.isoformat() if deployment.last_deployed_at else None
            },
            "runtime": {
                "runtime": deployment.runtime,
                "version": deployment.runtime_version,
                "memory_limit": deployment.memory_limit,
                "timeout": deployment.timeout
            },
            "distribution": {
                "total_locations": total_locations,
                "healthy_locations": healthy_locations,
                "deployment_strategy": deployment.deployment_strategy,
                "edge_locations": deployment.edge_locations
            },
            "performance": performance_metrics,
            "configuration": {
                "environment_variables": deployment.environment_variables,
                "custom_domains": deployment.custom_domains,
                "waf_rules": deployment.waf_rules,
                "rate_limits": deployment.rate_limits
            }
        }
    
    async def _get_performance_metrics(self, deployment: EdgeDeployment) -> Dict[str, Any]:
        """Get performance metrics for deployment"""
        # In production, this would query monitoring systems
        return {
            "requests_per_minute": deployment.requests_per_minute,
            "average_response_time": deployment.average_response_time,
            "error_rate": deployment.error_rate,
            "cache_hit_ratio": deployment.cache_hit_ratio,
            "cpu_usage": deployment.cpu_usage,
            "memory_usage": deployment.memory_usage,
            "uptime_percentage": 99.9  # Placeholder
        }
    
    async def list_edge_deployments(self, project_id: str, user_id: str) -> List[Dict[str, Any]]:
        """
        List all edge deployments for a project
        """
        deployments = self.db.query(EdgeDeployment).filter(
            EdgeDeployment.project_id == project_id,
            EdgeDeployment.user_id == user_id
        ).all()
        
        deployment_list = []
        for deployment in deployments:
            status = await self.get_edge_deployment_status(deployment.id)
            deployment_list.append(status)
        
        return deployment_list
    
    async def get_global_edge_map(self) -> Dict[str, Any]:
        """
        Get global edge location map data
        """
        all_locations = self.location_manager.get_all_locations()
        
        # Group by continent
        continents = {}
        for location in all_locations:
            if location.continent not in continents:
                continents[location.continent] = []
            continents[location.continent].append(location.to_dict())
        
        # Get deployment statistics
        total_deployments = self.db.query(EdgeDeployment).count()
        active_deployments = self.db.query(EdgeDeployment).filter(
            EdgeDeployment.status == EdgeDeploymentStatus.ACTIVE
        ).count()
        
        return {
            "statistics": {
                "total_locations": len(all_locations),
                "total_deployments": total_deployments,
                "active_deployments": active_deployments,
                "continents": len(continents)
            },
            "continents": continents,
            "locations": [loc.to_dict() for loc in all_locations]
        }
    
    async def get_deployment_logs(
        self,
        deployment_id: str,
        location_code: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """
        Get deployment logs
        """
        deployment = self.db.query(EdgeDeployment).filter(EdgeDeployment.id == deployment_id).first()
        if not deployment:
            raise ValueError("Edge deployment not found")
        
        # In production, this would query log aggregation systems
        # For demo, return sample logs
        sample_logs = [
            {
                "timestamp": datetime.utcnow().isoformat(),
                "level": "INFO",
                "location": location_code or "us-east-1",
                "message": "Request processed successfully",
                "response_time": 45,
                "status_code": 200
            },
            {
                "timestamp": (datetime.utcnow() - timedelta(minutes=1)).isoformat(),
                "level": "INFO",
                "location": location_code or "eu-west-1",
                "message": "Cache hit for static asset",
                "response_time": 12,
                "status_code": 200
            }
        ]
        
        return sample_logs
    
    async def configure_traffic_routing(
        self,
        deployment_id: str,
        routing_rules: List[Dict[str, Any]]
    ) -> bool:
        """
        Configure traffic routing rules
        """
        deployment = self.db.query(EdgeDeployment).filter(EdgeDeployment.id == deployment_id).first()
        if not deployment:
            raise ValueError("Edge deployment not found")
        
        try:
            # Update traffic allocation
            deployment.traffic_allocation = {
                "rules": routing_rules,
                "updated_at": datetime.utcnow().isoformat()
            }
            
            self.db.commit()
            
            # Apply routing rules to edge locations
            # In production, this would update edge router configurations
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to configure traffic routing: {e}")
            return False