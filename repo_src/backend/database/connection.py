from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool
import os
from pathlib import Path

# Use absolute path for database to ensure consistent location regardless of startup directory
# Database will be stored in datalake/ directory (project root)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # Get project root (3 levels up from backend/database/)
DATA_DIR = PROJECT_ROOT / "datalake"
DATA_DIR.mkdir(exist_ok=True)  # Create data directory if it doesn't exist

# Default database location
DEFAULT_DB_PATH = DATA_DIR / "exocortex.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_DB_PATH}")

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    if ":memory:" in DATABASE_URL: # Specific setup for in-memory SQLite for testing outside of TestClient
        # This StaticPool is more for when you want a single in-memory DB shared across direct test calls.
        # For TestClient, overriding dependencies with a fresh in-memory DB per test is often preferred.
        # engine = create_engine(DATABASE_URL, connect_args=connect_args, poolclass=StaticPool)
        pass # Handled by test_database.py for specific test engine config

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close() 