# PRD: Knowledge Dashboard Panel

**Project:** Exocortex - Personal Knowledge Dashboard
**Version:** 1.0
**Date:** 2026-01-02
**Status:** Proposal - Awaiting Review
**Author:** Architecture Planning Agent

---

## Executive Summary

This PRD outlines the implementation of a **Knowledge Dashboard Panel** for the Exocortex platform. The dashboard provides a comprehensive, real-time visualization of the user's personal knowledge ecosystem, combining quantitative metrics (item counts, growth trends) with qualitative insights (recent highlights, key themes).

The feature consists of three major components:
1. **ETL Pipeline** - Extract, transform, and aggregate metrics from datalake and index
2. **Backend API** - Serve dashboard metrics and computed insights
3. **Frontend Dashboard View** - Interactive visualization as a new top-level view

**Design Philosophy:** PDR (Personal Development Review) style - focused on reflection, progress tracking, and knowledge system health monitoring.

---

## 1. Goals and Objectives

### Primary Goals
- **Knowledge System Visibility**: Provide a single-pane view of the entire knowledge ecosystem
- **Progress Tracking**: Show growth trends and activity patterns over time
- **Quality Insights**: Surface important content, themes, and gaps
- **Motivation**: Gamify knowledge capture through visualized progress

### Success Metrics
- Dashboard loads in < 2 seconds
- Users check dashboard at least 2x per week
- Metrics update in real-time (< 5 minute lag from data changes)
- Users report improved awareness of knowledge system health

### Non-Goals (Out of Scope for V1)
- Advanced analytics (sentiment analysis, topic modeling)
- Export to PDF/PNG
- Social sharing of dashboard
- Customizable dashboard layouts (V1 uses fixed layout)
- Real-time collaboration or multi-user dashboards

---

## 2. Current State Analysis

### Existing Infrastructure

#### Data Sources ✓ (READY)
- **Datalake**: `/datalake/processed/current/` with 1,450+ Obsidian files, 42 Notion pages, Discord archives, 146 chat exports
- **Index Database**: `knowledge_index.json` with structured metadata (paths, sources, descriptions, tags)
- **SQLite Database**: `app_default.db` with `index_entries` table

#### Backend ✓ (READY FOR EXTENSION)
- **FastAPI** with established router patterns
- **SQLAlchemy ORM** for database queries
- **Data Pipeline Architecture**: Existing `pipelines/data_processing.py` for aggregation

#### Frontend ✓ (READY FOR NEW VIEW)
- **React + TypeScript** with view switcher pattern
- **Existing Views**: `chat`, `knowledge-chat`, `index`, `todo`
- **Component Patterns**: Established with `TodoView.tsx`, `IndexEditor.tsx`

### Gap Analysis

| Component | Current State | Required State | Gap |
|-----------|--------------|----------------|-----|
| Dashboard Metrics Pipeline | Not implemented | ETL pipeline computing metrics | Need pipeline implementation |
| Dashboard API | Not implemented | REST endpoint serving metrics | Need router implementation |
| Dashboard UI | Not implemented | Full dashboard view | Need React component |
| Caching Layer | Not implemented | Cache computed metrics | Need Redis or in-memory cache |
| Scheduled Refresh | Not implemented | Periodic metric recomputation | Need cron job or endpoint |

---

## 3. Proposed Solution

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat Views   │  │ Dashboard    │  │ Todo View    │      │
│  │ (Existing)   │  │ View (NEW)   │  │ (Existing)   │      │
│  └──────────────┘  └──────┬───────┘  └──────────────┘      │
│                            │                                 │
└────────────────────────────┼─────────────────────────────────┘
                             │
                             │ GET /api/dashboard/metrics
                             │ GET /api/dashboard/refresh
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Chat Router  │  │ Dashboard    │  │ Index Router │      │
│  │ (Existing)   │  │ Router (NEW) │  │ (Existing)   │      │
│  └──────────────┘  └──────┬───────┘  └──────────────┘      │
│                            │                                 │
│                            ▼                                 │
│  ┌──────────────────────────────────────────────────┐       │
│  │     Dashboard Metrics Pipeline (NEW)             │       │
│  │  - Extract from datalake/index                   │       │
│  │  - Transform to metrics (counts, trends, etc.)   │       │
│  │  - Load to cache + database                      │       │
│  └──────────────┬───────────────────┬────────────────┘       │
│                 │                   │                        │
└─────────────────┼───────────────────┼────────────────────────┘
                  │                   │
                  ▼                   ▼
          ┌──────────────┐    ┌──────────────┐
          │   Datalake   │    │   Database   │
          │  (Files)     │    │   (SQLite)   │
          │              │    │              │
          │ - processed/ │    │ - index_     │
          │ - index/     │    │   entries    │
          └──────────────┘    └──────────────┘
