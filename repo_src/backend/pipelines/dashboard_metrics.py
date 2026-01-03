"""
Dashboard Metrics ETL Pipeline

Phase 2: Hybrid implementation with real ETL insights + mock legacy data
This module provides dashboard metrics combining:
- Real data from ETL insights (tasks, interactions, metrics)
- Mock data for legacy sources (file counts, sizes, etc.)
"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from repo_src.backend.data.schemas import (
    DashboardMetrics,
    SourceMetrics,
    ActivityMetrics,
    QualitativeInsights,
    HighlightItem,
    TrendData,
    TrendDataset
)
from repo_src.backend.database.models import Task, Interaction, DailyMetric, ProcessingLog

# === CACHING CONFIGURATION ===
_metrics_cache: Optional[DashboardMetrics] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_MINUTES = 5


# === MOCK DATA GENERATORS ===

def _generate_mock_source_metrics() -> list[SourceMetrics]:
    """Generate mock metrics for each data source"""
    return [
        SourceMetrics(
            source_name="obsidian",
            total_items=1450,
            total_size_bytes=15728640,  # ~15 MB
            total_words=125000,
            recent_items_7d=23,
            recent_items_30d=87,
            top_tags=[("personal", 45), ("work", 32), ("research", 28)]
        ),
        SourceMetrics(
            source_name="notion",
            total_items=42,
            total_size_bytes=2097152,  # ~2 MB
            total_words=18500,
            recent_items_7d=5,
            recent_items_30d=12,
            top_tags=[("projects", 15), ("meetings", 12), ("ideas", 8)]
        ),
        SourceMetrics(
            source_name="discord",
            total_items=856,
            total_size_bytes=5242880,  # ~5 MB
            total_words=42000,
            recent_items_7d=142,
            recent_items_30d=520,
            top_tags=[("aimibot", 200), ("worldbuilding", 150), ("media", 100)]
        ),
        SourceMetrics(
            source_name="chat_exports",
            total_items=146,
            total_size_bytes=3145728,  # ~3 MB
            total_words=28000,
            recent_items_7d=8,
            recent_items_30d=22,
            top_tags=[("conversations", 80), ("technical", 40), ("brainstorming", 26)]
        )
    ]


def _generate_mock_activity_metrics(sources: list[SourceMetrics]) -> ActivityMetrics:
    """Generate mock activity metrics based on source data"""
    total_recent_7d = sum(s.recent_items_7d for s in sources)
    total_recent_30d = sum(s.recent_items_30d for s in sources)
    total_recent_90d = total_recent_30d * 3  # Mock approximation

    total_items = sum(s.total_items for s in sources)
    growth_rate_7d = (total_recent_7d / total_items * 100) if total_items > 0 else 0.0
    growth_rate_30d = (total_recent_30d / total_items * 100) if total_items > 0 else 0.0

    most_active_source = max(sources, key=lambda s: s.recent_items_7d).source_name

    return ActivityMetrics(
        items_added_last_7d=total_recent_7d,
        items_added_last_30d=total_recent_30d,
        items_added_last_90d=total_recent_90d,
        growth_rate_7d=round(growth_rate_7d, 2),
        growth_rate_30d=round(growth_rate_30d, 2),
        most_active_day=(datetime.now() - timedelta(days=2)).date().isoformat(),
        most_active_source=most_active_source
    )


def _generate_real_insights(db: Session) -> QualitativeInsights:
    """Generate qualitative insights from real ETL data"""

    # Get recent tasks as highlights
    recent_tasks = db.query(Task).filter(
        Task.status == "open"
    ).order_by(desc(Task.extracted_at)).limit(3).all()

    recent_highlights = []
    for task in recent_tasks:
        # Extract filename from path
        import os
        filename = os.path.basename(task.source_file_path)
        source = "obsidian" if "obsidian" in task.source_file_path else "markdown"

        recent_highlights.append(
            HighlightItem(
                title=f"Task: {task.raw_text[:50]}...",
                excerpt=f"{task.raw_text} [Tags: {task.context_tags or 'none'}]",
                source=source,
                date=task.extracted_at.isoformat() if task.extracted_at else datetime.now().isoformat()
            )
        )

    # If we don't have enough tasks, add placeholder
    while len(recent_highlights) < 3:
        recent_highlights.append(
            HighlightItem(
                title="No recent tasks",
                excerpt="Run the ETL pipeline to extract more insights from your documents.",
                source="system",
                date=datetime.now().isoformat()
            )
        )

    # Extract top tags from tasks
    all_tasks = db.query(Task).all()
    tag_counts = {}
    for task in all_tasks:
        if task.context_tags:
            for tag in task.context_tags.split(','):
                tag = tag.strip()
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

    # Convert to normalized scores
    max_count = max(tag_counts.values()) if tag_counts else 1
    top_topics = [
        (tag, count / max_count)
        for tag, count in sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    ]

    # If no tags, use placeholders
    if not top_topics:
        top_topics = [
            ("No topics yet", 0.0),
            ("Run ETL to extract", 0.0)
        ]

    # Generate insights based on data
    task_count = db.query(func.count(Task.id)).scalar()
    interaction_count = db.query(func.count(Interaction.id)).scalar()
    processed_count = db.query(func.count(ProcessingLog.id)).filter(
        ProcessingLog.processing_status == "success"
    ).scalar()

    knowledge_gaps = []
    if task_count < 50:
        knowledge_gaps.append(f"Only {task_count} tasks extracted so far - process more documents to build your task database")
    if interaction_count < 20:
        knowledge_gaps.append(f"Only {interaction_count} interactions logged - more social context will improve insights")
    if processed_count < 100:
        knowledge_gaps.append(f"{processed_count} files processed - run ETL on full dataset for comprehensive analysis")

    if not knowledge_gaps:
        knowledge_gaps = ["System is processing your knowledge base - more insights coming soon"]

    diversity_score = 0.5  # Placeholder

    return QualitativeInsights(
        recent_highlights=recent_highlights,
        top_topics=top_topics,
        knowledge_gaps=knowledge_gaps,
        diversity_score=diversity_score
    )


def _generate_mock_trends() -> TrendData:
    """Generate mock trend data for charts"""
    # Generate labels for last 7 days
    labels = [
        (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(6, -1, -1)
    ]

    # Mock data showing growth pattern
    datasets = [
        TrendDataset(
            label="Items Added Daily",
            data=[12.0, 8.0, 15.0, 23.0, 18.0, 25.0, 31.0]
        ),
        TrendDataset(
            label="Cumulative Items",
            data=[2400.0, 2412.0, 2420.0, 2435.0, 2458.0, 2476.0, 2494.0]
        )
    ]

    return TrendData(
        labels=labels,
        datasets=datasets
    )


# === MAIN ETL FUNCTION ===

async def compute_dashboard_metrics(db: Session = None) -> DashboardMetrics:
    """
    Compute dashboard metrics (Phase 2: Hybrid real + mock data)

    Args:
        db: Database session for real ETL insights

    Returns:
        Complete DashboardMetrics object combining real insights + mock legacy data
    """
    start_time = datetime.now()

    if db is None:
        # Fallback to pure mock if no DB
        sources = _generate_mock_source_metrics()
        activity = _generate_mock_activity_metrics(sources)
        insights = _generate_mock_insights_fallback()
        trends = _generate_mock_trends()
    else:
        # Use real data from ETL insights
        sources = _generate_mock_source_metrics()  # Keep mock for now (legacy file stats)
        activity = _generate_mock_activity_metrics(sources)  # Keep mock for now
        insights = _generate_real_insights(db)  # REAL DATA from ETL
        trends = _generate_real_trends(db)  # REAL DATA from ETL

    # Compute overview (add real ETL stats)
    if db:
        task_count = db.query(func.count(Task.id)).scalar() or 0
        interaction_count = db.query(func.count(Interaction.id)).scalar() or 0
        processed_files = db.query(func.count(ProcessingLog.id)).filter(
            ProcessingLog.processing_status == "success"
        ).scalar() or 0
    else:
        task_count = 0
        interaction_count = 0
        processed_files = 0

    overview = {
        "total_items": sum(s.total_items for s in sources),
        "total_sources": len(sources),
        "total_words": sum(s.total_words for s in sources),
        "total_size_mb": round(sum(s.total_size_bytes for s in sources) / (1024 * 1024), 2),
        "recent_activity_7d": activity.items_added_last_7d,
        # NEW: Real ETL insights
        "tasks_extracted": task_count,
        "interactions_logged": interaction_count,
        "files_processed": processed_files
    }

    # Calculate computation time
    computation_time = (datetime.now() - start_time).total_seconds() * 1000

    return DashboardMetrics(
        overview=overview,
        sources=sources,
        activity=activity,
        insights=insights,
        trends=trends,
        last_updated=datetime.now(),
        computation_time_ms=int(computation_time)
    )


def _generate_mock_insights_fallback() -> QualitativeInsights:
    """Fallback mock insights when DB not available"""
    recent_highlights = [
        HighlightItem(
            title="Database not connected",
            excerpt="Connect to database to see real insights from your documents",
            source="system",
            date=datetime.now().isoformat()
        )
    ]

    return QualitativeInsights(
        recent_highlights=recent_highlights,
        top_topics=[("system", 1.0)],
        knowledge_gaps=["Connect database to extract insights"],
        diversity_score=0.0
    )


def _generate_real_trends(db: Session) -> TrendData:
    """Generate real trend data from daily_metrics table"""

    # Get last 7 days of metrics
    seven_days_ago = datetime.now() - timedelta(days=7)
    seven_days_ago_str = seven_days_ago.strftime("%Y-%m-%d")

    metrics = db.query(DailyMetric).filter(
        DailyMetric.date >= seven_days_ago_str
    ).order_by(DailyMetric.date).all()

    # Generate labels and data
    if metrics:
        labels = [m.date for m in metrics]
        mood_data = [float(m.mood_score) if m.mood_score else 0.0 for m in metrics]
        words_data = [float(m.words_written) for m in metrics]

        datasets = [
            TrendDataset(label="Mood Score", data=mood_data),
            TrendDataset(label="Words Written (scaled)", data=[w/10 for w in words_data])
        ]
    else:
        # Fallback to mock if no data
        labels = [
            (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            for i in range(6, -1, -1)
        ]
        datasets = [
            TrendDataset(label="No data yet", data=[0.0] * 7)
        ]

    return TrendData(labels=labels, datasets=datasets)


# === CACHING LAYER ===

def get_cached_metrics() -> Optional[DashboardMetrics]:
    """
    Get cached metrics if still valid

    Returns:
        Cached DashboardMetrics if cache is fresh, None otherwise
    """
    if _metrics_cache and _cache_timestamp:
        age_minutes = (datetime.now() - _cache_timestamp).total_seconds() / 60
        if age_minutes < CACHE_TTL_MINUTES:
            return _metrics_cache
    return None


def cache_metrics(metrics: DashboardMetrics) -> None:
    """
    Cache computed metrics

    Args:
        metrics: DashboardMetrics to cache
    """
    global _metrics_cache, _cache_timestamp
    _metrics_cache = metrics
    _cache_timestamp = datetime.now()


def clear_cache() -> None:
    """Clear the metrics cache"""
    global _metrics_cache, _cache_timestamp
    _metrics_cache = None
    _cache_timestamp = None


def get_cache_status() -> dict:
    """
    Get current cache status

    Returns:
        Dict with cache hit/miss status and age
    """
    if _metrics_cache and _cache_timestamp:
        age_minutes = (datetime.now() - _cache_timestamp).total_seconds() / 60
        return {
            "status": "hit",
            "age_minutes": round(age_minutes, 2),
            "ttl_minutes": CACHE_TTL_MINUTES,
            "last_updated": _cache_timestamp.isoformat()
        }
    return {
        "status": "miss",
        "age_minutes": None,
        "ttl_minutes": CACHE_TTL_MINUTES,
        "last_updated": None
    }
