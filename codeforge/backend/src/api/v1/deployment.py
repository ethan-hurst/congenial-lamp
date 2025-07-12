"""
Deployment API endpoints for CodeForge
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json

from ...services.deployment_service import (
    DeploymentService, DeploymentConfig, DeploymentProvider, 
    ProjectType, DeploymentStatus
)
from ...auth.dependencies import get_current_user
from ...models.user import User


router = APIRouter(prefix="/deploy", tags=["deployment"])

# Shared deployment service instance
deployment_service = DeploymentService()


class CreateDeploymentRequest(BaseModel):
    project_id: str
    provider: str
    project_type: Optional[str] = None
    build_command: Optional[str] = None
    start_command: Optional[str] = None
    output_directory: Optional[str] = None
    environment_variables: Dict[str, str] = {}
    install_command: Optional[str] = None
    node_version: Optional[str] = None
    python_version: Optional[str] = None
    docker_file: Optional[str] = None
    domains: List[str] = []
    regions: List[str] = []
    auto_deploy: bool = True


class DeploymentResponse(BaseModel):
    success: bool
    deployment_id: str
    status: str
    message: str
    url: Optional[str] = None
    build_id: Optional[str] = None


@router.post("/create", response_model=DeploymentResponse)
async def create_deployment(
    request: CreateDeploymentRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new deployment"""
    try:
        # Build deployment config
        config = DeploymentConfig(
            provider=DeploymentProvider(request.provider),
            project_type=ProjectType(request.project_type) if request.project_type else ProjectType.STATIC_SITE,
            build_command=request.build_command,
            start_command=request.start_command,
            output_directory=request.output_directory,
            environment_variables=request.environment_variables,
            install_command=request.install_command,
            node_version=request.node_version,
            python_version=request.python_version,
            docker_file=request.docker_file,
            domains=request.domains,
            regions=request.regions,
            auto_deploy=request.auto_deploy
        )
        
        # Get project source path (would be from project storage)
        source_path = f"/projects/{request.project_id}"  # Simplified for demo
        
        deployment_id = await deployment_service.create_deployment(
            project_id=request.project_id,
            user_id=current_user.id,
            config=config,
            source_path=source_path
        )
        
        deployment = deployment_service.get_deployment(deployment_id)
        
        return DeploymentResponse(
            success=True,
            deployment_id=deployment_id,
            status=deployment.status,
            message="Deployment started successfully",
            url=deployment.url,
            build_id=deployment.build_id
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create deployment: {str(e)}"
        )


@router.get("/deployments/{deployment_id}")
async def get_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get deployment details"""
    deployment = deployment_service.get_deployment(deployment_id)
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    # Check ownership
    if deployment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "id": deployment.id,
        "project_id": deployment.project_id,
        "status": deployment.status,
        "provider": deployment.config.provider,
        "project_type": deployment.config.project_type,
        "url": deployment.url,
        "preview_urls": deployment.preview_urls,
        "build_id": deployment.build_id,
        "created_at": deployment.created_at.isoformat(),
        "updated_at": deployment.updated_at.isoformat(),
        "deployed_at": deployment.deployed_at.isoformat() if deployment.deployed_at else None,
        "build_time_seconds": deployment.build_time_seconds,
        "deploy_time_seconds": deployment.deploy_time_seconds,
        "bundle_size_mb": deployment.bundle_size_mb,
        "error_message": deployment.error_message,
        "config": {
            "build_command": deployment.config.build_command,
            "start_command": deployment.config.start_command,
            "output_directory": deployment.config.output_directory,
            "environment_variables": deployment.config.environment_variables,
            "domains": deployment.config.domains,
            "regions": deployment.config.regions,
            "auto_deploy": deployment.config.auto_deploy
        }
    }


@router.get("/deployments/{deployment_id}/logs")
async def get_deployment_logs(
    deployment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get deployment logs"""
    deployment = deployment_service.get_deployment(deployment_id)
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    if deployment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return {
        "deployment_id": deployment_id,
        "logs": [
            {
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "source": log.source
            }
            for log in deployment.logs
        ]
    }


