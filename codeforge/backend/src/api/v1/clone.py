"""
Clone API endpoints for CodeForge
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel

from ...services.clone_service import InstantCloneService, CloneResult, CloneMetadata
from ...auth.dependencies import get_current_user
from ...models.user import User


router = APIRouter(prefix="/clone", tags=["clone"])

# Shared clone service instance
clone_service = InstantCloneService()


class CloneProjectRequest(BaseModel):
    project_id: str
    clone_name: Optional[str] = None
    include_dependencies: bool = True
    include_containers: bool = True
    include_secrets: bool = False
    preserve_state: bool = True


class CloneResponse(BaseModel):
    success: bool
    clone_id: str
    new_project_id: str
    message: str
    cloned_files: int
    total_time_seconds: float
    performance_metrics: Dict[str, Any]


class CloneStatusResponse(BaseModel):
    clone_id: str
    status: str
    progress: float
    files_copied: int
    total_files: int
    bytes_copied: int
    total_bytes: int
    start_time: str
    end_time: Optional[str]
    error_message: Optional[str]


@router.post("/start", response_model=CloneResponse)
async def start_clone(
    request: CloneProjectRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Start instant project clone"""
    try:
        # Start clone operation
        result = await clone_service.clone_project(
            source_project_id=request.project_id,
            user_id=current_user.id,
            clone_name=request.clone_name,
            include_dependencies=request.include_dependencies,
            include_containers=request.include_containers,
            include_secrets=request.include_secrets,
            preserve_state=request.preserve_state
        )
        
        if result.success:
            return CloneResponse(
                success=True,
                clone_id=result.clone_id,
                new_project_id=result.new_project_id,
                message=f"Project cloned successfully in {result.total_time_seconds:.2f} seconds",
                cloned_files=result.cloned_files,
                total_time_seconds=result.total_time_seconds,
                performance_metrics=result.performance_metrics
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Clone failed: {result.error_message}"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clone operation failed: {str(e)}"
        )


@router.get("/status/{clone_id}", response_model=CloneStatusResponse)
async def get_clone_status(
    clone_id: str,
    current_user: User = Depends(get_current_user)
):
    """Get clone operation status"""
    metadata = clone_service.get_clone_status(clone_id)
    
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Clone operation not found"
        )
        
    # Verify ownership
    if metadata.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
        
    return CloneStatusResponse(
        clone_id=metadata.clone_id,
        status=metadata.status,
        progress=metadata.progress,
        files_copied=metadata.files_copied,
        total_files=metadata.total_files,
        bytes_copied=metadata.bytes_copied,
        total_bytes=metadata.total_bytes,
        start_time=metadata.start_time.isoformat(),
        end_time=metadata.end_time.isoformat() if metadata.end_time else None,
        error_message=metadata.error_message
    )


@router.get("/history", response_model=List[CloneStatusResponse])
async def get_clone_history(
    current_user: User = Depends(get_current_user)
):
    """Get user's clone history"""
    user_clones = clone_service.list_user_clones(current_user.id)
    
    return [
        CloneStatusResponse(
            clone_id=metadata.clone_id,
            status=metadata.status,
            progress=metadata.progress,
            files_copied=metadata.files_copied,
            total_files=metadata.total_files,
            bytes_copied=metadata.bytes_copied,
            total_bytes=metadata.total_bytes,
            start_time=metadata.start_time.isoformat(),
            end_time=metadata.end_time.isoformat() if metadata.end_time else None,
            error_message=metadata.error_message
        )
        for metadata in user_clones
    ]


@router.post("/quick/{project_id}")
async def quick_clone(
    project_id: str,
    current_user: User = Depends(get_current_user)
):
    """Ultra-fast clone with default settings for maximum speed"""
    try:
        result = await clone_service.clone_project(
            source_project_id=project_id,
            user_id=current_user.id,
            clone_name=None,  # Auto-generate name
            include_dependencies=False,  # Skip for speed
            include_containers=False,     # Skip for speed
            include_secrets=False,       # Skip for security
            preserve_state=False         # Skip for speed
        )
        
        if result.success:
            return {
                "success": True,
                "message": f"Ultra-fast clone completed in {result.total_time_seconds:.3f} seconds",
                "new_project_id": result.new_project_id,
                "performance": {
                    "time_seconds": result.total_time_seconds,
                    "files_cloned": result.cloned_files,
                    "speed_rating": "⚡ Ultra Fast" if result.total_time_seconds < 1.0 else "🚀 Fast"
                }
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error_message
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Quick clone failed: {str(e)}"
        )


