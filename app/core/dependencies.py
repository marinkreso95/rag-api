from functools import lru_cache
from langchain_openai import AzureOpenAIEmbeddings, AzureChatOpenAI
from langchain_postgres import PGVector
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import get_settings

settings = get_settings()


@lru_cache
def get_embeddings() -> AzureOpenAIEmbeddings:
    return AzureOpenAIEmbeddings(
        model=settings.azure_openai_embedding_model,
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version_embedding,

    )


@lru_cache
def get_llm() -> AzureChatOpenAI:
    return AzureChatOpenAI(
        model=settings.azure_openai_model,
        api_key=settings.azure_openai_api_key,
        azure_endpoint=settings.azure_openai_endpoint,
        api_version=settings.azure_openai_api_version,
        temperature=0.0
    )

@lru_cache
def get_vector_store() -> PGVector:
    return PGVector(
        embeddings=get_embeddings(),
        collection_name=settings.vector_collection_name,
        connection=settings.database_url,
        use_jsonb=True,
        engine_args={
            "pool_pre_ping": True,
            "connect_args": {
                "options": "-c idle_in_transaction_session_timeout=0"
            }
        }
    )


@lru_cache
def get_text_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
        separators=["\n\n", "\n", " ", ""]
    )
