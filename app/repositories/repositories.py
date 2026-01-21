from sqlmodel import Session, select, func
from uuid import UUID
from datetime import datetime
from typing import Optional, Sequence

from app.models import Project, Document, Chat, Message, ChatDocument
from app.models.models import DocumentStatus


class ProjectRepository:
    
    def create(self, session: Session, name: str, description: Optional[str] = None) -> Project:
        project = Project(name=name, description=description)
        session.add(project)
        session.commit()
        session.refresh(project)
        return project
    
    def get_by_id(self, session: Session, project_id: UUID) -> Optional[Project]:
        return session.get(Project, project_id)
    
    def get_all(self, session: Session, skip: int = 0, limit: int = 100) -> Sequence[Project]:
        statement = select(Project).offset(skip).limit(limit).order_by(Project.created_at.desc())
        return session.exec(statement).all()
    
    def count(self, session: Session) -> int:
        statement = select(func.count(Project.id))
        return session.exec(statement).one()
    
    def update(self, session: Session, project: Project, name: Optional[str] = None, 
               description: Optional[str] = None) -> Project:
        if name is not None:
            project.name = name
        if description is not None:
            project.description = description
        project.updated_at = datetime.utcnow()
        session.add(project)
        session.commit()
        session.refresh(project)
        return project
    
    def delete(self, session: Session, project: Project) -> None:
        session.delete(project)
        session.commit()
    
    def get_document_count(self, session: Session, project_id: UUID) -> int:
        statement = select(func.count(Document.id)).where(Document.project_id == project_id)
        return session.exec(statement).one()
    
    def get_chat_count(self, session: Session, project_id: UUID) -> int:
        statement = select(func.count(Chat.id)).where(Chat.project_id == project_id)
        return session.exec(statement).one()


class DocumentRepository:
    
    def create(self, session: Session, project_id: UUID, name: str, file_type: str,
               file_size: int, chunk_count: int = 0,
               status: DocumentStatus = DocumentStatus.IN_PROGRESS) -> Document:
        document = Document(
            project_id=project_id,
            name=name,
            file_type=file_type,
            file_size=file_size,
            chunk_count=chunk_count,
            status=status
        )
        session.add(document)
        session.commit()
        session.refresh(document)
        return document
    
    def get_by_id(self, session: Session, document_id: UUID) -> Optional[Document]:
        return session.get(Document, document_id)
    
    def get_by_project(self, session: Session, project_id: UUID, 
                       skip: int = 0, limit: int = 100) -> Sequence[Document]:
        statement = (
            select(Document)
            .where(Document.project_id == project_id)
            .offset(skip).limit(limit)
            .order_by(Document.created_at.desc())
        )
        return session.exec(statement).all()
    
    def count_by_project(self, session: Session, project_id: UUID) -> int:
        statement = select(func.count(Document.id)).where(Document.project_id == project_id)
        return session.exec(statement).one()
    
    def delete(self, session: Session, document: Document) -> None:
        session.delete(document)
        session.commit()
    
    def finish_embedding(self, session: Session, document: Document, chunk_count: int) -> Document:
        document.chunk_count = chunk_count
        document.status = DocumentStatus.SUCCESSFUL
        session.add(document)
        session.commit()
        session.refresh(document)
        return document


class ChatRepository:
    
    def create(self, session: Session, project_id: UUID, name: str = "New Chat",
               document_ids: Optional[list[UUID]] = None) -> Chat:
        chat = Chat(project_id=project_id, name=name)
        session.add(chat)
        session.commit()
        session.refresh(chat)
        
        # Associate documents with chat
        if document_ids:
            for doc_id in document_ids:
                chat_doc = ChatDocument(chat_id=chat.id, document_id=doc_id)
                session.add(chat_doc)
            session.commit()
        
        return chat
    
    def get_by_id(self, session: Session, chat_id: UUID) -> Optional[Chat]:
        return session.get(Chat, chat_id)
    
    def get_by_project(self, session: Session, project_id: UUID,
                       skip: int = 0, limit: int = 100) -> Sequence[Chat]:
        statement = (
            select(Chat)
            .where(Chat.project_id == project_id)
            .offset(skip).limit(limit)
            .order_by(Chat.updated_at.desc())
        )
        return session.exec(statement).all()
    
    def count_by_project(self, session: Session, project_id: UUID) -> int:
        statement = select(func.count(Chat.id)).where(Chat.project_id == project_id)
        return session.exec(statement).one()
    
    def update(self, session: Session, chat: Chat, name: Optional[str] = None) -> Chat:
        if name is not None:
            chat.name = name
        chat.updated_at = datetime.utcnow()
        session.add(chat)
        session.commit()
        session.refresh(chat)
        return chat
    
    def delete(self, session: Session, chat: Chat) -> None:
        session.delete(chat)
        session.commit()
    
    def get_message_count(self, session: Session, chat_id: UUID) -> int:
        statement = select(func.count(Message.id)).where(Message.chat_id == chat_id)
        return session.exec(statement).one()
    
    def get_document_ids(self, session: Session, chat_id: UUID) -> list[UUID]:
        statement = select(ChatDocument.document_id).where(ChatDocument.chat_id == chat_id)
        return list(session.exec(statement).all())
    
    def add_documents(self, session: Session, chat_id: UUID, document_ids: list[UUID]) -> None:
        for doc_id in document_ids:
            existing = session.exec(
                select(ChatDocument)
                .where(ChatDocument.chat_id == chat_id)
                .where(ChatDocument.document_id == doc_id)
            ).first()
            if not existing:
                chat_doc = ChatDocument(chat_id=chat_id, document_id=doc_id)
                session.add(chat_doc)
        session.commit()


class MessageRepository:
    
    def create(self, session: Session, chat_id: UUID, content: str, 
               sender_type: str) -> Message:
        message = Message(chat_id=chat_id, content=content, sender_type=sender_type)
        session.add(message)
        session.commit()
        session.refresh(message)
        return message
    
    def get_by_chat(self, session: Session, chat_id: UUID,
                    skip: int = 0, limit: int = 100) -> Sequence[Message]:
        statement = (
            select(Message)
            .where(Message.chat_id == chat_id)
            .offset(skip).limit(limit)
            .order_by(Message.created_at.asc())
        )
        return session.exec(statement).all()
    
    def count_by_chat(self, session: Session, chat_id: UUID) -> int:
        statement = select(func.count(Message.id)).where(Message.chat_id == chat_id)
        return session.exec(statement).one()
    
    def save_messages(self, session: Session, *messages: Message) -> None:
        for message in messages:
            session.add(message)
        session.commit()