```

### User Workflow

1. **Dashboard View**
   ```
   User clicks "Dashboard" tab
   → Dashboard loads with latest metrics
   → Shows overview cards (total items, sources breakdown, recent activity)
   → Shows trend charts (growth over time)
   → Shows qualitative insights (recent highlights, top tags)
   → Refresh button to recompute metrics on demand
   ```

2. **Data Refresh**
   ```
   User clicks "Refresh Metrics"
   → Backend triggers ETL pipeline
   → Progress indicator shows computation status
   → Dashboard updates with fresh data
   → Shows "Last updated: X minutes ago"
   ```

---

## 4. Technical Architecture

### 4.1 Dashboard Metrics Data Model

#### Metrics Schema

```python
# In repo_src/backend/data/schemas.py

from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime

class SourceMetrics(BaseModel):
    """Metrics for a single data source"""
    source_name: str  # "obsidian", "notion", "discord", "chat_exports"
    total_items: int
    total_size_bytes: int
    total_words: int
    recent_items_7d: int
    recent_items_30d: int
    top_tags: List[tuple[str, int]]  # (tag, count)

class ActivityMetrics(BaseModel):
    """Activity and growth metrics"""
    items_added_last_7d: int
    items_added_last_30d: int
    items_added_last_90d: int
    growth_rate_7d: float  # percentage
    growth_rate_30d: float
    most_active_day: str  # ISO date
    most_active_source: str

class QualitativeInsights(BaseModel):
    """AI-generated or rule-based insights"""
    recent_highlights: List[Dict[str, str]]  # {title, excerpt, source, date}
    top_topics: List[tuple[str, float]]  # (topic, score)
    knowledge_gaps: List[str]  # Suggested areas to expand
    diversity_score: float  # 0.0-1.0, how diverse the sources are

class TrendData(BaseModel):
    """Time-series data for charts"""
    labels: List[str]  # Dates or time periods
    datasets: List[Dict[str, List[float]]]  # {label, data[]}

class DashboardMetrics(BaseModel):
    """Complete dashboard data"""
    overview: Dict[str, int]  # {total_items, total_sources, total_words, etc.}
    sources: List[SourceMetrics]
    activity: ActivityMetrics
    insights: QualitativeInsights
    trends: TrendData
    last_updated: datetime
    computation_time_ms: int

class DashboardRefreshStatus(BaseModel):
    """Status of ongoing refresh operation"""
    status: str  # "idle", "computing", "complete", "error"
    progress: float  # 0.0-1.0
    message: str
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
```

---

### 4.2 ETL Pipeline Design

#### New Pipeline: `repo_src/backend/pipelines/dashboard_metrics.py`

```python
"""
Dashboard Metrics ETL Pipeline

Extracts data from:
  - datalake/processed/current/
  - datalake/index/knowledge_index.json
  - repo_src/backend/app_default.db

Transforms to:
  - Aggregated statistics
  - Growth trends
  - Qualitative insights (placeholders in V1)

Loads to:
  - In-memory cache (for fast access)
  - Database table (for persistence)
"""

import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from repo_src.backend.data.schemas import DashboardMetrics, SourceMetrics, ActivityMetrics, QualitativeInsights, TrendData

# === CONFIGURATION ===
DATALAKE_PATH = Path("datalake/processed/current")
INDEX_PATH = Path("datalake/index/knowledge_index.json")

# === EXTRACT ===

def extract_index_data() -> List[Dict]:
    """Load knowledge index JSON"""
    with open(INDEX_PATH, 'r') as f:
        return json.load(f)

def extract_file_stats(source_path: Path) -> Dict[str, int]:
    """Compute file statistics for a source directory"""
    files = list(source_path.rglob("*"))
    total_files = len([f for f in files if f.is_file()])
    total_size = sum(f.stat().st_size for f in files if f.is_file())

    # Estimate word count (for text files)
    total_words = 0
    for f in files:
        if f.is_file() and f.suffix in ['.md', '.txt']:
            try:
                content = f.read_text(encoding='utf-8')
                total_words += len(content.split())
            except:
                pass

    return {
        "total_files": total_files,
        "total_size_bytes": total_size,
        "total_words": total_words
    }

def extract_recent_activity(source_path: Path, days: int) -> int:
    """Count files modified in last N days"""
    cutoff = datetime.now() - timedelta(days=days)
    count = 0
    for f in source_path.rglob("*"):
        if f.is_file():
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            if mtime >= cutoff:
                count += 1
    return count

# === TRANSFORM ===

def compute_source_metrics(source_name: str, source_path: Path) -> SourceMetrics:
    """Compute metrics for a single data source"""
    stats = extract_file_stats(source_path)
    recent_7d = extract_recent_activity(source_path, 7)
    recent_30d = extract_recent_activity(source_path, 30)

    # TODO: Extract top tags from index (placeholder)
    top_tags = [("personal", 10), ("work", 8), ("research", 5)]

    return SourceMetrics(
        source_name=source_name,
        total_items=stats["total_files"],
        total_size_bytes=stats["total_size_bytes"],
        total_words=stats["total_words"],
        recent_items_7d=recent_7d,
        recent_items_30d=recent_30d,
        top_tags=top_tags
    )

