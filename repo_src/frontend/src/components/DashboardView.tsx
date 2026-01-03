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

interface HighlightItem {
  title: string;
  excerpt: string;
  source: string;
  date: string;
}

interface QualitativeInsights {
  recent_highlights: HighlightItem[];
  top_topics: [string, number][];
  knowledge_gaps: string[];
  diversity_score: number;
}

interface TrendDataset {
  label: string;
  data: number[];
}

interface TrendData {
  labels: string[];
  datasets: TrendDataset[];
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

  const getGreeting = () => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  };

  const getDateString = () => {
    const now = new Date();
    return now.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    }).toUpperCase();
  };

  return (
    <div className="dashboard-view">
      {/* Header */}
      <div className="dashboard-header">
        <div className="date-string">{getDateString()}</div>
        <h1 className="greeting">{getGreeting()}</h1>
        <p className="tagline">What patterns emerge from your knowledge today?</p>
      </div>

      {/* Navigation Tabs */}
      <div className="dashboard-nav">
        <button className="nav-tab active">NOW</button>
        <button className="nav-tab">PATTERNS</button>
        <button className="nav-tab">SOURCES</button>
        <button className="nav-tab">HISTORY</button>
      </div>

      <div className="dashboard-content">
        {/* Left Panel - Visualization */}
        <div className="left-panel">
          <div className="network-viz">
            <svg viewBox="0 0 300 300" className="constellation">
              <line x1="150" y1="150" x2="150" y2="80" stroke="rgba(255,255,255,0.3)" strokeWidth="1"/>
              <line x1="150" y1="150" x2="220" y2="130" stroke="rgba(255,255,255,0.3)" strokeWidth="1"/>
              <line x1="150" y1="150" x2="200" y2="200" stroke="rgba(255,255,255,0.3)" strokeWidth="1"/>
              <line x1="150" y1="150" x2="100" y2="200" stroke="rgba(255,255,255,0.3)" strokeWidth="1"/>
              <line x1="150" y1="150" x2="80" y2="150" stroke="rgba(255,255,255,0.3)" strokeWidth="1"/>

              <circle cx="150" cy="150" r="6" fill="#ffffff"/>
              <circle cx="150" cy="80" r="5" fill="rgba(255,255,255,0.7)"/>
              <circle cx="220" cy="130" r="5" fill="rgba(255,255,255,0.7)"/>
              <circle cx="200" cy="200" r="5" fill="rgba(255,255,255,0.7)"/>
              <circle cx="100" cy="200" r="5" fill="rgba(255,255,255,0.7)"/>
              <circle cx="80" cy="150" r="5" fill="rgba(255,255,255,0.7)"/>
            </svg>
            <div className="viz-labels">
              <div className="viz-label" style={{top: '20%', left: '50%'}}>JAY</div>
              <div className="viz-label" style={{top: '35%', right: '10%'}}>CONN.</div>
              <div className="viz-label" style={{bottom: '20%', right: '20%'}}>GROW</div>
              <div className="viz-label" style={{bottom: '20%', left: '15%'}}>SUSTAIN</div>
            </div>
          </div>
          <div className="attention-flow">
            <div className="flow-label">ATTENTION FLOW</div>
            <div className="flow-value">7 DAYS</div>
          </div>

          <div className="metric-cards">
            <div className="pdr-metric-card">
              <div className="metric-value">{formatNumber(metrics.overview.total_items)}</div>
              <div className="metric-label">TOTAL ITEMS</div>
            </div>
            <div className="pdr-metric-card">
              <div className="metric-value">{formatNumber(metrics.overview.total_words)}</div>
              <div className="metric-label">WORDS CAPTURED</div>
            </div>
            <div className="pdr-metric-card">
              <div className="metric-value">{metrics.activity.items_added_last_7d}</div>
              <div className="metric-label">RECENT ACTIVITY</div>
            </div>
          </div>

          {/* NEW: ETL Insights Metrics */}
          <div className="etl-insights-section" style={{marginTop: '2rem'}}>
            <div className="section-header">
              <span className="section-label">ETL INSIGHTS</span>
            </div>
            <div className="metric-cards">
              <div className="pdr-metric-card">
                <div className="metric-value">{(metrics.overview as any).tasks_extracted || 0}</div>
                <div className="metric-label">TASKS EXTRACTED</div>
              </div>
              <div className="pdr-metric-card">
                <div className="metric-value">{(metrics.overview as any).interactions_logged || 0}</div>
                <div className="metric-label">INTERACTIONS</div>
              </div>
              <div className="pdr-metric-card">
                <div className="metric-value">{(metrics.overview as any).files_processed || 0}</div>
                <div className="metric-label">FILES PROCESSED</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Panel - Content */}
        <div className="right-panel">

          {/* Insights / Quests Section */}
          <div className="section-header">
            <span className="section-label">INSIGHTS</span>
            <button className="action-link">
              <span onClick={refreshMetrics} style={{cursor: 'pointer'}}>
                {refreshing ? 'Refreshing...' : 'Refresh →'}
              </span>
            </button>
          </div>

          {/* Highlight Cards */}
          {metrics.insights.recent_highlights.map((highlight, idx) => (
            <div key={idx} className="quest-card">
              <div className="quest-category">{highlight.source.toUpperCase()}</div>
              <h3 className="quest-title">{highlight.title}</h3>
              <p className="quest-description">{highlight.excerpt}</p>
              <div className="quest-action">
                → {new Date(highlight.date).toLocaleDateString('en-US', {
                  month: 'long',
                  day: 'numeric'
                })}
              </div>
            </div>
          ))}

          {/* Active Sources Section */}
          <div className="section-header" style={{marginTop: '3rem'}}>
            <span className="section-label">ACTIVE SOURCES</span>
            <span className="section-meta">{metrics.activity.items_added_last_7d} ITEMS THIS WEEK</span>
          </div>

          <div className="sources-table">
            {metrics.sources.map((source, idx) => (
              <div key={idx} className="source-row">
                <div className="source-name">{source.source_name}</div>
                <div className="source-stat-group">
                  <span className="source-count">{source.recent_items_7d} ITEMS</span>
                  <span className="source-meta">{source.total_items} TOTAL</span>
                </div>
              </div>
            ))}
          </div>

          {/* Topics Section */}
          <div className="section-header" style={{marginTop: '3rem'}}>
            <span className="section-label">EMERGING TOPICS</span>
          </div>

          <div className="topics-grid">
            {metrics.insights.top_topics.map(([topic, score], idx) => (
              <div key={idx} className="topic-card">
                <div className="topic-name-alt">{topic}</div>
                <div className="topic-score-alt">{(score * 100).toFixed(0)}%</div>
              </div>
            ))}
          </div>

          {/* Footer Info */}
          <div className="dashboard-meta">
            <span>Last updated: {formatDate(metrics.last_updated)}</span>
            <span>•</span>
            <span>{metrics.computation_time_ms}ms</span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardView;
