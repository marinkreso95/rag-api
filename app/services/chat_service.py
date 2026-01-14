from dataclasses import dataclass
from uuid import UUID
from datetime import datetime
from typing import Optional, Sequence

from sqlmodel import Session

from app.models import Chat, Message, SenderType
from app.repositories import ChatRepository, MessageRepository
from app.services.ai_service import AIService
from app.services.document_service import DocumentService


@dataclass
class ChatService:
    chat_repository: ChatRepository
    message_repository: MessageRepository
    ai_service: AIService
    document_service: DocumentService
    
    def create_chat(
        self, 
        session: Session, 
        project_id: UUID,
        name: str = "New Chat",
        document_ids: Optional[list[UUID]] = None
    ) -> Chat:
        """Create a new chat in a project."""
        return self.chat_repository.create(
            session=session,
            project_id=project_id,
            name=name,
            document_ids=document_ids
        )
    
    def get_chat(self, session: Session, chat_id: UUID) -> Optional[Chat]:
        """Get a chat by ID."""
        return self.chat_repository.get_by_id(session, chat_id)
    
    def get_project_chats(
        self, 
        session: Session, 
        project_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[Chat]:
        """Get all chats in a project."""
        return self.chat_repository.get_by_project(session, project_id, skip, limit)
    
    def update_chat(
        self, 
        session: Session, 
        chat: Chat,
        name: Optional[str] = None
    ) -> Chat:
        """Update chat details."""
        return self.chat_repository.update(session, chat, name)
    
    def delete_chat(self, session: Session, chat: Chat) -> None:
        """Delete a chat and all its messages."""
        self.chat_repository.delete(session, chat)
    
    async def send_message(
        self, 
        session: Session, 
        chat: Chat,
        content: str,
        auto_title: bool = True
    ) -> tuple[Message, Message, list[str]]:
        """
        Send a message and get AI response.
        
        Returns:
            Tuple of (human_message, ai_message, sources)
        """
        # 1. Save human message
        human_message = Message(
            chat_id=chat.id,
            content=content,
            sender_type=SenderType.HUMAN
        )
        session.add(human_message)
        session.commit()
        session.refresh(human_message)
        
        # 2. Get document IDs associated with this chat
        document_ids = self.chat_repository.get_document_ids(session, chat.id)
        #('Message', content, document_ids)
        # 3. Search for relevant documents
        docs = await self.document_service.search(
            query=content,
            project_id=chat.project_id,
            document_ids=document_ids if document_ids else None,
            k=5
        )

        len(docs)
        
        # 4. Get chat history for context
        history = self._get_chat_history(session, chat.id)
        
        # 5. Generate AI response
        answer, sources = self.ai_service.retrieve_answer(
            question=content,
            docs=docs,
            chat_history=history
        )
        
        # 6. Save AI message
        ai_message = Message(
            chat_id=chat.id,
            content=answer,
            sender_type=SenderType.AI
        )
        session.add(ai_message)
        
        # 7. Update chat timestamp
        chat.updated_at = datetime.utcnow()
        session.add(chat)
        
        # 8. Auto-generate title if this is the first message
        if auto_title and len(history) == 0 and chat.name == "New Chat":
            try:
                new_title = self.ai_service.generate_chat_title(content)
                chat.name = new_title
                session.add(chat)
            except Exception:
                pass  # Keep default title if generation fails
        
        session.commit()
        session.refresh(ai_message)
        session.refresh(chat)
        
        return human_message, ai_message, sources
    
    def get_messages(
        self, 
        session: Session, 
        chat_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> Sequence[Message]:
        """Get all messages in a chat."""
        return self.message_repository.get_by_chat(session, chat_id, skip, limit)
    
    def get_message_count(self, session: Session, chat_id: UUID) -> int:
        """Get message count for a chat."""
        return self.message_repository.count_by_chat(session, chat_id)
    
    def add_documents_to_chat(
        self, 
        session: Session, 
        chat_id: UUID,
        document_ids: list[UUID]
    ) -> None:
        """Add documents to an existing chat."""
        self.chat_repository.add_documents(session, chat_id, document_ids)
    
    def _get_chat_history(self, session: Session, chat_id: UUID) -> list[dict]:
        """Get chat history formatted for AI service."""
        messages = self.message_repository.get_by_chat(session, chat_id)
        return [
            {"role": msg.sender_type.value, "content": msg.content}
            for msg in messages
        ]
