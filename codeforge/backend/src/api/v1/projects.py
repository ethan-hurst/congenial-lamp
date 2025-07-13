"""
Project Management API endpoints for CodeForge
"""
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.orm import Session
import uuid
from datetime import datetime

from ...database.connection import get_database_session
from ...models.user import User
from ...models.project import Project, ProjectCollaborator, ProjectFile, ProjectSnapshot, ProjectType, ProjectVisibility
from ...auth.dependencies import get_current_user
from ...services.file_service import FileService
from ...services.container_service import ContainerService

router = APIRouter(prefix="/projects", tags=["projects"])


class CreateProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    project_type: str = ProjectType.BLANK
    visibility: str = ProjectVisibility.PRIVATE
    template_id: Optional[str] = None
    git_url: Optional[str] = None


class UpdateProjectRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[str] = None
    environment_variables: Optional[Dict[str, str]] = None
    start_command: Optional[str] = None
    install_command: Optional[str] = None
    build_command: Optional[str] = None


class AddCollaboratorRequest(BaseModel):
    email: str
    role: str = "read"  # admin, write, read


class ProjectFileRequest(BaseModel):
    path: str
    content: str
    encoding: str = "utf-8"


class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: Optional[str]
    project_type: str
    visibility: str
    language: Optional[str]
    framework: Optional[str]
    owner_id: str
    created_at: datetime
    updated_at: datetime
    is_active: bool
    stats: Dict[str, int]


@router.post("/", response_model=ProjectResponse)
async def create_project(
    request: CreateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Create a new project"""
    try:
        # Generate unique ID and slug
        project_id = str(uuid.uuid4())
        slug = request.name.lower().replace(' ', '-').replace('_', '-')
        
        # Check if slug is unique for this user
        existing = db.query(Project).filter(
            Project.owner_id == current_user.id,
            Project.slug == slug
        ).first()
        
        if existing:
            # Make slug unique by appending number
            counter = 1
            while existing:
                new_slug = f"{slug}-{counter}"
                existing = db.query(Project).filter(
                    Project.owner_id == current_user.id,
                    Project.slug == new_slug
                ).first()
                if not existing:
                    slug = new_slug
                    break
                counter += 1
        
        # Create project
        project = Project(
            id=project_id,
            name=request.name,
            slug=slug,
            description=request.description,
            project_type=request.project_type,
            visibility=request.visibility,
            owner_id=current_user.id,
            git_url=request.git_url,
            template_id=request.template_id
        )
        
        db.add(project)
        db.commit()
        db.refresh(project)
        
        # Initialize project files if template is specified
        if request.template_id:
            await _initialize_from_template(project_id, request.template_id, db)
        else:
            await _initialize_blank_project(project_id, db)
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            project_type=project.project_type,
            visibility=project.visibility,
            language=project.language,
            framework=project.framework,
            owner_id=project.owner_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            is_active=project.is_active,
            stats={
                "views_count": project.views_count,
                "forks_count": project.forks_count,
                "stars_count": project.stars_count,
                "runs_count": project.runs_count
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create project: {str(e)}"
        )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    visibility: Optional[str] = Query(None, description="Filter by visibility"),
    project_type: Optional[str] = Query(None, description="Filter by project type"),
    limit: int = Query(50, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """List user's projects"""
    try:
        query = db.query(Project).filter(
            Project.owner_id == current_user.id,
            Project.is_active == True
        )
        
        if visibility:
            query = query.filter(Project.visibility == visibility)
        
        if project_type:
            query = query.filter(Project.project_type == project_type)
        
        projects = query.order_by(Project.updated_at.desc()).offset(offset).limit(limit).all()
        
        return [
            ProjectResponse(
                id=project.id,
                name=project.name,
                slug=project.slug,
                description=project.description,
                project_type=project.project_type,
                visibility=project.visibility,
                language=project.language,
                framework=project.framework,
                owner_id=project.owner_id,
                created_at=project.created_at,
                updated_at=project.updated_at,
                is_active=project.is_active,
                stats={
                    "views_count": project.views_count,
                    "forks_count": project.forks_count,
                    "stars_count": project.stars_count,
                    "runs_count": project.runs_count
                }
            )
            for project in projects
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list projects: {str(e)}"
        )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get project details"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check access permissions
    if not _can_access_project(project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Increment view count if not owner
    if project.owner_id != current_user.id:
        project.views_count += 1
        db.commit()
    
    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        project_type=project.project_type,
        visibility=project.visibility,
        language=project.language,
        framework=project.framework,
        owner_id=project.owner_id,
        created_at=project.created_at,
        updated_at=project.updated_at,
        is_active=project.is_active,
        stats={
            "views_count": project.views_count,
            "forks_count": project.forks_count,
            "stars_count": project.stars_count,
            "runs_count": project.runs_count
        }
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    request: UpdateProjectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Update project"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check permissions
    if not _can_modify_project(project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    try:
        # Update fields
        update_data = request.dict(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(project, field):
                setattr(project, field, value)
        
        project.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(project)
        
        return ProjectResponse(
            id=project.id,
            name=project.name,
            slug=project.slug,
            description=project.description,
            project_type=project.project_type,
            visibility=project.visibility,
            language=project.language,
            framework=project.framework,
            owner_id=project.owner_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            is_active=project.is_active,
            stats={
                "views_count": project.views_count,
                "forks_count": project.forks_count,
                "stars_count": project.stars_count,
                "runs_count": project.runs_count
            }
        )
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update project: {str(e)}"
        )


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Delete project (soft delete)"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Only owner can delete
    if project.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owner can delete project"
        )
    
    try:
        # Soft delete
        project.is_active = False
        project.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"success": True, "message": "Project deleted successfully"}
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}"
        )


