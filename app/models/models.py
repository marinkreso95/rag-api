from sqlmodel import SQLModel, Field, Relationship
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional
from enum import Enum


class SenderType(str, Enum):
    HUMAN = "human"
    AI = "ai"


class DocumentStatus(str, Enum):
    PENDING = "Pending"
    IN_PROGRESS = "In progress"
    SUCCESSFUL = "Successful"
    FAILED = "Failed"


# ============== Project ==============

class ProjectBase(SQLModel):
    name: str = Field(max_length=255)
    description: Optional[str] = Field(default=None, max_length=1000)


class Project(ProjectBase, table=True):
    __tablename__ = "projects"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    documents: list["Document"] = Relationship(back_populates="project", cascade_delete=True)
    chats: list["Chat"] = Relationship(back_populates="project", cascade_delete=True)


# ============== Document ==============

class DocumentBase(SQLModel):
    name: str = Field(max_length=255)
    file_type: str = Field(max_length=50)
    file_size: int = Field(default=0)


class Document(DocumentBase, table=True):
    __tablename__ = "documents"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", ondelete="CASCADE")
    chunk_count: int = Field(default=0)
    status: DocumentStatus = Field(default=DocumentStatus.IN_PROGRESS)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    project: Project = Relationship(back_populates="documents")


# ============== Chat ==============

class ChatBase(SQLModel):
    name: str = Field(default="New Chat", max_length=255)


class Chat(ChatBase, table=True):
    __tablename__ = "chats"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="projects.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    project: Project = Relationship(back_populates="chats")
    messages: list["Message"] = Relationship(back_populates="chat", cascade_delete=True)


# ============== Message ==============

class MessageBase(SQLModel):
    content: str
    sender_type: SenderType


class Message(MessageBase, table=True):
    __tablename__ = "messages"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    chat_id: UUID = Field(foreign_key="chats.id", ondelete="CASCADE")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    chat: Chat = Relationship(back_populates="messages")


# ============== Chat-Document Association ==============
# Allows specifying which documents are used in a chat

class ChatDocument(SQLModel, table=True):
    __tablename__ = "chat_documents"
    
    chat_id: UUID = Field(foreign_key="chats.id", primary_key=True, ondelete="CASCADE")
    document_id: UUID = Field(foreign_key="documents.id", primary_key=True, ondelete="CASCADE")
