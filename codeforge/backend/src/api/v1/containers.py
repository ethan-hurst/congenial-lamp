"""
Container API endpoints for CodeForge
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import json

from ...services.container_orchestrator import ContainerOrchestrator
from ...services.container_service import ContainerService
from ...services.usage_calculator import UsageCalculator
from ...auth.dependencies import get_current_user
from ...models.user import User


router = APIRouter(prefix="/containers", tags=["containers"])

# Shared instances
orchestrator = ContainerOrchestrator()
container_service = ContainerService()
usage_calculator = UsageCalculator()


class ContainerCreateRequest(BaseModel):
    project_id: str
    language: str
    version: str
    cpu_cores: int = 2
    memory_gb: int = 2
    gpu_type: Optional[str] = None
    

class ContainerScaleRequest(BaseModel):
    cpu_cores: int
    memory_gb: int
    gpu_type: Optional[str] = None
    

class ContainerResponse(BaseModel):
    container_id: str
    status: str
    websocket_url: str
    created_at: str
    

class ContainerStatsResponse(BaseModel):
    cpu_percent: float
    memory_mb: float
    credits_used: int
    credits_per_hour: float
    is_idle: bool
    

@router.post("/create", response_model=ContainerResponse)
async def create_container(
    request: ContainerCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """Create a new container for the project"""
    try:
        # Get container from orchestrator (uses pool if available)
        container_id = await orchestrator.get_container(
            user_id=current_user.id,
            project_id=request.project_id,
            language=request.language,
            version=request.version
        )
        
        # Scale to requested resources
        if request.cpu_cores > 2 or request.memory_gb > 2 or request.gpu_type:
            await orchestrator.scale_container(
                container_id=container_id,
                cpu_cores=request.cpu_cores,
                memory_gb=request.memory_gb,
                gpu_type=request.gpu_type
            )
            
        return ContainerResponse(
            container_id=container_id,
            status="running",
            websocket_url=f"ws://localhost:8765/ide/{container_id}",
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@router.post("/{container_id}/scale")
async def scale_container(
    container_id: str,
    request: ContainerScaleRequest,
    current_user: User = Depends(get_current_user)
):
    """Live scale container resources"""
    try:
        await orchestrator.scale_container(
            container_id=container_id,
            cpu_cores=request.cpu_cores,
            memory_gb=request.memory_gb,
            gpu_type=request.gpu_type
        )
        
        return {"status": "scaled", "container_id": container_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@router.post("/{container_id}/clone")
async def clone_container(
    container_id: str,
    new_project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Clone container with full state"""
    try:
        new_container_id = await orchestrator.clone_container(
            source_container_id=container_id,
            user_id=current_user.id,
            new_project_id=new_project_id
        )
        
        return ContainerResponse(
            container_id=new_container_id,
            status="running",
            websocket_url=f"ws://localhost:8765/ide/{new_container_id}",
            created_at=datetime.utcnow().isoformat()
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@router.get("/{container_id}/stats", response_model=ContainerStatsResponse)
async def get_container_stats(
    container_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get real-time container usage statistics"""
    try:
        # Find session ID for container
        session_id = None
        for sid, info in usage_calculator.active_sessions.items():
            if info.get("container_id") == container_id:
                session_id = sid
                break
                
        if not session_id:
            raise HTTPException(status_code=404, detail="Container not found")
            
        stats = await usage_calculator.get_current_usage(session_id)
        
        return ContainerStatsResponse(
            cpu_percent=stats["current_cpu_percent"],
            memory_mb=stats["current_memory_mb"],
            credits_used=int(stats["credits_used_so_far"]),
            credits_per_hour=stats["credits_per_hour_rate"],
            is_idle=stats["is_idle"]
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@router.delete("/{container_id}")
async def stop_container(
    container_id: str,
    current_user: User = Depends(get_current_user)
):
    """Stop and remove container"""
    try:
        await orchestrator.stop_container(container_id)
        return {"status": "stopped", "container_id": container_id}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

@router.websocket("/{container_id}/exec")
async def container_exec_websocket(
    websocket: WebSocket,
    container_id: str
):
    """WebSocket endpoint for container command execution"""
    await websocket.accept()
    
    try:
        # Get container
        container = await container_service.docker.containers.get(container_id)
        
        while True:
            # Receive command from client
            data = await websocket.receive_json()
            command = data.get("command", "").split()
            
            if not command:
                await websocket.send_json({
                    "type": "error",
                    "message": "No command provided"
                })
                continue
                
            # Execute command in container
            exec_instance = await container.exec(
                command,
                stdout=True,
                stderr=True,
                tty=True
            )
            
            # Stream output
            async with exec_instance.start() as stream:
                async for chunk in stream:
                    await websocket.send_json({
                        "type": "output",
                        "data": chunk.decode('utf-8', errors='replace')
                    })
                    
            # Get exit code
            exec_info = await exec_instance.inspect()
            await websocket.send_json({
                "type": "exit",
                "code": exec_info["ExitCode"]
            })
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        await websocket.close()
        

@router.get("/pools/stats")
async def get_pool_stats(
    current_user: User = Depends(get_current_user)
):
    """Get container pool statistics"""
    try:
        stats = await orchestrator.get_container_stats()
        return stats
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        

# Initialize orchestrator on module load
import asyncio
from datetime import datetime

async def init_orchestrator():
    await orchestrator.start()
    
# Run initialization in background
asyncio.create_task(init_orchestrator())