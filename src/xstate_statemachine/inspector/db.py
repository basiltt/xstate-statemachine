try:
    from typing import Optional
    from sqlmodel import Field, Session, SQLModel, create_engine
    from dotenv import load_dotenv
    import os
    from datetime import datetime, UTC
except ImportError:
    raise ImportError(
        "The 'inspector' feature requires additional dependencies. "
        "Please install them with 'pip install xstate-statemachine[inspector]'"
    )

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///xstate_inspector.db")

# The check_same_thread argument is needed for SQLite to allow it to be
# accessed from different threads, which is necessary because the server
# will run in a background thread.
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

class EventLog(SQLModel, table=True):
    __tablename__ = "event_logs"

    id: Optional[int] = Field(default=None, primary_key=True, index=True)
    session_id: str = Field(index=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str
    data: str # Storing data as JSON string

from contextlib import contextmanager


def create_db_and_tables():
    """Creates the database and all necessary tables if they don't exist."""
    SQLModel.metadata.create_all(engine)


@contextmanager
def get_session():
    """Provides a transactional scope around a series of operations."""
    session = Session(engine)
    try:
        yield session
    finally:
        session.close()