@router.post("/{project_id}/fork")
async def fork_project(
    project_id: str,
    name: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Fork a project"""
    original_project = db.query(Project).filter(Project.id == project_id).first()
    
    if not original_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if project is forkable (public or accessible)
    if not _can_access_project(original_project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot fork private project"
        )
    
    try:
        # Create fork
        fork_id = str(uuid.uuid4())
        fork_name = name or f"{original_project.name}-fork"
        fork_slug = f"{fork_name.lower().replace(' ', '-')}-{fork_id[:8]}"
        
        fork = Project(
            id=fork_id,
            name=fork_name,
            slug=fork_slug,
            description=f"Fork of {original_project.name}",
            project_type=original_project.project_type,
            visibility=ProjectVisibility.PRIVATE,  # Forks start as private
            language=original_project.language,
            framework=original_project.framework,
            owner_id=current_user.id,
            forked_from=project_id,
            environment_variables=original_project.environment_variables,
            start_command=original_project.start_command,
            install_command=original_project.install_command,
            build_command=original_project.build_command
        )
        
        db.add(fork)
        
        # Update fork count
        original_project.forks_count += 1
        
        db.commit()
        db.refresh(fork)
        
        # Copy project files (async operation)
        await _copy_project_files(original_project.id, fork.id, db)
        
        return {
            "success": True,
            "fork_id": fork.id,
            "message": "Project forked successfully"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fork project: {str(e)}"
        )


@router.get("/{project_id}/files")
async def list_project_files(
    project_id: str,
    path: str = Query("/", description="Directory path to list"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """List project files"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if not _can_access_project(project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        file_service = FileService()
        files = await file_service.list_files(project_id, path)
        return {"files": files, "path": path}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )


@router.get("/{project_id}/files/**")
async def get_project_file(
    project_id: str,
    file_path: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Get project file content"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if not _can_access_project(project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    try:
        file_service = FileService()
        file_content = await file_service.get_file(project_id, file_path)
        return file_content
        
    except FileNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file: {str(e)}"
        )


@router.put("/{project_id}/files/**")
async def update_project_file(
    project_id: str,
    file_path: str,
    request: ProjectFileRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_database_session)
):
    """Update project file"""
    project = db.query(Project).filter(Project.id == project_id).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    if not _can_modify_project(project, current_user, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    try:
        file_service = FileService()
        await file_service.update_file(
            project_id=project_id,
            file_path=file_path,
            content=request.content,
            user_id=current_user.id,
            encoding=request.encoding
        )
        
        # Update project activity
        project.updated_at = datetime.utcnow()
        project.last_activity = datetime.utcnow()
        db.commit()
        
        return {"success": True, "message": "File updated successfully"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update file: {str(e)}"
        )


# Helper functions
def _can_access_project(project: Project, user: User, db: Session) -> bool:
    """Check if user can access project"""
    # Owner always has access
    if project.owner_id == user.id:
        return True
    
    # Public projects are accessible
    if project.visibility == ProjectVisibility.PUBLIC:
        return True
    
    # Check collaboration
    collab = db.query(ProjectCollaborator).filter(
        ProjectCollaborator.project_id == project.id,
        ProjectCollaborator.user_id == user.id,
        ProjectCollaborator.is_active == True
    ).first()
    
    return collab is not None


def _can_modify_project(project: Project, user: User, db: Session) -> bool:
    """Check if user can modify project"""
    # Owner always can modify
    if project.owner_id == user.id:
        return True
    
    # Check collaboration with write access
    collab = db.query(ProjectCollaborator).filter(
        ProjectCollaborator.project_id == project.id,
        ProjectCollaborator.user_id == user.id,
        ProjectCollaborator.is_active == True,
        ProjectCollaborator.role.in_(["admin", "write"])
    ).first()
    
    return collab is not None


async def _initialize_from_template(project_id: str, template_id: str, db: Session):
    """Initialize project from template"""
    # TODO: Implement template initialization
    pass


async def _initialize_blank_project(project_id: str, db: Session):
    """Initialize blank project with basic files"""
    file_service = FileService()
    
    # Create basic README
    readme_content = "# My CodeForge Project\n\nWelcome to your new project!\n"
    await file_service.create_file(
        project_id=project_id,
        file_path="/README.md",
        content=readme_content,
        user_id="system"
    )


async def _copy_project_files(source_project_id: str, target_project_id: str, db: Session):
    """Copy files from source project to target project"""
    # TODO: Implement file copying
    pass