def compute_activity_metrics(sources: List[SourceMetrics]) -> ActivityMetrics:
    """Compute overall activity metrics"""
    total_recent_7d = sum(s.recent_items_7d for s in sources)
    total_recent_30d = sum(s.recent_items_30d for s in sources)
    total_recent_90d = total_recent_30d * 3  # Placeholder approximation

    total_items = sum(s.total_items for s in sources)
    growth_rate_7d = (total_recent_7d / total_items * 100) if total_items > 0 else 0.0
    growth_rate_30d = (total_recent_30d / total_items * 100) if total_items > 0 else 0.0

    most_active_source = max(sources, key=lambda s: s.recent_items_7d).source_name

    return ActivityMetrics(
        items_added_last_7d=total_recent_7d,
        items_added_last_30d=total_recent_30d,
        items_added_last_90d=total_recent_90d,
        growth_rate_7d=growth_rate_7d,
        growth_rate_30d=growth_rate_30d,
        most_active_day=datetime.now().date().isoformat(),  # Placeholder
        most_active_source=most_active_source
    )

def compute_qualitative_insights(sources: List[SourceMetrics], index_data: List[Dict]) -> QualitativeInsights:
    """
    Generate qualitative insights (AI-powered in V2, rule-based placeholders in V1)

    TODO V2: Use LLM to generate insights from recent content
    """
    # Placeholder insights
    recent_highlights = [
        {
            "title": "Placeholder: Recent Note 1",
            "excerpt": "This is a placeholder for a recent highlight from your knowledge base...",
            "source": "obsidian",
            "date": (datetime.now() - timedelta(days=2)).isoformat()
        },
        {
            "title": "Placeholder: Recent Note 2",
            "excerpt": "Another placeholder highlight showing recent activity...",
            "source": "notion",
            "date": (datetime.now() - timedelta(days=5)).isoformat()
        }
    ]

    top_topics = [
        ("AI & Machine Learning", 0.85),
        ("Personal Development", 0.72),
        ("Software Engineering", 0.68)
    ]

    knowledge_gaps = [
        "Consider adding more content about [Topic X]",
        "Limited recent activity in Discord channels",
        "Notion pages could benefit from more detailed descriptions"
    ]

    # Diversity score: ratio of sources with content
    active_sources = sum(1 for s in sources if s.total_items > 0)
    diversity_score = active_sources / len(sources) if sources else 0.0

    return QualitativeInsights(
        recent_highlights=recent_highlights,
        top_topics=top_topics,
        knowledge_gaps=knowledge_gaps,
        diversity_score=diversity_score
    )

def compute_trend_data(sources: List[SourceMetrics]) -> TrendData:
    """
    Generate time-series data for charts

    TODO V2: Track historical metrics in database for real trends
    """
    # Placeholder: Generate sample trend data for last 7 days
    labels = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(6, -1, -1)]

    datasets = [
        {
            "label": "Items Added",
            "data": [5, 8, 3, 12, 7, 10, 15]  # Placeholder values
        },
        {
            "label": "Total Items",
            "data": [1200, 1205, 1213, 1216, 1228, 1235, 1245, 1260]  # Cumulative
        }
    ]

    return TrendData(
        labels=labels,
        datasets=datasets
    )

# === MAIN ETL FUNCTION ===

async def compute_dashboard_metrics(db: Session = None) -> DashboardMetrics:
    """
    Main ETL function to compute all dashboard metrics

    Args:
        db: Optional database session for querying index_entries

    Returns:
        Complete DashboardMetrics object
    """
    start_time = datetime.now()

    # 1. Extract
    index_data = extract_index_data() if INDEX_PATH.exists() else []

    # 2. Transform: Compute metrics per source
    sources = []
    for source_name in ["obsidian", "notion", "discord", "chat_exports"]:
        source_path = DATALAKE_PATH / source_name
        if source_path.exists():
            metrics = compute_source_metrics(source_name, source_path)
            sources.append(metrics)

    activity = compute_activity_metrics(sources)
    insights = compute_qualitative_insights(sources, index_data)
    trends = compute_trend_data(sources)

    # 3. Compute overview
    overview = {
        "total_items": sum(s.total_items for s in sources),
        "total_sources": len(sources),
        "total_words": sum(s.total_words for s in sources),
        "total_size_mb": round(sum(s.total_size_bytes for s in sources) / (1024 * 1024), 2),
        "recent_activity_7d": activity.items_added_last_7d
    }

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

# === CACHING ===

_metrics_cache: Optional[DashboardMetrics] = None
_cache_timestamp: Optional[datetime] = None
CACHE_TTL_MINUTES = 5

def get_cached_metrics() -> Optional[DashboardMetrics]:
    """Get cached metrics if still valid"""
    if _metrics_cache and _cache_timestamp:
        age = (datetime.now() - _cache_timestamp).total_seconds() / 60
        if age < CACHE_TTL_MINUTES:
            return _metrics_cache
    return None

