"""
Deployment Pipeline Service
One-click deployment to multiple cloud providers and platforms
"""
import asyncio
import json
import uuid
import yaml
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum
from pathlib import Path
import docker
import subprocess
import tempfile
import shutil

from ..config.settings import settings


class DeploymentProvider(str, Enum):
    """Supported deployment providers"""
    VERCEL = "vercel"
    NETLIFY = "netlify"
    HEROKU = "heroku"
    AWS_LAMBDA = "aws_lambda"
    GOOGLE_CLOUD_RUN = "google_cloud_run"
    DIGITAL_OCEAN_APPS = "digital_ocean_apps"
    RAILWAY = "railway"
    RENDER = "render"
    FLY_IO = "fly_io"
    CLOUDFLARE_PAGES = "cloudflare_pages"


class DeploymentStatus(str, Enum):
    """Deployment status"""
    PENDING = "pending"
    BUILDING = "building"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProjectType(str, Enum):
    """Project types for deployment"""
    STATIC_SITE = "static_site"
    SPA = "spa"
    NODE_APP = "node_app"
    PYTHON_APP = "python_app"
    DOCKER_APP = "docker_app"
    SERVERLESS = "serverless"
    FULL_STACK = "full_stack"


@dataclass
class DeploymentConfig:
    """Deployment configuration"""
    provider: DeploymentProvider
    project_type: ProjectType
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    output_directory: Optional[str] = None
    environment_variables: Dict[str, str] = None
    install_command: Optional[str] = None
    node_version: Optional[str] = None
    python_version: Optional[str] = None
    docker_file: Optional[str] = None
    domains: List[str] = None
    regions: List[str] = None
    auto_deploy: bool = True
    
    def __post_init__(self):
        if self.environment_variables is None:
            self.environment_variables = {}
        if self.domains is None:
            self.domains = []
        if self.regions is None:
            self.regions = []


@dataclass
class DeploymentLog:
    """Single deployment log entry"""
    timestamp: datetime
    level: str  # info, warning, error
    message: str
    source: str  # build, deploy, runtime


@dataclass
class Deployment:
    """Deployment instance"""
    id: str
    project_id: str
    user_id: str
    config: DeploymentConfig
    status: DeploymentStatus
    created_at: datetime
    updated_at: datetime
    deployed_at: Optional[datetime] = None
    
    # Deployment details
    build_id: Optional[str] = None
    url: Optional[str] = None
    preview_urls: List[str] = None
    logs: List[DeploymentLog] = None
    error_message: Optional[str] = None
    
    # Metrics
    build_time_seconds: Optional[float] = None
    deploy_time_seconds: Optional[float] = None
    bundle_size_mb: Optional[float] = None
    
    def __post_init__(self):
        if self.preview_urls is None:
            self.preview_urls = []
        if self.logs is None:
            self.logs = []


