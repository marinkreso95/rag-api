from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session
from uuid import UUID

from app.core import get_session, get_vector_store, get_text_splitter, get_llm
from app.repositories import ProjectRepository, ChatRepository, MessageRepository, DocumentRepository
from app.services import ChatService, AIService, DocumentService
from app.schemas import (
    ChatCreate,
    ChatUpdate,
    ChatResponse,
    ChatListResponse,
    ChatDetailResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    AIResponse
)

router = APIRouter(prefix="/projects/{project_id}/chats", tags=["chats"])

# Repository instances
project_repo = ProjectRepository()
chat_repo = ChatRepository()
message_repo = MessageRepository()
document_repo = DocumentRepository()


def get_chat_service() -> ChatService:
    ai_service = AIService(llm=get_llm())
    document_service = DocumentService(
        vector_store=get_vector_store(),
        text_splitter=get_text_splitter(),
        document_repository=document_repo
    )
    return ChatService(
        chat_repository=chat_repo,
        message_repository=message_repo,
        ai_service=ai_service,
        document_service=document_service
    )


def _to_response(chat, session: Session) -> ChatResponse:
    """Convert Chat model to response schema."""
    return ChatResponse(
        id=chat.id,
        project_id=chat.project_id,
        name=chat.name,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat_repo.get_message_count(session, chat.id)
    )


def _to_detail_response(chat, session: Session) -> ChatDetailResponse:
    """Convert Chat model to detail response schema."""
    return ChatDetailResponse(
        id=chat.id,
        project_id=chat.project_id,
        name=chat.name,
        created_at=chat.created_at,
        updated_at=chat.updated_at,
        message_count=chat_repo.get_message_count(session, chat.id),
        document_ids=chat_repo.get_document_ids(session, chat.id)
    )


@router.post("", response_model=ChatDetailResponse, status_code=status.HTTP_201_CREATED)
def create_chat(
    project_id: UUID,
    chat_data: ChatCreate,
    session: Session = Depends(get_session),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Create a new chat in a project."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    # Validate document IDs if provided
    if chat_data.document_ids:
        for doc_id in chat_data.document_ids:
            doc = document_repo.get_by_id(session, doc_id)
            if not doc or doc.project_id != project_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Document {doc_id} not found in project"
                )
    
    chat = chat_service.create_chat(
        session=session,
        project_id=project_id,
        name=chat_data.name or "New Chat",
        document_ids=chat_data.document_ids
    )
    
    return _to_detail_response(chat, session)


@router.get("", response_model=ChatListResponse)
def list_chats(
    project_id: UUID,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """List all chats in a project."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    chats = chat_repo.get_by_project(session, project_id, skip, limit)
    total = chat_repo.count_by_project(session, project_id)
    
    return ChatListResponse(
        chats=[_to_response(c, session) for c in chats],
        total=total
    )


@router.get("/{chat_id}", response_model=ChatDetailResponse)
def get_chat(
    project_id: UUID,
    chat_id: UUID,
    session: Session = Depends(get_session)
):
    """Get a chat by ID with its associated documents."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    chat = chat_repo.get_by_id(session, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found in project"
        )
    
    return _to_detail_response(chat, session)


@router.patch("/{chat_id}", response_model=ChatResponse)
def update_chat(
    project_id: UUID,
    chat_id: UUID,
    chat_data: ChatUpdate,
    session: Session = Depends(get_session),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Update a chat's name."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    chat = chat_repo.get_by_id(session, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found in project"
        )
    
    chat = chat_service.update_chat(session, chat, name=chat_data.name)
    return _to_response(chat, session)


@router.delete("/{chat_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat(
    project_id: UUID,
    chat_id: UUID,
    session: Session = Depends(get_session),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Delete a chat and all its messages."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    chat = chat_repo.get_by_id(session, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found in project"
        )
    
    chat_service.delete_chat(session, chat)
    return None


# ============== Messages ==============

@router.get("/{chat_id}/messages", response_model=MessageListResponse)
def list_messages(
    project_id: UUID,
    chat_id: UUID,
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session)
):
    """Get all messages in a chat."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    chat = chat_repo.get_by_id(session, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found in project"
        )
    
    messages = message_repo.get_by_chat(session, chat_id, skip, limit)
    total = message_repo.count_by_chat(session, chat_id)
    
    return MessageListResponse(
        messages=[
            MessageResponse(
                id=m.id,
                chat_id=m.chat_id,
                content=m.content,
                sender_type=m.sender_type,
                created_at=m.created_at
            ) for m in messages
        ],
        total=total
    )


@router.post("/{chat_id}/messages", response_model=AIResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    project_id: UUID,
    chat_id: UUID,
    message_data: MessageCreate,
    session: Session = Depends(get_session),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Send a message and get AI response."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    chat = chat_repo.get_by_id(session, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found in project"
        )
    
    # Send message and get AI response
    human_msg, ai_msg, sources = await chat_service.send_message(
        session=session,
        chat=chat,
        content=message_data.content
    )
    
    return AIResponse(
        message=MessageResponse(
            id=ai_msg.id,
            chat_id=ai_msg.chat_id,
            content=ai_msg.content,
            sender_type=ai_msg.sender_type,
            created_at=ai_msg.created_at
        ),
        sources=sources
    )


@router.post("/{chat_id}/documents", status_code=status.HTTP_204_NO_CONTENT)
def add_documents_to_chat(
    project_id: UUID,
    chat_id: UUID,
    document_ids: list[UUID],
    session: Session = Depends(get_session),
    chat_service: ChatService = Depends(get_chat_service)
):
    """Add documents to an existing chat."""
    # Check project exists
    project = project_repo.get_by_id(session, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with ID {project_id} not found"
        )
    
    chat = chat_repo.get_by_id(session, chat_id)
    if not chat or chat.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chat with ID {chat_id} not found in project"
        )
    
    # Validate document IDs
    for doc_id in document_ids:
        doc = document_repo.get_by_id(session, doc_id)
        if not doc or doc.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document {doc_id} not found in project"
            )
    
    chat_service.add_documents_to_chat(session, chat_id, document_ids)
    return None
