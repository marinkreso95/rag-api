from sqlmodel import create_engine, Session, SQLModel
from app.core.config import get_settings

settings = get_settings()

engine = create_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    connect_args={"options": "-c idle_in_transaction_session_timeout=0"}
)


def init_db():
    """Initialize database tables."""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Dependency to get database session."""
    with Session(engine) as session:
        yield session
