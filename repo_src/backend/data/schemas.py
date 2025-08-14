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

class ChatResponse(BaseModel):
    """Schema for a chat response sent to the frontend."""
    response: str
    selected_files: Optional[List[str]] = None
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