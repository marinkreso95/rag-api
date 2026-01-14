from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core import init_db, get_session
from app.routes import projects_router, documents_router, chats_router
from app.schemas import HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    print("🚀 Starting RAG API...")
    init_db()
    print("✅ Database initialized")
    
    yield
    
    # Shutdown
    print("👋 Shutting down RAG API...")


app = FastAPI(
    title="RAG API",
    description="""
    A multi-project RAG (Retrieval-Augmented Generation) API.
    
    ## Features
    
    - **Projects**: Create and manage multiple projects
    - **Documents**: Upload PDF, TXT, and MD files to projects
    - **Chats**: Create chats within projects to interact with documents
    - **Messages**: Send messages and get AI-powered responses based on document content
    
    ## Architecture
    
    - PostgreSQL with pgvector for vector storage
    - LangChain for document processing and RAG
    - OpenAI for embeddings and chat completion
    """,
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(projects_router)
app.include_router(documents_router)
app.include_router(chats_router)


@app.get("/", response_model=HealthResponse, tags=["health"])
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        database="connected",
        version="1.0.0"
    )


@app.get("/health", response_model=HealthResponse, tags=["health"])
def health():
    """Detailed health check."""
    # Try to get a database session
    try:
        session = next(get_session())
        session.close()
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        database=db_status,
        version="1.0.0"
    )
