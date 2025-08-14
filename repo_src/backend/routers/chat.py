from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session

from repo_src.backend.data.schemas import ChatRequest, ChatResponse
# from repo_src.backend.llm_chat.chat_logic import process_chat_request # Old logic
from repo_src.backend.agents.file_selection_agent import run_agent
from repo_src.backend.database.connection import get_db

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def handle_chat_request(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Receives a user prompt, gets a response from the LLM based on document context,
    and returns the response.
    """
    try:
        # Use the new agent-based logic
        selected_files, response_text, total_tokens = await run_agent(
            db=db,
            user_prompt=request.prompt, 
            selection_model=request.selection_model, 
            execution_model=request.execution_model)
        return ChatResponse(response=response_text, selected_files=selected_files, total_tokens=total_tokens)
    except Exception as e:
        print(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request.") 