def cache_metrics(metrics: DashboardMetrics):
    """Cache computed metrics"""
    global _metrics_cache, _cache_timestamp
    _metrics_cache = metrics
    _cache_timestamp = datetime.now()
```

---

### 4.3 Backend API Design

#### New Router: `repo_src/backend/routers/dashboard.py`

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from repo_src.backend.database.connection import get_db
from repo_src.backend.data.schemas import DashboardMetrics, DashboardRefreshStatus
from repo_src.backend.pipelines.dashboard_metrics import (
    compute_dashboard_metrics,
    get_cached_metrics,
    cache_metrics
)

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

# === METRICS ENDPOINTS ===

@router.get("/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    force_refresh: bool = False,
    db: Session = Depends(get_db)
):
    """
    Get dashboard metrics (cached or fresh)

    Args:
        force_refresh: If True, recompute metrics even if cache is valid
        db: Database session

    Returns:
        Complete dashboard metrics
    """
    # Check cache first
    if not force_refresh:
        cached = get_cached_metrics()
        if cached:
            return cached

    # Compute fresh metrics
    metrics = await compute_dashboard_metrics(db)
    cache_metrics(metrics)

    return metrics

@router.post("/refresh", response_model=DashboardRefreshStatus)
async def refresh_dashboard_metrics(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Trigger background refresh of dashboard metrics

    Returns:
        Status of refresh operation
    """
    # For V1: Just compute synchronously (fast enough)
    # V2: Use background task for long-running computation

    metrics = await compute_dashboard_metrics(db)
    cache_metrics(metrics)

    return DashboardRefreshStatus(
        status="complete",
        progress=1.0,
        message="Dashboard metrics refreshed successfully",
        started_at=datetime.now(),
        completed_at=datetime.now()
    )

@router.get("/health")
async def dashboard_health():
    """Health check for dashboard service"""
    cached = get_cached_metrics()
    return {
        "status": "healthy",
        "cache_status": "hit" if cached else "miss",
        "last_updated": cached.last_updated.isoformat() if cached else None
    }
```

**Key Design Decisions:**
- **Caching**: 5-minute TTL to balance freshness with performance
- **Force Refresh**: Allow users to bypass cache on demand
- **Background Tasks**: Prepare for async computation in V2
- **Health Check**: Monitor dashboard service status

---

### 4.4 Frontend Dashboard UI

#### New Component: `repo_src/frontend/src/components/DashboardView.tsx`

