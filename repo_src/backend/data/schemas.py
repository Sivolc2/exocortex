from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class ItemBase(BaseModel):
    name: str
    description: Optional[str] = None

class ItemCreate(ItemBase):
    """Schema for creating a new item"""
    pass

class ItemUpdate(BaseModel):
    """Schema for updating an existing item"""
    name: Optional[str] = None
    description: Optional[str] = None

class ItemResponse(ItemBase):
    """Schema for returning item data in responses"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True # Updated from orm_mode for Pydantic V2 compatibility 

# --- Schemas for LLM Chat ---

class ChatRequest(BaseModel):
    """Schema for a chat request from the frontend."""
    prompt: str
    selection_model: Optional[str] = None
    execution_model: Optional[str] = None
    enabled_sources: Optional[dict] = None
    max_turns: Optional[int] = None

class FileTokenInfo(BaseModel):
    """Schema for file and its token count."""
    file_path: str
    token_count: int

class ChatResponse(BaseModel):
    """Schema for a chat response sent to the frontend."""
    response: str
    selected_files: Optional[List[str]] = None
    file_token_info: Optional[List[FileTokenInfo]] = None
    total_tokens: Optional[int] = None 
    
# --- Schemas for Structured Index ---

class IndexEntryBase(BaseModel):
    file_path: str
    source: str = "unknown"
    description: Optional[str] = None
    tags: Optional[str] = None

class IndexEntryCreate(IndexEntryBase):
    pass

class IndexEntryUpdate(BaseModel):
    source: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None

class IndexEntryResponse(IndexEntryBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

# --- Schemas for People Tracking ---

class PersonBase(BaseModel):
    name: str
    external_link: Optional[str] = None
    contact_info: Optional[str] = None
    unstructured_context: Optional[str] = None

class PersonCreate(PersonBase):
    """Schema for creating a new person entry"""
    pass

class PersonUpdate(BaseModel):
    """Schema for updating an existing person entry"""
    name: Optional[str] = None
    external_link: Optional[str] = None
    contact_info: Optional[str] = None
    unstructured_context: Optional[str] = None

class PersonResponse(PersonBase):
    """Schema for returning person data in responses"""
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# --- Schemas for Dashboard Metrics ---

class SourceMetrics(BaseModel):
    """Metrics for a single data source"""
    source_name: str
    total_items: int
    total_size_bytes: int
    total_words: int
    recent_items_7d: int
    recent_items_30d: int
    top_tags: List[tuple[str, int]]

class ActivityMetrics(BaseModel):
    """Activity and growth metrics"""
    items_added_last_7d: int
    items_added_last_30d: int
    items_added_last_90d: int
    growth_rate_7d: float
    growth_rate_30d: float
    most_active_day: str
    most_active_source: str

class HighlightItem(BaseModel):
    """A single highlight item"""
    title: str
    excerpt: str
    source: str
    date: str

class QualitativeInsights(BaseModel):
    """AI-generated or rule-based insights"""
    recent_highlights: List[HighlightItem]
    top_topics: List[tuple[str, float]]
    knowledge_gaps: List[str]
    diversity_score: float

class TrendDataset(BaseModel):
    """A single dataset for trend charts"""
    label: str
    data: List[float]

class TrendData(BaseModel):
    """Time-series data for charts"""
    labels: List[str]
    datasets: List[TrendDataset]

class DashboardMetrics(BaseModel):
    """Complete dashboard data"""
    overview: dict
    sources: List[SourceMetrics]
    activity: ActivityMetrics
    insights: QualitativeInsights
    trends: TrendData
    last_updated: datetime
    computation_time_ms: int

class DashboardRefreshStatus(BaseModel):
    """Status of ongoing refresh operation"""
    status: str
    progress: float
    message: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

# --- Schemas for ETL Insights (Silver Layer) ---

class TaskBase(BaseModel):
    source_file_path: str
    raw_text: str
    status: str = "open"  # open, done, waiting
    due_date: Optional[datetime] = None
    context_tags: Optional[str] = None

class TaskCreate(TaskBase):
    """Schema for creating a new task"""
    pass

class TaskUpdate(BaseModel):
    """Schema for updating an existing task"""
    raw_text: Optional[str] = None
    status: Optional[str] = None
    due_date: Optional[datetime] = None
    context_tags: Optional[str] = None

class TaskResponse(TaskBase):
    """Schema for returning task data in responses"""
    id: str
    extracted_at: datetime
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class InteractionBase(BaseModel):
    person_name: str
    date: datetime
    sentiment_score: Optional[int] = None  # -100 to 100
    summary: Optional[str] = None
    source_file_path: str

class InteractionCreate(InteractionBase):
    """Schema for creating a new interaction"""
    pass

class InteractionUpdate(BaseModel):
    """Schema for updating an existing interaction"""
    person_name: Optional[str] = None
    sentiment_score: Optional[int] = None
    summary: Optional[str] = None

class InteractionResponse(InteractionBase):
    """Schema for returning interaction data in responses"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class DailyMetricBase(BaseModel):
    date: str  # YYYY-MM-DD format
    mood_score: Optional[int] = None  # -100 to 100
    tasks_completed: int = 0
    words_written: int = 0
    meetings_recorded: int = 0

class DailyMetricCreate(DailyMetricBase):
    """Schema for creating a new daily metric"""
    pass

class DailyMetricUpdate(BaseModel):
    """Schema for updating an existing daily metric"""
    mood_score: Optional[int] = None
    tasks_completed: Optional[int] = None
    words_written: Optional[int] = None
    meetings_recorded: Optional[int] = None

class DailyMetricResponse(DailyMetricBase):
    """Schema for returning daily metric data in responses"""
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ExtractedEntities(BaseModel):
    """Schema for extracted entities from a document"""
    tasks: List[TaskCreate] = []
    interactions: List[InteractionCreate] = []
    sentiment_score: Optional[int] = None
    people_mentioned: List[str] = [] 