@router.post("/deployments/{deployment_id}/cancel")
async def cancel_deployment(
    deployment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Cancel a running deployment"""
    deployment = deployment_service.get_deployment(deployment_id)
    
    if not deployment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Deployment not found"
        )
    
    if deployment.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    success = await deployment_service.cancel_deployment(deployment_id)
    
    if success:
        return {"success": True, "message": "Deployment cancelled successfully"}
    else:
        return {"success": False, "message": "Deployment cannot be cancelled"}


@router.post("/deployments/{deployment_id}/redeploy")
async def redeploy(
    deployment_id: str,
    current_user: User = Depends(get_current_user)
):
    """Redeploy using same configuration"""
    try:
        original = deployment_service.get_deployment(deployment_id)
        
        if not original:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Original deployment not found"
            )
        
        if original.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied"
            )
        
        source_path = f"/projects/{original.project_id}"
        new_deployment_id = await deployment_service.redeploy(deployment_id, source_path)
        
        return {
            "success": True,
            "new_deployment_id": new_deployment_id,
            "message": "Redeployment started successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to redeploy: {str(e)}"
        )


@router.get("/projects/{project_id}/deployments")
async def get_project_deployments(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get all deployments for a project"""
    deployments = deployment_service.list_deployments(project_id=project_id, user_id=current_user.id)
    
    return {
        "project_id": project_id,
        "deployments": [
            {
                "id": d.id,
                "status": d.status,
                "provider": d.config.provider,
                "url": d.url,
                "created_at": d.created_at.isoformat(),
                "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
                "build_time_seconds": d.build_time_seconds,
                "bundle_size_mb": d.bundle_size_mb
            }
            for d in deployments
        ],
        "total": len(deployments)
    }


@router.get("/user/deployments")
async def get_user_deployments(
    current_user: User = Depends(get_current_user)
):
    """Get all deployments for current user"""
    deployments = deployment_service.list_deployments(user_id=current_user.id)
    
    return {
        "deployments": [
            {
                "id": d.id,
                "project_id": d.project_id,
                "status": d.status,
                "provider": d.config.provider,
                "project_type": d.config.project_type,
                "url": d.url,
                "created_at": d.created_at.isoformat(),
                "deployed_at": d.deployed_at.isoformat() if d.deployed_at else None,
                "build_time_seconds": d.build_time_seconds,
                "bundle_size_mb": d.bundle_size_mb
            }
            for d in deployments
        ],
        "total": len(deployments)
    }


@router.get("/providers")
async def get_deployment_providers(
    project_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Get available deployment providers"""
    project_type_enum = None
    if project_type:
        try:
            project_type_enum = ProjectType(project_type)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid project type: {project_type}"
            )
    
    providers = deployment_service.get_supported_providers(project_type_enum)
    
    return {
        "providers": providers,
        "total": len(providers)
    }


@router.post("/quick-deploy/{project_id}")
async def quick_deploy(
    project_id: str,
    provider: str = "vercel",
    current_user: User = Depends(get_current_user)
):
    """Quick deploy with smart defaults"""
    try:
        # Auto-detect project type and set smart defaults
        config = DeploymentConfig(
            provider=DeploymentProvider(provider),
            project_type=ProjectType.SPA,  # Will be auto-detected
            auto_deploy=True
        )
        
        source_path = f"/projects/{project_id}"
        
        deployment_id = await deployment_service.create_deployment(
            project_id=project_id,
            user_id=current_user.id,
            config=config,
            source_path=source_path
        )
        
        return {
            "success": True,
            "deployment_id": deployment_id,
            "message": f"Quick deploy to {provider} started!",
            "estimated_time": "2-3 minutes"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick deploy failed: {str(e)}"
        )


@router.websocket("/deployments/{deployment_id}/logs/stream")
async def stream_deployment_logs(
    websocket: WebSocket,
    deployment_id: str
):
    """Stream deployment logs in real-time"""
    await websocket.accept()
    
    try:
        deployment = deployment_service.get_deployment(deployment_id)
        if not deployment:
            await websocket.close(code=1000, reason="Deployment not found")
            return
        
        # Send existing logs
        for log in deployment.logs:
            await websocket.send_text(json.dumps({
                "timestamp": log.timestamp.isoformat(),
                "level": log.level,
                "message": log.message,
                "source": log.source
            }))
        
        # Stream new logs (simplified - would use pub/sub in production)
        last_log_count = len(deployment.logs)
        
        while deployment.status in [DeploymentStatus.PENDING, DeploymentStatus.BUILDING, DeploymentStatus.DEPLOYING]:
            # Check for new logs
            current_logs = deployment_service.get_deployment(deployment_id).logs
            if len(current_logs) > last_log_count:
                for log in current_logs[last_log_count:]:
                    await websocket.send_text(json.dumps({
                        "timestamp": log.timestamp.isoformat(),
                        "level": log.level,
                        "message": log.message,
                        "source": log.source
                    }))
                last_log_count = len(current_logs)
            
            await asyncio.sleep(1)
        
        # Send final status
        final_deployment = deployment_service.get_deployment(deployment_id)
        await websocket.send_text(json.dumps({
            "type": "status_update",
            "status": final_deployment.status,
            "url": final_deployment.url,
            "completed": True
        }))
        
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_text(json.dumps({
            "type": "error",
            "message": f"Stream error: {str(e)}"
        }))


@router.get("/analytics/{project_id}")
async def get_deployment_analytics(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get deployment analytics for a project"""
    deployments = deployment_service.list_deployments(project_id=project_id, user_id=current_user.id)
    
    if not deployments:
        return {
            "project_id": project_id,
            "total_deployments": 0,
            "success_rate": 0,
            "average_build_time": 0,
            "average_bundle_size": 0
        }
    
    successful_deployments = [d for d in deployments if d.status == DeploymentStatus.DEPLOYED]
    failed_deployments = [d for d in deployments if d.status == DeploymentStatus.FAILED]
    
    # Calculate metrics
    success_rate = len(successful_deployments) / len(deployments) * 100
    
    build_times = [d.build_time_seconds for d in deployments if d.build_time_seconds]
    avg_build_time = sum(build_times) / len(build_times) if build_times else 0
    
    bundle_sizes = [d.bundle_size_mb for d in deployments if d.bundle_size_mb]
    avg_bundle_size = sum(bundle_sizes) / len(bundle_sizes) if bundle_sizes else 0
    
    # Provider usage
    provider_usage = {}
    for deployment in deployments:
        provider = deployment.config.provider
        provider_usage[provider] = provider_usage.get(provider, 0) + 1
    
    return {
        "project_id": project_id,
        "total_deployments": len(deployments),
        "successful_deployments": len(successful_deployments),
        "failed_deployments": len(failed_deployments),
        "success_rate": round(success_rate, 2),
        "average_build_time_seconds": round(avg_build_time, 2),
        "average_bundle_size_mb": round(avg_bundle_size, 2),
        "provider_usage": provider_usage,
        "recent_deployments": [
            {
                "id": d.id,
                "status": d.status,
                "provider": d.config.provider,
                "created_at": d.created_at.isoformat(),
                "build_time": d.build_time_seconds
            }
            for d in deployments[:10]  # Last 10 deployments
        ]
    }


@router.get("/health")
async def deployment_health():
    """Get deployment service health"""
    all_deployments = deployment_service.list_deployments()
    active_deployments = [
        d for d in all_deployments 
        if d.status in [DeploymentStatus.PENDING, DeploymentStatus.BUILDING, DeploymentStatus.DEPLOYING]
    ]
    
    return {
        "status": "healthy",
        "total_deployments": len(all_deployments),
        "active_deployments": len(active_deployments),
        "supported_providers": len(deployment_service.get_supported_providers()),
        "service_uptime": "running"
    }