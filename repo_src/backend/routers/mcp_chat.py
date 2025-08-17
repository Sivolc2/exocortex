"""
MCP-Powered Chat Router

This router provides chat functionality powered by Model Context Protocol,
allowing queries against the knowledge base without traditional file selection.
"""

from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from repo_src.backend.data.schemas import ChatRequest, ChatResponse, FileTokenInfo
from repo_src.backend.agents.mcp_chat_agent import run_mcp_agent
from repo_src.backend.database.connection import get_db

router = APIRouter(
    prefix="/api/mcp-chat",
    tags=["mcp-chat"],
)

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def handle_mcp_chat_request(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Handle chat requests using MCP server for knowledge base queries.
    
    This endpoint:
    1. Extracts search terms from the user query
    2. Searches the MCP knowledge base for relevant files
    3. Selects the most relevant files using LLM
    4. Loads file contents via MCP
    5. Generates a contextual response
    
    Args:
        request: Chat request containing user prompt and model preferences
        db: Database session (kept for compatibility)
        
    Returns:
        Chat response with MCP-sourced context and generated answer
    """
    try:
        # Use the MCP-powered agent
        selected_files, response_text, total_tokens, file_token_counts = await run_mcp_agent(
            db=db,
            user_prompt=request.prompt,
            search_model=request.selection_model,
            response_model=request.execution_model,
            max_files=5
        )
        
        # Convert file token counts to FileTokenInfo objects
        file_token_info = None
        if file_token_counts:
            file_token_info = [
                FileTokenInfo(file_path=file_path, token_count=token_count)
                for file_path, token_count in file_token_counts.items()
            ]
        
        return ChatResponse(
            response=response_text,
            selected_files=selected_files,
            file_token_info=file_token_info,
            total_tokens=total_tokens
        )
        
    except Exception as e:
        print(f"Error processing MCP chat request: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"An error occurred while processing your request: {str(e)}"
        )

@router.get("/status")
async def get_mcp_status():
    """
    Get status information about the MCP server connection.
    
    Returns:
        Status information including connectivity and knowledge base stats
    """
    try:
        from repo_src.backend.mcp_client import get_mcp_client
        
        mcp_client = get_mcp_client()
        stats = await mcp_client.get_knowledge_stats()
        
        return {
            "status": "connected",
            "mcp_server": "operational",
            "knowledge_base_stats": stats
        }
        
    except Exception as e:
        return {
            "status": "error",
            "mcp_server": "disconnected",
            "error": str(e)
        }

@router.get("/search/{query}")
async def search_knowledge_base(query: str, source: str = None, limit: int = 20):
    """
    Direct search endpoint for the knowledge base via MCP.
    
    Args:
        query: Search terms
        source: Optional source filter (notion, obsidian, discord)
        limit: Maximum results to return
        
    Returns:
        Search results from the knowledge base
    """
    try:
        from repo_src.backend.mcp_client import get_mcp_client
        
        mcp_client = get_mcp_client()
        search_results = await mcp_client.search_knowledge(query, source, limit)
        
        return {
            "query": query,
            "source_filter": source,
            "results": search_results.entries,
            "total_count": search_results.total_count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching knowledge base: {str(e)}"
        )