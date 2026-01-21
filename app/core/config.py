from pydantic_settings import BaseSettings
from functools import lru_cache

import os
class Settings(BaseSettings):
    # Database
    database_url: str = os.getenv('DATABASE_URI')
    
    # OpenAI
    openai_api_key: str = os.getenv('OPENAI_KEY')
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Vector store
    vector_collection_name: str = "document_embeddings"
    
    # File upload
    max_file_size_mb: int = 50
    allowed_extensions: list[str] = ["pdf", "txt", "md"]
    
    class Config:
        env_file = ".env"
        env_prefix = "RAG_API_"


@lru_cache
def get_settings() -> Settings:
    return Settings()
