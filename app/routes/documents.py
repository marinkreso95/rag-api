import io

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, BackgroundTasks
from sqlmodel import Session
from uuid import UUID

from starlette.responses import StreamingResponse

from app.core import get_session, get_settings, get_vector_store, get_text_splitter
from app.repositories import ProjectRepository, DocumentRepository
from app.services import DocumentService
from app.schemas import DocumentResponse, DocumentListResponse
from app.services.blob_storage import AzureBlobStorageService

router = APIRouter(prefix="/projects/{project_id}/documents", tags=["documents"])

# Repository instances
project_repo = ProjectRepository()
document_repo = DocumentRepository()

settings = get_settings()


def get_document_service() -> DocumentService:
    return DocumentService(
        vector_store=get_vector_store(),
        text_splitter=get_text_splitter(),
        document_repository=document_repo
    )


def get_blob_storage_service() -> AzureBlobStorageService:
    return AzureBlobStorageService(
        settings.blob_storage_container,
        settings.blob_storage_connection_string
    )


def _to_response(document) -> DocumentResponse:
    """Convert Document model to response schema."""
    return DocumentResponse(
        id=document.id,
        project_id=document.project_id,
        name=document.name,
        file_type=document.file_type,
        file_size=document.file_size,
        chunk_count=document.chunk_count,
        created_at=document.created_at,
        status=document.status
    )


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    background_tasks: BackgroundTasks,
    project_id: UUID,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    document_service: DocumentService = Depends(get_document_service),
    blob_storage_service: AzureBlobStorageService = Depends(get_blob_storage_service)
):
    """Upload a document to a project."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Validate file extension
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required"
        )
    
    file_ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if file_ext not in settings.allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_ext}' not allowed. Allowed types: {settings.allowed_extensions}"
        )
    
    # Read file content
    content = file.file.read()
    file_size = len(content)
    
    # Check file size
    max_size_bytes = settings.max_file_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
        )

    document = document_repo.create(
        session=session,
        project_id=project_id,
        name=file.filename,
        file_type=file_ext,
        file_size=file_size,
        chunk_count=0,
    )

    blob_storage_service.upload(f"{project_id}/{document.id}.{document.file_type}", content)

    background_tasks.add_task(document_service.save_document_vectors, document.id, content)
    
    return _to_response(document)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """List all documents in a project."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    documents = document_repo.get_by_project(session, project_id, skip, limit)
    total = document_repo.count_by_project(session, project_id)
    
    return DocumentListResponse(
        documents=[_to_response(d) for d in documents],
        total=total
    )


@router.get("/{document_id}")
def get_document(
    project_id: UUID,
    document_id: UUID,
    session: Session = Depends(get_session),
    blob_storage_service: AzureBlobStorageService = Depends(get_blob_storage_service)
):
    """Get a document by ID."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    document = document_repo.get_by_id(session, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found in project"
        )

    blob_name = f"{project_id}/{document.id}.{document.file_type}"
    file = blob_storage_service.download(blob_name)
    file_stream = io.BytesIO(file)

    return StreamingResponse(
        file_stream,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{blob_name}"'
        }
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    project_id: UUID,
    document_id: UUID,
    session: Session = Depends(get_session),
    document_service: DocumentService = Depends(get_document_service),
    blob_storage_service: AzureBlobStorageService = Depends(get_blob_storage_service)
):
    """Delete a document from a project."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    document = document_repo.get_by_id(session, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document with ID {document_id} not found in project"
        )
    
    # Delete vectors from vector store
    await document_service.delete_document_vectors(document_id)

    blob_name = f"{project_id}/{document.id}.{document.file_type}"

    blob_storage_service.delete(blob_name)
    
    # Delete document from database
    document_repo.delete(session, document)
    
    return None
