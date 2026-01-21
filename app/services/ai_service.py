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


SYSTEM_PROMPT = """Si koristen AI pomočnik, ki odgovarja izključno na podlagi priloženih kontekstnih dokumentov.

Pravila:
- Vedno odgovarjaj samo v slovenščini.
- Uporabi izključno informacije iz priloženega konteksta. Ne uporabljaj splošnega znanja ali ugibanja.
- Če v kontekstu ni dovolj informacij, jasno povej: "V priloženem kontekstu ni dovolj informacij za odgovor."
- Ne izmišljaj si dejstev, številk, imen, datumov ali citatov.
- Vsako pomembno trditev podpri s citatom v obliki [1][2], ki se ujema z oznakami dokumentov v kontekstu.
- Citiraj samo številke/oznake, ki se pojavijo v kontekstu.
- Če dokumenti vsebujejo nasprotujoče si informacije, to izrecno omeni in navedi ustrezne citate.

Kontekst iz dokumentov:
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
    ) -> tuple[str, dict[str, dict[str, str]]]:
        if not docs:
            return (
                "I couldn't find any relevant information in the documents to answer your question.",
                {}
            )

        context_parts = []
        source_refs: dict[str, dict[str, str]] = {}
        document_to_ref: dict[str, int] = {}
        ref_counter = 1

        for i, doc in enumerate(docs, 1):
            doc_name = doc.metadata.get("document_name", "Unknown")
            document_id = doc.metadata.get("document_id", "")

            doc_key = document_id or doc_name
            if doc_key not in document_to_ref:
                document_to_ref[doc_key] = ref_counter
                source_refs[str(ref_counter)] = {
                    "document_id": str(document_id),
                    "document_title": str(doc_name),
                }
                ref_counter += 1

            ref_num = document_to_ref[doc_key]
            context_parts.append(f"[{ref_num}] {doc_name}\n{doc.page_content}")


        context = "\n\n---\n\n".join(context_parts)
        print(context)
        
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
        
        return answer, source_refs
    
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