@router.get("/templates")
async def get_clone_templates(
    current_user: User = Depends(get_current_user)
):
    """Get available clone templates for instant setup"""
    return {
        "templates": [
            {
                "id": "react-typescript",
                "name": "React + TypeScript",
                "description": "Modern React app with TypeScript, Vite, and Tailwind CSS",
                "tags": ["frontend", "react", "typescript"],
                "clone_time_estimate": "0.8s",
                "file_count": 45,
                "size_mb": 2.1
            },
            {
                "id": "python-fastapi",
                "name": "Python FastAPI",
                "description": "FastAPI backend with SQLAlchemy, Pydantic, and pytest",
                "tags": ["backend", "python", "api"],
                "clone_time_estimate": "0.6s",
                "file_count": 32,
                "size_mb": 1.8
            },
            {
                "id": "node-express",
                "name": "Node.js Express",
                "description": "Express.js API with TypeScript, Prisma, and Jest",
                "tags": ["backend", "nodejs", "api"],
                "clone_time_estimate": "0.7s",
                "file_count": 38,
                "size_mb": 2.3
            },
            {
                "id": "fullstack-nextjs",
                "name": "Full-Stack Next.js",
                "description": "Complete Next.js app with database, auth, and deployment",
                "tags": ["fullstack", "nextjs", "react"],
                "clone_time_estimate": "1.2s",
                "file_count": 67,
                "size_mb": 4.5
            },
            {
                "id": "rust-actix",
                "name": "Rust Actix Web",
                "description": "High-performance Rust web service with Actix Web",
                "tags": ["backend", "rust", "performance"],
                "clone_time_estimate": "0.9s",
                "file_count": 28,
                "size_mb": 3.2
            }
        ]
    }


@router.post("/template/{template_id}")
async def clone_template(
    template_id: str,
    project_name: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """Clone from a pre-built template (fastest option)"""
    try:
        # Templates are pre-optimized projects stored in the system
        template_project_id = f"template_{template_id}"
        
        result = await clone_service.clone_project(
            source_project_id=template_project_id,
            user_id=current_user.id,
            clone_name=project_name or f"New {template_id.replace('-', ' ').title()} Project",
            include_dependencies=True,   # Templates have optimized deps
            include_containers=True,     # Templates have pre-built containers
            include_secrets=False,       # Never include template secrets
            preserve_state=False         # Templates start fresh
        )
        
        if result.success:
            return {
                "success": True,
                "message": f"Template cloned in {result.total_time_seconds:.3f} seconds",
                "new_project_id": result.new_project_id,
                "template_id": template_id,
                "ready_to_code": True,
                "next_steps": [
                    "Configure environment variables in .env",
                    "Update project name in package.json/pyproject.toml",
                    "Commit your initial changes",
                    "Start developing!"
                ]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result.error_message
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Template clone failed: {str(e)}"
        )


@router.get("/performance/stats")
async def get_clone_performance_stats(
    current_user: User = Depends(get_current_user)
):
    """Get clone performance statistics"""
    user_clones = clone_service.list_user_clones(current_user.id)
    completed_clones = [c for c in user_clones if c.end_time is not None]
    
    if not completed_clones:
        return {
            "total_clones": 0,
            "average_time": 0,
            "fastest_clone": 0,
            "total_files_cloned": 0,
            "total_data_cloned_mb": 0
        }
        
    times = [
        (c.end_time - c.start_time).total_seconds() 
        for c in completed_clones
    ]
    
    return {
        "total_clones": len(completed_clones),
        "average_time_seconds": sum(times) / len(times),
        "fastest_clone_seconds": min(times),
        "slowest_clone_seconds": max(times),
        "total_files_cloned": sum(c.files_copied for c in completed_clones),
        "total_data_cloned_mb": sum(c.bytes_copied for c in completed_clones) / (1024 * 1024),
        "sub_second_clones": len([t for t in times if t < 1.0]),
        "performance_rating": "🚀 Lightning Fast" if min(times) < 0.5 else "⚡ Very Fast" if min(times) < 1.0 else "🏃 Fast"
    }