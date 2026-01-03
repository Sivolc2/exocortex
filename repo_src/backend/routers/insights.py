"""
API endpoints for querying extracted insights (Silver Layer).

These endpoints provide access to structured entities extracted from markdown files:
- Tasks (for GTD dashboard)
- Interactions (for Social Neocortex)
- Daily Metrics (for Quantified Self)
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from datetime import datetime, timedelta

from repo_src.backend.database.connection import get_db
from repo_src.backend.database.models import Task, Interaction, DailyMetric, ProcessingLog
from repo_src.backend.data.schemas import (
    TaskResponse,
    InteractionResponse,
    DailyMetricResponse
)

router = APIRouter(
    prefix="/api/insights",
    tags=["insights"],
)


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(
    status: Optional[str] = Query(None, description="Filter by status: open, done, waiting"),
    context_tags: Optional[str] = Query(None, description="Filter by tags (comma-separated)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
    offset: int = Query(0, ge=0, description="Number of tasks to skip"),
    db: Session = Depends(get_db)
):
    """
    Get tasks extracted from markdown files.

    Query parameters:
    - status: Filter by task status (open, done, waiting)
    - context_tags: Filter by tags (e.g., "work,email")
    - limit: Maximum number of results (default: 100)
    - offset: Skip N results for pagination
    """
    query = db.query(Task)

    # Apply filters
    if status:
        query = query.filter(Task.status == status)

    if context_tags:
        # Simple tag matching - could be improved with proper tag normalization
        for tag in context_tags.split(","):
            tag = tag.strip()
            if tag:
                query = query.filter(Task.context_tags.contains(tag))

    # Order by most recently extracted
    query = query.order_by(desc(Task.extracted_at))

    # Apply pagination
    query = query.limit(limit).offset(offset)

    tasks = query.all()
    return tasks


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    """Get a specific task by ID."""
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.get("/tasks/stats")
async def get_task_stats(db: Session = Depends(get_db)):
    """
    Get statistics about tasks.

    Returns:
    - Total tasks by status
    - Tasks by context tag
    - Tasks created in last 7 days
    - Overdue tasks (if due_date is past)
    """
    total = db.query(func.count(Task.id)).scalar()

    # Count by status
    status_counts = db.query(
        Task.status,
        func.count(Task.id)
    ).group_by(Task.status).all()

    # Recent tasks (last 7 days)
    seven_days_ago = datetime.now() - timedelta(days=7)
    recent_count = db.query(func.count(Task.id)).filter(
        Task.extracted_at >= seven_days_ago
    ).scalar()

    # Overdue tasks
    now = datetime.now()
    overdue_count = db.query(func.count(Task.id)).filter(
        Task.due_date < now,
        Task.status == "open"
    ).scalar()

    return {
        "total": total,
        "by_status": {status: count for status, count in status_counts},
        "recent_7d": recent_count,
        "overdue": overdue_count
    }


@router.get("/interactions", response_model=List[InteractionResponse])
async def get_interactions(
    person_name: Optional[str] = Query(None, description="Filter by person name"),
    min_sentiment: Optional[int] = Query(None, ge=-100, le=100, description="Minimum sentiment score"),
    max_sentiment: Optional[int] = Query(None, ge=-100, le=100, description="Maximum sentiment score"),
    days_back: Optional[int] = Query(None, ge=1, description="Only show interactions from last N days"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """
    Get social interactions extracted from documents.

    Query parameters:
    - person_name: Filter by person (partial match)
    - min_sentiment / max_sentiment: Filter by sentiment range
    - days_back: Only show recent interactions
    - limit / offset: Pagination
    """
    query = db.query(Interaction)

    # Apply filters
    if person_name:
        query = query.filter(Interaction.person_name.contains(person_name))

    if min_sentiment is not None:
        query = query.filter(Interaction.sentiment_score >= min_sentiment)

    if max_sentiment is not None:
        query = query.filter(Interaction.sentiment_score <= max_sentiment)

    if days_back:
        cutoff_date = datetime.now() - timedelta(days=days_back)
        query = query.filter(Interaction.date >= cutoff_date)

    # Order by most recent
    query = query.order_by(desc(Interaction.date))

    # Apply pagination
    query = query.limit(limit).offset(offset)

    interactions = query.all()
    return interactions


@router.get("/interactions/people")
async def get_people_with_last_interaction(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """
    Get list of people with their most recent interaction date.
    Useful for "Social Neocortex" - seeing who you haven't talked to recently.
    """
    # Subquery to get the most recent interaction for each person
    subquery = db.query(
        Interaction.person_name,
        func.max(Interaction.date).label("last_interaction")
    ).group_by(Interaction.person_name).subquery()

    # Join to get full details
    results = db.query(
        subquery.c.person_name,
        subquery.c.last_interaction
    ).order_by(desc(subquery.c.last_interaction)).limit(limit).all()

    return [
        {
            "person_name": name,
            "last_interaction_date": last_interaction.isoformat() if last_interaction else None,
            "days_since": (datetime.now() - last_interaction).days if last_interaction else None
        }
        for name, last_interaction in results
    ]


@router.get("/metrics/daily", response_model=List[DailyMetricResponse])
async def get_daily_metrics(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(90, ge=1, le=365),
    db: Session = Depends(get_db)
):
    """
    Get daily aggregated metrics for quantified self dashboard.

    Query parameters:
    - start_date / end_date: Date range filter
    - limit: Maximum number of days to return (default: 90)
    """
    query = db.query(DailyMetric)

    if start_date:
        query = query.filter(DailyMetric.date >= start_date)

    if end_date:
        query = query.filter(DailyMetric.date <= end_date)

    query = query.order_by(desc(DailyMetric.date)).limit(limit)

    metrics = query.all()
    return metrics


@router.get("/metrics/summary")
async def get_metrics_summary(
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get summary statistics for daily metrics over a time period.
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    metrics = db.query(DailyMetric).filter(
        DailyMetric.date >= cutoff_date
    ).all()

    if not metrics:
        return {
            "days_analyzed": 0,
            "avg_mood": None,
            "total_tasks_completed": 0,
            "total_words_written": 0,
            "total_meetings": 0
        }

    # Calculate averages and totals
    moods = [m.mood_score for m in metrics if m.mood_score is not None]
    avg_mood = sum(moods) / len(moods) if moods else None

    return {
        "days_analyzed": len(metrics),
        "avg_mood": round(avg_mood, 1) if avg_mood else None,
        "total_tasks_completed": sum(m.tasks_completed for m in metrics),
        "total_words_written": sum(m.words_written for m in metrics),
        "total_meetings": sum(m.meetings_recorded for m in metrics)
    }


@router.get("/processing/status")
async def get_processing_status(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Get status of file processing (for monitoring the ETL pipeline).

    Returns recent processing logs showing which files were processed,
    when, and if there were any errors.
    """
    logs = db.query(ProcessingLog).order_by(
        desc(ProcessingLog.last_processed_at)
    ).limit(limit).all()

    return [
        {
            "file_path": log.file_path,
            "status": log.processing_status,
            "last_processed": log.last_processed_at.isoformat() if log.last_processed_at else None,
            "error_message": log.error_message
        }
        for log in logs
    ]


@router.get("/processing/stats")
async def get_processing_stats(db: Session = Depends(get_db)):
    """
    Get overall statistics about the ETL processing.
    """
    total_files = db.query(func.count(ProcessingLog.id)).scalar()
    success_count = db.query(func.count(ProcessingLog.id)).filter(
        ProcessingLog.processing_status == "success"
    ).scalar()
    failed_count = db.query(func.count(ProcessingLog.id)).filter(
        ProcessingLog.processing_status == "failed"
    ).scalar()

    # Get most recently processed file
    latest = db.query(ProcessingLog).order_by(
        desc(ProcessingLog.last_processed_at)
    ).first()

    return {
        "total_files_tracked": total_files,
        "successfully_processed": success_count,
        "failed": failed_count,
        "last_processing_time": latest.last_processed_at.isoformat() if latest and latest.last_processed_at else None
    }
