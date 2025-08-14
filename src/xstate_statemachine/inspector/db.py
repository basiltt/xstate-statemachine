try:
    from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime
    from sqlalchemy.orm import sessionmaker, declarative_base
    from dotenv import load_dotenv
    import os
    from datetime import datetime
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
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class EventLog(Base):
    __tablename__ = "event_logs"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    event_type = Column(String)
    # Storing complex data as a JSON string for simplicity.
    data = Column(Text)


def create_db_and_tables():
    """Creates the database and all necessary tables if they don't exist."""
    Base.metadata.create_all(bind=engine)
