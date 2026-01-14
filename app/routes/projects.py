from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from uuid import UUID

from app.core import get_session
from app.repositories import ProjectRepository
from app.schemas import (
    ProjectCreate,
    ProjectUpdate,
    ProjectResponse,
    ProjectListResponse
)

router = APIRouter(prefix="/projects", tags=["projects"])

# Repository instance
project_repo = ProjectRepository()


def _to_response(project, session: Session) -> ProjectResponse:
    """Convert Project model to response schema."""
    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
        updated_at=project.updated_at,
        document_count=project_repo.get_document_count(session, project.id),
        chat_count=project_repo.get_chat_count(session, project.id)
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project_data: ProjectCreate,
    session: Session = Depends(get_session)
):
    """Create a new project."""
    project = project_repo.create(
        session=session,
        name=project_data.name,
        description=project_data.description
    )
    return _to_response(project, session)


@router.get("", response_model=ProjectListResponse)
def list_projects(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """List all projects."""
    projects = project_repo.get_all(session, skip, limit)
    total = project_repo.count(session)
    
    return ProjectListResponse(
        projects=[_to_response(p, session) for p in projects],
        total=total
    )


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: UUID,
    session: Session = Depends(get_session)
):
    """Get a project by ID."""
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    return _to_response(project, session)


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: UUID,
    project_data: ProjectUpdate,
    session: Session = Depends(get_session)
):
    """Update a project."""
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    project = project_repo.update(
        session=session,
        project=project,
        name=project_data.name,
        description=project_data.description
    )
    return _to_response(project, session)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: UUID,
    session: Session = Depends(get_session)
):
    """Delete a project and all its documents and chats."""
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    project_repo.delete(session, project)
    return None