```typescript
import React, { useState, useEffect } from 'react';
import './DashboardView.css';

interface DashboardMetrics {
  overview: Record<string, number>;
  sources: SourceMetrics[];
  activity: ActivityMetrics;
  insights: QualitativeInsights;
  trends: TrendData;
  last_updated: string;
  computation_time_ms: number;
}

interface SourceMetrics {
  source_name: string;
  total_items: number;
  total_size_bytes: number;
  total_words: number;
  recent_items_7d: number;
  recent_items_30d: number;
  top_tags: [string, number][];
}

interface ActivityMetrics {
  items_added_last_7d: number;
  items_added_last_30d: number;
  items_added_last_90d: number;
  growth_rate_7d: number;
  growth_rate_30d: number;
  most_active_day: string;
  most_active_source: string;
}

interface QualitativeInsights {
  recent_highlights: Array<{
    title: string;
    excerpt: string;
    source: string;
    date: string;
  }>;
  top_topics: [string, number][];
  knowledge_gaps: string[];
  diversity_score: number;
}

interface TrendData {
  labels: string[];
  datasets: Array<{
    label: string;
    data: number[];
  }>;
}

const DashboardView: React.FC = () => {
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // === API CALLS ===

  const fetchMetrics = async (forceRefresh: boolean = false) => {
    try {
      setLoading(true);
      setError(null);
      const url = `/api/dashboard/metrics${forceRefresh ? '?force_refresh=true' : ''}`;
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch dashboard metrics');
      const data = await response.json();
      setMetrics(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  const refreshMetrics = async () => {
    try {
      setRefreshing(true);
      const response = await fetch('/api/dashboard/refresh', { method: 'POST' });
      if (!response.ok) throw new Error('Failed to refresh metrics');
      await fetchMetrics(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  // === RENDER HELPERS ===

  const formatNumber = (num: number): string => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatDate = (isoDate: string): string => {
    return new Date(isoDate).toLocaleString();
  };

  // === RENDER ===

  if (loading && !metrics) {
    return (
      <div className="dashboard-view loading">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-view error">
        <h2>Error</h2>
        <p>{error}</p>
        <button onClick={() => fetchMetrics()}>Retry</button>
      </div>
    );
  }

  if (!metrics) {
    return (
      <div className="dashboard-view empty">
        <p>No metrics available</p>
      </div>
    );
  }

  return (
    <div className="dashboard-view">
      {/* Header */}
      <div className="dashboard-header">
        <h1>Knowledge Dashboard</h1>
        <div className="header-actions">
          <span className="last-updated">
            Last updated: {formatDate(metrics.last_updated)}
          </span>
          <button
            onClick={refreshMetrics}
            disabled={refreshing}
            className="refresh-button"
          >
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="overview-section">
        <div className="metric-card">
          <div className="metric-value">{formatNumber(metrics.overview.total_items)}</div>
          <div className="metric-label">Total Items</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{metrics.overview.total_sources}</div>
          <div className="metric-label">Active Sources</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{formatNumber(metrics.overview.total_words)}</div>
          <div className="metric-label">Total Words</div>
        </div>
        <div className="metric-card">
          <div className="metric-value">{metrics.overview.total_size_mb} MB</div>
          <div className="metric-label">Storage Used</div>
        </div>
        <div className="metric-card highlight">
          <div className="metric-value">{metrics.activity.items_added_last_7d}</div>
          <div className="metric-label">Added Last 7 Days</div>
        </div>
      </div>

      {/* Activity Section */}
      <div className="activity-section">
        <h2>Activity Overview</h2>
        <div className="activity-stats">
          <div className="stat-item">
            <strong>Last 7 days:</strong> {metrics.activity.items_added_last_7d} items
            ({metrics.activity.growth_rate_7d.toFixed(1)}% growth)
          </div>
          <div className="stat-item">
            <strong>Last 30 days:</strong> {metrics.activity.items_added_last_30d} items
            ({metrics.activity.growth_rate_30d.toFixed(1)}% growth)
          </div>
          <div className="stat-item">
            <strong>Most active source:</strong> {metrics.activity.most_active_source}
          </div>
        </div>
      </div>

      {/* Sources Breakdown */}
      <div className="sources-section">
        <h2>Sources Breakdown</h2>
        <div className="sources-grid">
          {metrics.sources.map((source) => (
            <div key={source.source_name} className="source-card">
              <h3>{source.source_name}</h3>
              <div className="source-metrics">
                <div className="source-stat">
                  <span className="stat-value">{source.total_items}</span>
                  <span className="stat-label">Items</span>
                </div>
                <div className="source-stat">
                  <span className="stat-value">{formatNumber(source.total_words)}</span>
                  <span className="stat-label">Words</span>
                </div>
                <div className="source-stat">
                  <span className="stat-value">{source.recent_items_7d}</span>
                  <span className="stat-label">Recent (7d)</span>
                </div>
              </div>
              <div className="source-tags">
                {source.top_tags.slice(0, 3).map(([tag, count]) => (
                  <span key={tag} className="tag">
                    {tag} ({count})
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Trends Chart (Placeholder for V2) */}
      <div className="trends-section">
        <h2>Growth Trends</h2>
        <div className="chart-placeholder">
          <p>Chart visualization coming in V2</p>
          <p>Data: {metrics.trends.labels.join(', ')}</p>
          {metrics.trends.datasets.map((dataset, idx) => (
            <div key={idx}>
              <strong>{dataset.label}:</strong> {dataset.data.join(', ')}
            </div>
          ))}
        </div>
      </div>

      {/* Insights Section */}
      <div className="insights-section">
        <h2>Insights</h2>

        {/* Recent Highlights */}
        <div className="insights-subsection">
          <h3>Recent Highlights</h3>
          <div className="highlights-list">
            {metrics.insights.recent_highlights.map((highlight, idx) => (
              <div key={idx} className="highlight-item">
                <div className="highlight-title">{highlight.title}</div>
                <div className="highlight-excerpt">{highlight.excerpt}</div>
                <div className="highlight-meta">
                  {highlight.source} • {new Date(highlight.date).toLocaleDateString()}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Top Topics */}
        <div className="insights-subsection">
          <h3>Top Topics</h3>
          <div className="topics-list">
            {metrics.insights.top_topics.map(([topic, score], idx) => (
              <div key={idx} className="topic-item">
                <span className="topic-name">{topic}</span>
                <div className="topic-bar">
                  <div
                    className="topic-bar-fill"
                    style={{ width: `${score * 100}%` }}
                  ></div>
                </div>
                <span className="topic-score">{(score * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>

        {/* Knowledge Gaps */}
        <div className="insights-subsection">
          <h3>Suggestions</h3>
          <ul className="gaps-list">
            {metrics.insights.knowledge_gaps.map((gap, idx) => (
              <li key={idx}>{gap}</li>
            ))}
          </ul>
        </div>

        {/* Diversity Score */}
        <div className="insights-subsection">
          <h3>Source Diversity</h3>
          <div className="diversity-meter">
            <div
              className="diversity-fill"
              style={{ width: `${metrics.insights.diversity_score * 100}%` }}
            ></div>
          </div>
          <p>
            {(metrics.insights.diversity_score * 100).toFixed(0)}% of sources are active
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="dashboard-footer">
        <p>Computed in {metrics.computation_time_ms}ms</p>
      </div>
    </div>
  );
};

export default DashboardView;
```

