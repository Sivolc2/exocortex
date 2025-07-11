from fastapi import APIRouter, HTTPException, status

from repo_src.backend.data.schemas import ChatRequest, ChatResponse
from repo_src.backend.llm_chat.chat_logic import process_chat_request

router = APIRouter(
    prefix="/api/chat",
    tags=["chat"],
)

@router.post("/", response_model=ChatResponse, status_code=status.HTTP_200_OK)
async def handle_chat_request(request: ChatRequest):
    """
    Receives a user prompt, gets a response from the LLM based on document context,
    and returns the response.
    """
    try:
        llm_response = await process_chat_request(request.prompt)
        return ChatResponse(response=llm_response)
    except Exception as e:
        print(f"Error processing chat request: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while processing your request.") 