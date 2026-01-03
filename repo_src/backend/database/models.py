from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func # for server_default=func.now()
from repo_src.backend.database.connection import Base

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    description = Column(String, index=True, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now()) # server_default for initial creation 

class IndexEntry(Base):
    __tablename__ = "index_entries"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    source = Column(String, index=True, nullable=False, default="unknown")  # obsidian, notion, discord
    description = Column(String, nullable=True)
    tags = Column(String, nullable=True) # Simple comma-separated tags

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Person(Base):
    __tablename__ = "people"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, index=True, nullable=False)
    external_link = Column(String, nullable=True)  # URL or reference to external profile
    contact_info = Column(String, nullable=True)  # Phone, email, social handles, etc.
    unstructured_context = Column(String, nullable=True)  # Free-form notes and context

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

# --- ETL Insights Tables (Silver Layer) ---

class Task(Base):
    """Tasks extracted from markdown files for GTD dashboard"""
    __tablename__ = "tasks"

    id = Column(String, primary_key=True)  # UUID or hash-based ID
    source_file_path = Column(String, index=True, nullable=False)
    raw_text = Column(String, nullable=False)  # e.g., "Buy milk"
    status = Column(String, index=True, nullable=False, default="open")  # open, done, waiting
    due_date = Column(DateTime(timezone=True), nullable=True)
    context_tags = Column(String, nullable=True)  # Comma-separated: "home,shopping"
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class Interaction(Base):
    """Social interactions extracted from various sources (Discord, transcripts, emails)"""
    __tablename__ = "interactions"

    id = Column(String, primary_key=True)  # UUID or hash-based ID
    person_name = Column(String, index=True, nullable=False)
    date = Column(DateTime(timezone=True), index=True, nullable=False)
    sentiment_score = Column(Integer, nullable=True)  # -100 to 100 (stored as int for SQLite compatibility)
    summary = Column(String, nullable=True)
    source_file_path = Column(String, index=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class DailyMetric(Base):
    """Aggregated daily metrics for quantified self dashboard"""
    __tablename__ = "daily_metrics"

    date = Column(String, primary_key=True)  # YYYY-MM-DD format
    mood_score = Column(Integer, nullable=True)  # -100 to 100
    tasks_completed = Column(Integer, default=0)
    words_written = Column(Integer, default=0)
    meetings_recorded = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

class ProcessingLog(Base):
    """Track which files have been processed by the ETL pipeline"""
    __tablename__ = "processing_log"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    file_path = Column(String, unique=True, index=True, nullable=False)
    content_hash = Column(String, nullable=False)  # Hash of file content to detect changes
    last_processed_at = Column(DateTime(timezone=True), server_default=func.now())
    processing_status = Column(String, default="success")  # success, failed, skipped
    error_message = Column(String, nullable=True) 