#### Modified: `repo_src/frontend/src/App.tsx`

```typescript
// Add to view state type
type ViewMode = 'chat' | 'knowledge-chat' | 'index' | 'todo' | 'dashboard';  // Add 'dashboard'

// Add to imports
import DashboardView from './components/DashboardView';

// Add to view switcher buttons
<button
  onClick={() => setCurrentView('dashboard')}
  className={currentView === 'dashboard' ? 'active' : ''}
>
  Dashboard
</button>

// Add to view rendering
{currentView === 'dashboard' && <DashboardView />}
```

#### New Stylesheet: `repo_src/frontend/src/components/DashboardView.css`

```css
.dashboard-view {
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  background: var(--bg-primary, #ffffff);
}

/* Header */
.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.dashboard-header h1 {
  font-size: 2rem;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.last-updated {
  color: var(--text-secondary, #666);
  font-size: 0.9rem;
}

.refresh-button {
  padding: 0.5rem 1rem;
  background: var(--primary-color, #007bff);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: background 0.2s;
}

.refresh-button:hover:not(:disabled) {
  background: var(--primary-color-dark, #0056b3);
}

.refresh-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Overview Cards */
.overview-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: var(--bg-secondary, #f8f9fa);
  padding: 1.5rem;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.metric-card.highlight {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.metric-value {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.metric-label {
  font-size: 0.9rem;
  color: var(--text-secondary, #666);
}

.metric-card.highlight .metric-label {
  color: rgba(255,255,255,0.9);
}

/* Activity Section */
.activity-section {
  margin-bottom: 2rem;
}

.activity-stats {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  background: var(--bg-secondary, #f8f9fa);
  border-radius: 8px;
}

.stat-item {
  font-size: 1rem;
}

/* Sources Section */
.sources-section {
  margin-bottom: 2rem;
}

.sources-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.source-card {
  background: var(--bg-secondary, #f8f9fa);
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.source-card h3 {
  font-size: 1.2rem;
  margin-bottom: 1rem;
  text-transform: capitalize;
}

.source-metrics {
  display: flex;
  justify-content: space-around;
  margin-bottom: 1rem;
}

.source-stat {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.source-stat .stat-value {
  font-size: 1.5rem;
  font-weight: 600;
}

.source-stat .stat-label {
  font-size: 0.8rem;
  color: var(--text-secondary, #666);
}

.source-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.source-tags .tag {
  background: var(--primary-color-light, #e7f3ff);
  color: var(--primary-color, #007bff);
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
}

/* Trends Section */
.trends-section {
  margin-bottom: 2rem;
}

.chart-placeholder {
  background: var(--bg-secondary, #f8f9fa);
  padding: 2rem;
  border-radius: 8px;
  text-align: center;
}

/* Insights Section */
.insights-section {
  margin-bottom: 2rem;
}

.insights-subsection {
  margin-bottom: 1.5rem;
  background: var(--bg-secondary, #f8f9fa);
  padding: 1.5rem;
  border-radius: 8px;
}

.insights-subsection h3 {
  font-size: 1.1rem;
  margin-bottom: 1rem;
}

.highlights-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.highlight-item {
  padding: 1rem;
  background: white;
  border-left: 4px solid var(--primary-color, #007bff);
  border-radius: 4px;
}

.highlight-title {
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.highlight-excerpt {
  color: var(--text-secondary, #666);
  margin-bottom: 0.5rem;
}

.highlight-meta {
  font-size: 0.85rem;
  color: var(--text-tertiary, #999);
}

.topics-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.topic-name {
  flex: 0 0 200px;
  font-weight: 500;
}

.topic-bar {
  flex: 1;
  height: 20px;
  background: var(--bg-tertiary, #e0e0e0);
  border-radius: 10px;
  overflow: hidden;
}

.topic-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
}

.topic-score {
  flex: 0 0 50px;
  text-align: right;
  font-weight: 600;
}

.gaps-list {
  list-style: none;
  padding: 0;
}

.gaps-list li {
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--border-color, #e0e0e0);
}

.gaps-list li:last-child {
  border-bottom: none;
}

.diversity-meter {
  height: 30px;
  background: var(--bg-tertiary, #e0e0e0);
  border-radius: 15px;
  overflow: hidden;
  margin-bottom: 0.5rem;
}

.diversity-fill {
  height: 100%;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  transition: width 0.3s ease;
}

/* Footer */
.dashboard-footer {
  text-align: center;
  color: var(--text-secondary, #666);
  font-size: 0.85rem;
  padding-top: 1rem;
  border-top: 1px solid var(--border-color, #e0e0e0);
}

/* Loading and Error States */
.dashboard-view.loading,
.dashboard-view.error,
.dashboard-view.empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid var(--bg-secondary, #f8f9fa);
  border-top-color: var(--primary-color, #007bff);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
```

---

## 5. Implementation Phases

### Phase 1: ETL Pipeline & Backend (Days 1-3)
**Goal**: Compute and serve basic metrics

