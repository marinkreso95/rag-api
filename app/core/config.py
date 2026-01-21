from pydantic_settings import BaseSettings
from functools import lru_cache

import os
class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv('DATABASE_URI')
    
    # OpenAI
    azure_openai_endpoint: str = os.getenv("AZURE_ENDPOINT")
    azure_openai_api_key: str = os.getenv("AZURE_API_OPENAI")
    azure_openai_model: str = "gpt-4.1"
    azure_openai_embedding_model: str = "text-embedding-3-small"
    azure_openai_api_version: str = "2024-12-01-preview"
    azure_openai_api_version_embedding: str = "2024-02-01"
    
    # Vector store
    vector_collection_name: str = "document_embeddings"
    
    # File upload
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "txt", "md"]

    # Azure Blob Storage
    blob_storage_container: str = "rag-api"
    blob_storage_connection_string: str = os.getenv("AZURE_BLOB_URI")
    
    class Config:
        env_file = ".env"
        env_prefix = "RAG_API_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
