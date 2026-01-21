from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional
from app.models import SenderType
from app.models.models import DocumentStatus


# ============== Project Schemas ==============

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)


class ProjectResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    document_count: int = 0
    chat_count: int = 0
    
    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: list[ProjectResponse]
    total: int


# ============== Document Schemas ==============

class DocumentResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    file_type: str
    file_size: int
    chunk_count: int
    status: DocumentStatus
    created_at: datetime
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# ============== Chat Schemas ==============

class ChatCreate(BaseModel):
    name: Optional[str] = Field(default="New Chat", max_length=255)
    document_ids: Optional[list[UUID]] = Field(default=None, description="Document IDs to use in this chat")


class ChatUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=255)


class ChatResponse(BaseModel):
    id: UUID
    project_id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    
    class Config:
        from_attributes = True


class ChatListResponse(BaseModel):
    chats: list[ChatResponse]
    total: int


class ChatDetailResponse(ChatResponse):
    document_ids: list[UUID] = []


# ============== Message Schemas ==============

class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    id: UUID
    chat_id: UUID
    content: str
    sender_type: SenderType
    created_at: datetime
    
    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    total: int


class AIResponse(BaseModel):
    message: MessageResponse
    source_refs: dict[str, dict[str, str]] = Field(
        default={},
        description="Per-document source references keyed by citation number"
    )


# ============== Health Check ==============

class HealthResponse(BaseModel):
    status: str
    database: str
    version: str