- [ ] Create `dashboard_metrics.py` pipeline
- [ ] Implement extract functions (datalake, index)
- [ ] Implement transform functions (compute metrics)
- [ ] Add caching layer (in-memory)
- [ ] Create `dashboard.py` router
- [ ] Implement `/api/dashboard/metrics` endpoint
- [ ] Implement `/api/dashboard/refresh` endpoint
- [ ] Write unit tests for pipeline

**Deliverable**: Backend API serving dashboard metrics

---

### Phase 2: Frontend Dashboard (Days 4-6)
**Goal**: Visualize metrics in UI

- [ ] Create `DashboardView.tsx` component
- [ ] Implement overview cards section
- [ ] Implement sources breakdown section
- [ ] Implement activity stats section
- [ ] Add refresh button and loading states
- [ ] Style with `DashboardView.css`
- [ ] Integrate into `App.tsx` as new view
- [ ] Add dashboard tab to navigation

**Deliverable**: Functional dashboard UI with all sections

---

### Phase 3: Insights & Trends (Days 7-9)
**Goal**: Add qualitative insights

- [ ] Implement placeholder insights generation
- [ ] Add recent highlights section
- [ ] Add top topics section
- [ ] Add knowledge gaps suggestions
- [ ] Add diversity score meter
- [ ] Implement trend data (placeholder for V2 charts)
- [ ] Polish UI/UX

**Deliverable**: Complete dashboard with insights

---

### Phase 4: Testing & Polish (Days 10-11)
**Goal**: Production-ready feature

- [ ] Unit tests for ETL pipeline
- [ ] Integration tests for API endpoints
- [ ] Frontend component tests
- [ ] E2E test for dashboard view
- [ ] Performance testing (large datalakes)
- [ ] Error handling and edge cases
- [ ] Documentation

**Deliverable**: Stable, tested dashboard feature

---

## 6. Data Flow Diagrams

### Dashboard Metrics Flow

```
┌──────────────────────────────────────────────────────────────┐
│  USER                                                         │
└────┬─────────────────────────────────────────────────────────┘
     │
     │ 1. Clicks "Dashboard" tab
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (DashboardView)                                    │
│  - componentDidMount() triggers fetchMetrics()              │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 2. GET /api/dashboard/metrics
     ▼
┌─────────────────────────────────────────────────────────────┐
│  BACKEND (Dashboard Router)                                  │
│  - Check cache (5min TTL)                                   │
│  - If cache miss: Call compute_dashboard_metrics()          │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 3. ETL Pipeline starts
     ▼
┌─────────────────────────────────────────────────────────────┐
│  DASHBOARD METRICS PIPELINE                                  │
│  ┌────────────────────────────────────────────────┐         │
│  │ EXTRACT                                        │         │
│  │ - Read datalake/processed/current/             │         │
│  │ - Read datalake/index/knowledge_index.json     │         │
│  │ - Query app_default.db (index_entries)         │         │
│  └────────────────┬───────────────────────────────┘         │
│                   │                                          │
│                   │ 4. File stats, word counts, etc.        │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────┐         │
│  │ TRANSFORM                                      │         │
│  │ - Compute source metrics (per source)          │         │
│  │ - Compute activity metrics (7d, 30d, 90d)      │         │
│  │ - Compute qualitative insights (placeholders)  │         │
│  │ - Compute trend data (time-series)             │         │
│  │ - Build overview object                        │         │
│  └────────────────┬───────────────────────────────┘         │
│                   │                                          │
│                   │ 5. Structured metrics                    │
│                   ▼                                          │
│  ┌────────────────────────────────────────────────┐         │
│  │ LOAD                                           │         │
│  │ - Cache in memory (5min TTL)                   │         │
│  │ - (Optional V2: Save to database)              │         │
│  └────────────────────────────────────────────────┘         │
└────┬────────────────────────────────────────────────────────┘
     │
     │ 6. Return DashboardMetrics JSON
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FRONTEND (DashboardView)                                    │
│  - Parse metrics JSON                                       │
│  - Render overview cards                                    │
│  - Render sources grid                                      │
│  - Render activity stats                                    │
│  - Render insights sections                                 │
└─────────────────────────────────────────────────────────────┘
```

---

## 7. V2 Enhancements (Future)

### 7.1 Advanced Analytics
- **LLM-Generated Insights**: Use Claude to analyze recent content and generate meaningful summaries
- **Topic Modeling**: Automatic extraction of themes using NLP
- **Sentiment Analysis**: Track emotional tone of notes over time
- **Knowledge Graph**: Visual network of interconnected concepts

### 7.2 Interactive Charts
- **Chart.js Integration**: Replace placeholder with real time-series charts
- **Drill-Down**: Click on metrics to see detailed breakdowns
- **Comparison View**: Compare current period to previous periods
- **Custom Date Ranges**: User-selectable time ranges for analysis

