"""
Dashboard Router

Provides API endpoints for dashboard metrics and refresh operations.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime

from repo_src.backend.database.connection import get_db
from repo_src.backend.data.schemas import DashboardMetrics, DashboardRefreshStatus
from repo_src.backend.pipelines.dashboard_metrics import (
    compute_dashboard_metrics,
    get_cached_metrics,
    cache_metrics,
    clear_cache,
    get_cache_status
)

router = APIRouter(
    prefix="/api/dashboard",
    tags=["dashboard"],
)


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
    # Check cache first unless force refresh
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
    db: Session = Depends(get_db)
):
    """
    Trigger refresh of dashboard metrics

    Returns:
        Status of refresh operation
    """
    started_at = datetime.now()

    try:
        # Clear existing cache
        clear_cache()

        # Compute fresh metrics
        metrics = await compute_dashboard_metrics(db)
        cache_metrics(metrics)

        completed_at = datetime.now()

        return DashboardRefreshStatus(
            status="complete",
            progress=1.0,
            message="Dashboard metrics refreshed successfully",
            started_at=started_at,
            completed_at=completed_at
        )
    except Exception as e:
        return DashboardRefreshStatus(
            status="error",
            progress=0.0,
            message=f"Error refreshing metrics: {str(e)}",
            started_at=started_at,
            completed_at=datetime.now()
        )


@router.get("/health")
async def dashboard_health():
    """
    Health check for dashboard service

    Returns:
        Dashboard service status and cache information
    """
    cache_status = get_cache_status()

    return {
        "status": "healthy",
        "cache": cache_status,
        "timestamp": datetime.now().isoformat()
    }


@router.delete("/cache")
async def clear_dashboard_cache():
    """
    Clear the dashboard metrics cache

    Returns:
        Confirmation message
    """
    clear_cache()
    return {
        "status": "success",
        "message": "Dashboard cache cleared",
        "timestamp": datetime.now().isoformat()
    }
