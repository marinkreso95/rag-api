# RAG API

Multi-project RAG (Retrieval-Augmented Generation) API built with FastAPI, LangChain, and PostgreSQL.

## Features

- **Multi-project support**: Create multiple isolated projects
- **Document management**: Upload PDF, TXT, and MD files per project
- **Multiple chats per project**: Each project can have multiple chat sessions
- **Document-specific chats**: Associate specific documents with each chat
- **Vector search**: pgvector for efficient similarity search
- **Chat history**: Full conversation history with context awareness

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI                               │
├─────────────────────────────────────────────────────────────┤
│  Routes: /projects, /documents, /chats, /messages           │
├─────────────────────────────────────────────────────────────┤
│  Services: DocumentService, AIService, ChatService          │
├─────────────────────────────────────────────────────────────┤
│  Repositories: Project, Document, Chat, Message             │
├─────────────────────────────────────────────────────────────┤
│  LangChain + OpenAI          │     PostgreSQL + pgvector    │
└─────────────────────────────────────────────────────────────┘
```

## Data Model

```
Project (1) ──────< Document (N)
    │
    └──────< Chat (N) ──────< Message (N)
                │
                └──────< ChatDocument (N) >────── Document
```

## Requirements

- Python 3.11+
- PostgreSQL 16+ with pgvector extension
- OpenAI API key

## Installation

### 1. Clone and setup environment

```bash
cd rag-api

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Start PostgreSQL with pgvector

```bash
docker compose up -d
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
```

### 4. Run the API

```bash
# Development mode
fastapi dev app/main.py

# Production mode
fastapi run app/main.py
```

API will be available at http://localhost:8000

## API Endpoints

### Projects

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects` | Create a new project |
| GET | `/projects` | List all projects |
| GET | `/projects/{id}` | Get project by ID |
| PATCH | `/projects/{id}` | Update project |
| DELETE | `/projects/{id}` | Delete project |

### Documents

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/documents` | Upload document |
| GET | `/projects/{id}/documents` | List documents |
| GET | `/projects/{id}/documents/{doc_id}` | Get document |
| DELETE | `/projects/{id}/documents/{doc_id}` | Delete document |

### Chats

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/projects/{id}/chats` | Create chat |
| GET | `/projects/{id}/chats` | List chats |
| GET | `/projects/{id}/chats/{chat_id}` | Get chat |
| PATCH | `/projects/{id}/chats/{chat_id}` | Update chat |
| DELETE | `/projects/{id}/chats/{chat_id}` | Delete chat |
| POST | `/projects/{id}/chats/{chat_id}/documents` | Add documents to chat |

### Messages

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/projects/{id}/chats/{chat_id}/messages` | List messages |
| POST | `/projects/{id}/chats/{chat_id}/messages` | Send message (returns AI response) |

## Usage Example

### 1. Create a project

```bash
curl -X POST http://localhost:8000/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "My Project", "description": "Project for analyzing documents"}'
```

Response:
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "My Project",
  "description": "Project for analyzing documents",
  "created_at": "2025-01-09T10:00:00Z",
  "updated_at": "2025-01-09T10:00:00Z",
  "document_count": 0,
  "chat_count": 0
}
```

### 2. Upload a document

```bash
curl -X POST http://localhost:8000/projects/{project_id}/documents \
  -F "file=@document.pdf"
```

### 3. Create a chat

```bash
curl -X POST http://localhost:8000/projects/{project_id}/chats \
  -H "Content-Type: application/json" \
  -d '{"name": "Analysis Chat", "document_ids": ["doc-uuid-here"]}'
```

### 4. Send a message

```bash
curl -X POST http://localhost:8000/projects/{project_id}/chats/{chat_id}/messages \
  -H "Content-Type: application/json" \
  -d '{"content": "What are the main topics covered in the document?"}'
```

Response:
```json
{
  "message": {
    "id": "msg-uuid",
    "chat_id": "chat-uuid",
    "content": "Based on the document, the main topics are...",
    "sender_type": "ai",
    "created_at": "2025-01-09T10:05:00Z"
  },
  "sources": ["document.pdf (page 1)", "document.pdf (page 3)"]
}
```

## Interactive API Documentation

Once running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
rag-api/
├── app/
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Settings and configuration
│   │   ├── database.py      # Database connection
│   │   └── dependencies.py  # DI for LangChain components
│   ├── models/
│   │   ├── __init__.py
│   │   └── models.py        # SQLModel definitions
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── schemas.py       # Pydantic schemas
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── repositories.py  # Database operations
│   ├── services/
│   │   ├── __init__.py
│   │   ├── document_service.py  # Document processing
│   │   ├── ai_service.py        # LLM interaction
│   │   └── chat_service.py      # Chat orchestration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── projects.py      # Project endpoints
│   │   ├── documents.py     # Document endpoints
│   │   └── chats.py         # Chat & message endpoints
│   ├── __init__.py
│   └── main.py              # FastAPI app
├── docker-compose.yaml
├── init.sql
├── requirements.txt
├── .env.example
└── README.md
```

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `RAG_API_DATABASE_URL` | `postgresql://root:root@localhost:5432/rag_api` | PostgreSQL connection string |
| `RAG_API_OPENAI_API_KEY` | - | OpenAI API key (required) |
| `RAG_API_OPENAI_MODEL` | `gpt-4o-mini` | Chat model |
| `RAG_API_OPENAI_EMBEDDING_MODEL` | `text-embedding-3-small` | Embedding model |
| `RAG_API_VECTOR_COLLECTION_NAME` | `document_embeddings` | Vector collection name |
| `RAG_API_MAX_FILE_SIZE_MB` | `50` | Max upload size in MB |
| `RAG_API_ALLOWED_EXTENSIONS` | `["pdf", "txt", "md"]` | Allowed file types |

## License

MIT
