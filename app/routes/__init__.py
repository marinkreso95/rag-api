from app.routes.projects import router as projects_router
from app.routes.documents import router as documents_router
from app.routes.chats import router as chats_router

__all__ = [
    "projects_router",
    "documents_router",
    "chats_router"
]
