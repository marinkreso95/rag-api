import logging
import tempfile
import time
from dataclasses import dataclass
from uuid import UUID
from typing import Optional
import fitz

from langchain_core.vectorstores import VectorStore
from langchain_core.documents import Document as LangchainDocument
from langchain_text_splitters import TextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from sqlmodel import Session

from app.core import engine
from app.models import Document
from app.repositories import DocumentRepository


@dataclass
class DocumentService:
    vector_store: VectorStore
    text_splitter: TextSplitter
    document_repository: DocumentRepository
    
    def save_document_vectors(
        self,
        document_id: UUID,
        content: bytes
    ):
        """Calculate vectors and store them to vector store."""

        with Session(engine, expire_on_commit=False) as session:
            document = self.document_repository.get_by_id(session, document_id)
            if not document:
                logging.error(f"Document not found")
                return

            langchain_docs = self._convert_to_documents(content, document.file_type, document.name)
            all_splits = self.text_splitter.split_documents(langchain_docs)

            self._add_metadata(all_splits, document, document.project_id)

            self.vector_store.add_documents(all_splits)

            self.document_repository.finish_embedding(
                session, document, len(all_splits)
            )

    async def search(
        self, 
        query: str, 
        project_id: UUID,
        document_ids: Optional[list[UUID]] = None,
        k: int = 5
    ) -> list[LangchainDocument]:
        """Search for relevant documents in vector store."""
        
        # Build filter based on project and optionally specific documents
        filter_dict = {"project_id": str(project_id)}
        
        if document_ids:
            filter_dict = {
                "$and": [
                    {"project_id": str(project_id)},
                    {"document_id": {"$in": [str(doc_id) for doc_id in document_ids]}}
                ]
            }
        

        # return await self.vector_store.asimilarity_search(
        #     query, 
        #     k=k, 
        #     filter=filter_dict
        # )
        # print(query, document_ids, self.vector_store.similarity_search(
        #     query, 
        #     k=k, 
        #     filter=filter_dict
        # ))
        return self.vector_store.similarity_search(
            query, 
            k=k, 
            filter=filter_dict
        )
    
    async def delete_document_vectors(self, document_id: UUID) -> None:
        """Delete all vectors associated with a document."""
        # Note: Implementation depends on vector store capabilities
        # PGVector supports deletion by metadata filter
        try:
            await self.vector_store.adelete(
                filter={"document_id": str(document_id)}
            )
        except Exception:
            # Some vector stores may not support this operation
            pass
    
    def _convert_to_documents(
        self, 
        content: bytes, 
        file_type: str,
        filename: str
    ) -> list[LangchainDocument]:
        """Convert file content to LangChain documents."""
        
        suffix = f".{file_type}"
        
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            
            if file_type == "pdf":
                doc = fitz.open(stream=content, filetype="pdf")
                documents = []

                for page_number, page in enumerate(doc):
                    text = page.get_text()
                    if text.strip():
                        print(text)
                        documents.append(
                            LangchainDocument(
                                page_content=text,
                                metadata={
                                    "source": filename,
                                    "page": page_number + 1
                                }
                            )
                        )

                return documents
            elif file_type in ["txt", "md"]:
                loader = TextLoader(tmp_file.name)
            else:
                # Default to text loader
                loader = TextLoader(tmp_file.name)
            
            return loader.load()

    def _add_metadata(
            self,
            documents: list[LangchainDocument],
            document: Document,
            project_id: UUID
    ) -> None:
        """Add metadata to documents for filtering."""
        for idx, doc in enumerate(documents, 1):
            doc.metadata["document_id"] = str(document.id)
            doc.metadata["document_name"] = document.name
            doc.metadata["project_id"] = str(project_id)
            doc.metadata["chunk_id"] = f"{document.id}:{idx}"
            doc.metadata["chunk_index"] = idx
