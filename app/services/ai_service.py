from dataclasses import dataclass
from typing import Optional

from langchain_core.language_models import BaseChatModel
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from pydantic import BaseModel, Field


class AnswerOutput(BaseModel):
    """Structured output from LLM."""
    answer: str = Field(description="The answer to the user's question based on the provided context")
    confidence: float = Field(
        default=1.0, 
        description="Confidence level from 0 to 1",
        ge=0.0,
        le=1.0
    )


SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on the provided context documents.

Instructions:
- Only use information from the provided context to answer questions
- If the context doesn't contain enough information to answer, say so clearly
- Be concise but thorough in your responses
- If you're not sure about something, express appropriate uncertainty
- Reference specific parts of the documents when relevant

Context from documents:
{context}"""

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "{question}")
])


@dataclass
class AIService:
    llm: BaseChatModel
    
    def retrieve_answer(
        self, 
        question: str, 
        docs: list[Document],
        chat_history: Optional[list[dict]] = None
    ) -> tuple[str, list[str]]:
        """
        Generate an answer based on retrieved documents.
        
        Returns:
            Tuple of (answer, source_documents)
        """
        if not docs:
            return "I couldn't find any relevant information in the documents to answer your question.", []
        
        # Prepare context from documents
        context_parts = []
        sources = []
        
        for i, doc in enumerate(docs, 1):
            doc_name = doc.metadata.get("document_name", "Unknown")
            page = doc.metadata.get("page", "N/A")
            context_parts.append(f"[Document {i}: {doc_name}, Page {page}]\n{doc.page_content}")
            
            source = f"{doc_name}"
            if page != "N/A":
                source += f" (page {page})"
            if source not in sources:
                sources.append(source)
        
        context = "\n\n---\n\n".join(context_parts)
        
        # Build messages
        messages = []
        
        # Add chat history if provided
        if chat_history:
            messages.append(SystemMessage(content=SYSTEM_PROMPT.format(context=context)))
            for msg in chat_history[-10:]:  # Limit history to last 10 messages
                if msg["role"] == "human":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            messages.append(HumanMessage(content=question))
        else:
            prompt = RAG_PROMPT.invoke({"context": context, "question": question})
            messages = prompt.to_messages()
        
        # Get response from LLM
        response = self.llm.invoke(messages)
        answer = response.content if hasattr(response, 'content') else str(response)
        
        return answer, sources
    
    def generate_chat_title(self, first_message: str) -> str:
        """Generate a title for a chat based on the first message."""
        prompt = f"""Generate a short, descriptive title (max 5 words) for a chat that starts with this message:

"{first_message[:200]}"

Respond with only the title, no quotes or additional text."""
        
        response = self.llm.invoke([HumanMessage(content=prompt)])
        title = response.content.strip().strip('"\'')
        
        # Limit length
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title or "New Chat"