### 7.3 Personalization
- **Customizable Widgets**: Drag-and-drop dashboard layout
- **Metric Preferences**: Choose which metrics to display prominently
- **Goals & Targets**: Set knowledge capture goals and track progress
- **Notifications**: Alert when goals are reached or patterns detected

### 7.4 Export & Sharing
- **PDF Export**: Generate PDF report of dashboard
- **Email Digests**: Weekly/monthly email summary
- **Public Dashboard**: Shareable read-only view (with privacy controls)

---

## 8. Success Metrics

### 8.1 Performance Metrics
- [ ] Dashboard loads in < 2 seconds (cached)
- [ ] Fresh computation completes in < 10 seconds
- [ ] API response time < 500ms (cached)
- [ ] ETL pipeline scales to 10,000+ files

### 8.2 User Engagement Metrics
- [ ] Users visit dashboard 2+ times per week
- [ ] Average session time on dashboard > 30 seconds
- [ ] Users click "Refresh" at least once per visit
- [ ] Dashboard view is in top 3 most-visited views

### 8.3 Functional Metrics
- [ ] Metrics accuracy: 100% match with ground truth
- [ ] Cache hit rate > 80%
- [ ] Zero errors in production
- [ ] Graceful degradation if datalake unavailable

---

## 9. Testing Strategy

### 9.1 Unit Tests

**Backend (`tests/test_dashboard_metrics.py`)**
```python
def test_extract_index_data():
    """Test loading knowledge_index.json"""

def test_extract_file_stats():
    """Test computing file statistics"""

def test_compute_source_metrics():
    """Test metrics computation for single source"""

def test_compute_activity_metrics():
    """Test activity aggregation"""

def test_compute_qualitative_insights():
    """Test insights generation"""

def test_caching():
    """Test cache hit/miss logic"""
```

**Frontend (`src/components/__tests__/DashboardView.test.tsx`)**
```typescript
describe('DashboardView', () => {
  test('renders loading state initially', () => { ... });
  test('fetches and displays metrics', async () => { ... });
  test('refresh button triggers API call', async () => { ... });
  test('handles API errors gracefully', async () => { ... });
});
```

### 9.2 Integration Tests

```python
def test_full_dashboard_flow():
    """
    End-to-end test: API call → ETL → Cache → Response
    """

def test_dashboard_refresh():
    """
    Test: POST /refresh → Compute → Cache → GET /metrics
    """
```

### 9.3 E2E Tests (Playwright)

```typescript
test('user can view dashboard', async ({ page }) => {
  await page.goto('/');
  await page.click('button:has-text("Dashboard")');
  await expect(page.locator('.dashboard-view')).toBeVisible();
  await expect(page.locator('.metric-card')).toHaveCount(5);
});

test('user can refresh metrics', async ({ page }) => {
  await page.goto('/dashboard');
  await page.click('button:has-text("Refresh")');
  await expect(page.locator('.refresh-button')).toBeDisabled();
  await expect(page.locator('.refresh-button')).toBeEnabled({ timeout: 15000 });
});
```

---

## 10. Open Questions for Review

### 10.1 Design Decisions

1. **Metrics Persistence**:
   - Should metrics be saved to database or only cached?
   - Suggestion: V1 cache only, V2 add database for historical trends

2. **Refresh Strategy**:
   - Manual refresh only or automatic periodic refresh?
   - Suggestion: V1 manual + cache, V2 add automatic refresh every 1 hour

3. **Insights Generation**:
   - Use LLM for insights in V1 or wait for V2?
   - Suggestion: V1 placeholders, V2 LLM integration

4. **Chart Library**:
   - Which charting library? (Chart.js, Recharts, D3.js)
   - Suggestion: Chart.js for simplicity

5. **Mobile Responsiveness**:
   - Optimize for mobile in V1 or desktop-first?
   - Suggestion: Desktop-first V1, responsive design V2

### 10.2 Technical Questions

1. **ETL Performance**:
   - Run in background thread or async task?
   - Suggestion: Synchronous for V1 (< 10s), async in V2

2. **Cache Strategy**:
   - Redis vs in-memory cache?
   - Suggestion: In-memory V1, Redis V2 if needed

3. **Historical Data**:
   - Store snapshots for trend analysis?
   - Suggestion: V2 feature, add time-series database

---

## 11. Conclusion

The Knowledge Dashboard Panel provides a comprehensive view of the user's personal knowledge ecosystem, combining quantitative metrics with qualitative insights. The implementation is straightforward, leveraging existing architecture (datalake, index, FastAPI, React) and can be delivered in 10-11 days.

### Key Strengths
- ✅ Foundation exists (datalake, index, database)
- ✅ Clear ETL pipeline with extract/transform/load pattern
- ✅ Caching strategy for performance
- ✅ Room for growth (V2 enhancements)

### Recommended Next Steps
1. Review and approve this PRD
2. Resolve open questions (Section 10)
3. Begin Phase 1 implementation (ETL pipeline)
4. Iterate with user feedback after each phase

---

**END OF PRD**