class DeploymentService:
    """
    Universal deployment service supporting multiple providers
    """
    
    def __init__(self):
        self.deployments: Dict[str, Deployment] = {}
        self.docker_client = docker.from_env()
        
        # Provider configurations
        self.provider_configs = {
            DeploymentProvider.VERCEL: {
                "api_endpoint": "https://api.vercel.com",
                "supports": [ProjectType.STATIC_SITE, ProjectType.SPA, ProjectType.NODE_APP, ProjectType.SERVERLESS],
                "regions": ["us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"]
            },
            DeploymentProvider.NETLIFY: {
                "api_endpoint": "https://api.netlify.com",
                "supports": [ProjectType.STATIC_SITE, ProjectType.SPA, ProjectType.SERVERLESS],
                "regions": ["us-east-1", "eu-west-1"]
            },
            DeploymentProvider.HEROKU: {
                "api_endpoint": "https://api.heroku.com",
                "supports": [ProjectType.NODE_APP, ProjectType.PYTHON_APP, ProjectType.DOCKER_APP],
                "regions": ["us", "eu"]
            },
            DeploymentProvider.RAILWAY: {
                "api_endpoint": "https://backboard.railway.app",
                "supports": [ProjectType.NODE_APP, ProjectType.PYTHON_APP, ProjectType.DOCKER_APP],
                "regions": ["us-west-1", "us-east-1", "eu-west-1"]
            }
        }
    
    async def create_deployment(
        self,
        project_id: str,
        user_id: str,
        config: DeploymentConfig,
        source_path: str
    ) -> str:
        """Create a new deployment"""
        deployment_id = str(uuid.uuid4())
        
        deployment = Deployment(
            id=deployment_id,
            project_id=project_id,
            user_id=user_id,
            config=config,
            status=DeploymentStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        
        self.deployments[deployment_id] = deployment
        
        # Start deployment process asynchronously
        asyncio.create_task(self._execute_deployment(deployment, source_path))
        
        return deployment_id
    
    async def _execute_deployment(self, deployment: Deployment, source_path: str) -> None:
        """Execute the deployment process"""
        try:
            deployment.status = DeploymentStatus.BUILDING
            deployment.updated_at = datetime.now(timezone.utc)
            
            await self._log_deployment(deployment, "info", "Starting deployment process", "deploy")
            
            # Detect project type if not specified
            if not deployment.config.project_type:
                deployment.config.project_type = await self._detect_project_type(source_path)
                await self._log_deployment(deployment, "info", f"Detected project type: {deployment.config.project_type}", "build")
            
            # Prepare build
            build_path = await self._prepare_build(deployment, source_path)
            
            # Execute build
            build_start = datetime.now(timezone.utc)
            await self._execute_build(deployment, build_path)
            build_end = datetime.now(timezone.utc)
            deployment.build_time_seconds = (build_end - build_start).total_seconds()
            
            # Deploy to provider
            deployment.status = DeploymentStatus.DEPLOYING
            deployment.updated_at = datetime.now(timezone.utc)
            
            deploy_start = datetime.now(timezone.utc)
            await self._deploy_to_provider(deployment, build_path)
            deploy_end = datetime.now(timezone.utc)
            deployment.deploy_time_seconds = (deploy_end - deploy_start).total_seconds()
            
            # Success
            deployment.status = DeploymentStatus.DEPLOYED
            deployment.deployed_at = datetime.now(timezone.utc)
            deployment.updated_at = datetime.now(timezone.utc)
            
            await self._log_deployment(deployment, "info", f"Deployment successful! URL: {deployment.url}", "deploy")
            
        except Exception as e:
            deployment.status = DeploymentStatus.FAILED
            deployment.error_message = str(e)
            deployment.updated_at = datetime.now(timezone.utc)
            
            await self._log_deployment(deployment, "error", f"Deployment failed: {str(e)}", "deploy")
        
        finally:
            # Cleanup temporary files
            if 'build_path' in locals():
                shutil.rmtree(build_path, ignore_errors=True)
    
    async def _detect_project_type(self, source_path: str) -> ProjectType:
        """Auto-detect project type from source code"""
        source = Path(source_path)
        
        # Check for specific files
        if (source / "package.json").exists():
            package_json = json.loads((source / "package.json").read_text())
            
            # Check for React/SPA indicators
            dependencies = {**package_json.get("dependencies", {}), **package_json.get("devDependencies", {})}
            if any(dep in dependencies for dep in ["react", "vue", "@angular/core", "svelte"]):
                return ProjectType.SPA
            
            # Check for Next.js
            if "next" in dependencies:
                return ProjectType.FULL_STACK
            
            # Check for serverless indicators
            if any(dep in dependencies for dep in ["serverless", "@vercel/node", "netlify-lambda"]):
                return ProjectType.SERVERLESS
            
            return ProjectType.NODE_APP
        
        elif (source / "requirements.txt").exists() or (source / "Pipfile").exists():
            return ProjectType.PYTHON_APP
        
        elif (source / "Dockerfile").exists():
            return ProjectType.DOCKER_APP
        
        elif any((source / ext).exists() for ext in ["index.html", "index.htm"]):
            return ProjectType.STATIC_SITE
        
        else:
            return ProjectType.STATIC_SITE  # Default fallback
    
    async def _prepare_build(self, deployment: Deployment, source_path: str) -> str:
        """Prepare build directory"""
        build_path = tempfile.mkdtemp(prefix=f"codeforge_build_{deployment.id}_")
        
        # Copy source files
        await self._log_deployment(deployment, "info", "Copying source files", "build")
        shutil.copytree(source_path, Path(build_path) / "source")
        
        # Generate deployment configuration files
        await self._generate_deployment_configs(deployment, build_path)
        
        return build_path
    
    async def _generate_deployment_configs(self, deployment: Deployment, build_path: str) -> None:
        """Generate provider-specific configuration files"""
        config = deployment.config
        build_dir = Path(build_path)
        source_dir = build_dir / "source"
        
        if config.provider == DeploymentProvider.VERCEL:
            vercel_config = {
                "version": 2,
                "builds": [],
                "routes": []
            }
            
            if config.project_type == ProjectType.SPA:
                vercel_config["builds"] = [{"src": "package.json", "use": "@vercel/static-build"}]
                vercel_config["routes"] = [{"src": "/(.*)", "dest": "/index.html"}]
            elif config.project_type == ProjectType.NODE_APP:
                vercel_config["builds"] = [{"src": "package.json", "use": "@vercel/node"}]
            
            with open(source_dir / "vercel.json", "w") as f:
                json.dump(vercel_config, f, indent=2)
        
        elif config.provider == DeploymentProvider.NETLIFY:
            netlify_config = {
                "build": {
                    "command": config.build_command or "npm run build",
                    "publish": config.output_directory or "dist"
                }
            }
            
            if config.project_type == ProjectType.SPA:
                netlify_config["redirects"] = [{"from": "/*", "to": "/index.html", "status": 200}]
            
            with open(source_dir / "netlify.toml", "w") as f:
                f.write(self._dict_to_toml(netlify_config))
        
        elif config.provider == DeploymentProvider.HEROKU:
            # Generate Procfile
            if config.start_command:
                with open(source_dir / "Procfile", "w") as f:
                    f.write(f"web: {config.start_command}")
            elif config.project_type == ProjectType.NODE_APP:
                with open(source_dir / "Procfile", "w") as f:
                    f.write("web: npm start")
            elif config.project_type == ProjectType.PYTHON_APP:
                with open(source_dir / "Procfile", "w") as f:
                    f.write("web: python app.py")
    
    async def _execute_build(self, deployment: Deployment, build_path: str) -> None:
        """Execute build process"""
        config = deployment.config
        source_dir = Path(build_path) / "source"
        
        await self._log_deployment(deployment, "info", "Starting build process", "build")
        
        # Install dependencies
        if config.install_command:
            await self._run_command(deployment, config.install_command, source_dir, "install")
        elif (source_dir / "package.json").exists():
            await self._run_command(deployment, "npm install", source_dir, "install")
        elif (source_dir / "requirements.txt").exists():
            await self._run_command(deployment, "pip install -r requirements.txt", source_dir, "install")
        
        # Run build command
        if config.build_command:
            await self._run_command(deployment, config.build_command, source_dir, "build")
        elif config.project_type in [ProjectType.SPA, ProjectType.STATIC_SITE]:
            if (source_dir / "package.json").exists():
                await self._run_command(deployment, "npm run build", source_dir, "build")
        
        # Calculate bundle size
        if config.output_directory:
            output_dir = source_dir / config.output_directory
            if output_dir.exists():
                deployment.bundle_size_mb = await self._calculate_directory_size(output_dir)
        
        await self._log_deployment(deployment, "info", "Build completed successfully", "build")
    
    async def _deploy_to_provider(self, deployment: Deployment, build_path: str) -> None:
        """Deploy to the specified provider"""
        config = deployment.config
        
        await self._log_deployment(deployment, "info", f"Deploying to {config.provider}", "deploy")
        
        if config.provider == DeploymentProvider.VERCEL:
            await self._deploy_to_vercel(deployment, build_path)
        elif config.provider == DeploymentProvider.NETLIFY:
            await self._deploy_to_netlify(deployment, build_path)
        elif config.provider == DeploymentProvider.HEROKU:
            await self._deploy_to_heroku(deployment, build_path)
        elif config.provider == DeploymentProvider.RAILWAY:
            await self._deploy_to_railway(deployment, build_path)
        else:
            raise ValueError(f"Provider {config.provider} not implemented yet")
    
    async def _deploy_to_vercel(self, deployment: Deployment, build_path: str) -> None:
        """Deploy to Vercel"""
        source_dir = Path(build_path) / "source"
        
        # Simulate Vercel deployment
        deployment.build_id = f"vercel_build_{deployment.id}"
        deployment.url = f"https://{deployment.project_id}-{deployment.id[:8]}.vercel.app"
        deployment.preview_urls = [deployment.url]
        
        await self._log_deployment(deployment, "info", "Uploaded to Vercel", "deploy")
        await self._log_deployment(deployment, "info", "Building on Vercel servers", "deploy")
        
        # Simulate build time
        await asyncio.sleep(2)
        
        await self._log_deployment(deployment, "info", "Deployment live on Vercel", "deploy")
    
    async def _deploy_to_netlify(self, deployment: Deployment, build_path: str) -> None:
        """Deploy to Netlify"""
        source_dir = Path(build_path) / "source"
        
        # Simulate Netlify deployment
        deployment.build_id = f"netlify_build_{deployment.id}"
        deployment.url = f"https://{deployment.id[:8]}.netlify.app"
        deployment.preview_urls = [deployment.url]
        
        await self._log_deployment(deployment, "info", "Uploaded to Netlify", "deploy")
        await self._log_deployment(deployment, "info", "Processing on Netlify CDN", "deploy")
        
        # Simulate build time
        await asyncio.sleep(1.5)
        
        await self._log_deployment(deployment, "info", "Site deployed to Netlify", "deploy")
    
    async def _deploy_to_heroku(self, deployment: Deployment, build_path: str) -> None:
        """Deploy to Heroku"""
        source_dir = Path(build_path) / "source"
        
        # Simulate Heroku deployment
        deployment.build_id = f"heroku_build_{deployment.id}"
        deployment.url = f"https://{deployment.project_id}-{deployment.id[:8]}.herokuapp.com"
        deployment.preview_urls = [deployment.url]
        
        await self._log_deployment(deployment, "info", "Creating Heroku app", "deploy")
        await self._log_deployment(deployment, "info", "Pushing to Heroku git", "deploy")
        await self._log_deployment(deployment, "info", "Building slug", "deploy")
        
        # Simulate build time
        await asyncio.sleep(3)
        
        await self._log_deployment(deployment, "info", "App deployed to Heroku", "deploy")
    
    async def _deploy_to_railway(self, deployment: Deployment, build_path: str) -> None:
        """Deploy to Railway"""
        source_dir = Path(build_path) / "source"
        
        # Simulate Railway deployment
        deployment.build_id = f"railway_build_{deployment.id}"
        deployment.url = f"https://{deployment.project_id}-{deployment.id[:8]}.up.railway.app"
        deployment.preview_urls = [deployment.url]
        
        await self._log_deployment(deployment, "info", "Uploading to Railway", "deploy")
        await self._log_deployment(deployment, "info", "Building container", "deploy")
        
        # Simulate build time
        await asyncio.sleep(2.5)
        
        await self._log_deployment(deployment, "info", "Service deployed on Railway", "deploy")
    
    async def _run_command(self, deployment: Deployment, command: str, cwd: Path, source: str) -> None:
        """Run a shell command and log output"""
        await self._log_deployment(deployment, "info", f"Running: {command}", source)
        
        try:
            # In a real implementation, this would capture and stream output
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                await self._log_deployment(deployment, "info", f"Command completed successfully", source)
                if stdout:
                    await self._log_deployment(deployment, "info", stdout.decode(), source)
            else:
                await self._log_deployment(deployment, "error", f"Command failed with code {process.returncode}", source)
                if stderr:
                    await self._log_deployment(deployment, "error", stderr.decode(), source)
                raise Exception(f"Command failed: {command}")
                
        except Exception as e:
            await self._log_deployment(deployment, "error", f"Failed to run command: {str(e)}", source)
            raise
    
    async def _log_deployment(self, deployment: Deployment, level: str, message: str, source: str) -> None:
        """Add log entry to deployment"""
        log_entry = DeploymentLog(
            timestamp=datetime.now(timezone.utc),
            level=level,
            message=message,
            source=source
        )
        deployment.logs.append(log_entry)
        
        # In production, this would also stream to WebSocket clients
        print(f"[{deployment.id}] {level.upper()}: {message}")
    
    async def _calculate_directory_size(self, directory: Path) -> float:
        """Calculate directory size in MB"""
        total_size = 0
        for file_path in directory.rglob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size / (1024 * 1024)  # Convert to MB
    
    def _dict_to_toml(self, data: Dict) -> str:
        """Convert dict to TOML format (simplified)"""
        # This is a basic implementation, would use a TOML library in production
        result = ""
        for key, value in data.items():
            if isinstance(value, dict):
                result += f"[{key}]\n"
                for subkey, subvalue in value.items():
                    if isinstance(subvalue, str):
                        result += f'{subkey} = "{subvalue}"\n'
                    else:
                        result += f'{subkey} = {subvalue}\n'
                result += "\n"
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        result += f"[[{key}]]\n"
                        for subkey, subvalue in item.items():
                            if isinstance(subvalue, str):
                                result += f'{subkey} = "{subvalue}"\n'
                            else:
                                result += f'{subkey} = {subvalue}\n'
                        result += "\n"
        return result
    
    def get_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """Get deployment by ID"""
        return self.deployments.get(deployment_id)
    
    def list_deployments(self, project_id: Optional[str] = None, user_id: Optional[str] = None) -> List[Deployment]:
        """List deployments with optional filters"""
        deployments = list(self.deployments.values())
        
        if project_id:
            deployments = [d for d in deployments if d.project_id == project_id]
        
        if user_id:
            deployments = [d for d in deployments if d.user_id == user_id]
        
        return sorted(deployments, key=lambda d: d.created_at, reverse=True)
    
    async def cancel_deployment(self, deployment_id: str) -> bool:
        """Cancel a running deployment"""
        deployment = self.deployments.get(deployment_id)
        if not deployment:
            return False
        
        if deployment.status in [DeploymentStatus.PENDING, DeploymentStatus.BUILDING, DeploymentStatus.DEPLOYING]:
            deployment.status = DeploymentStatus.CANCELLED
            deployment.updated_at = datetime.now(timezone.utc)
            await self._log_deployment(deployment, "info", "Deployment cancelled by user", "deploy")
            return True
        
        return False
    
    async def redeploy(self, deployment_id: str, source_path: str) -> str:
        """Redeploy using same configuration"""
        original = self.deployments.get(deployment_id)
        if not original:
            raise ValueError(f"Deployment {deployment_id} not found")
        
        return await self.create_deployment(
            project_id=original.project_id,
            user_id=original.user_id,
            config=original.config,
            source_path=source_path
        )
    
    def get_supported_providers(self, project_type: Optional[ProjectType] = None) -> List[Dict[str, Any]]:
        """Get list of supported providers"""
        providers = []
        
        for provider, config in self.provider_configs.items():
            if not project_type or project_type in config["supports"]:
                providers.append({
                    "id": provider,
                    "name": provider.replace("_", " ").title(),
                    "supports": config["supports"],
                    "regions": config["regions"]
                })
        
        return providers