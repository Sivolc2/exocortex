import os
from typing import Optional
from dotenv import load_dotenv
from openai import OpenAI
from pathlib import Path
from datetime import datetime
import yaml

# Load environment variables from the .env file in the backend directory
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEFAULT_MODEL_NAME = os.getenv("OPENROUTER_MODEL_NAME", "anthropic/claude-3.5-sonnet")

# These are optional but recommended for OpenRouter tracking
YOUR_SITE_URL = os.getenv("YOUR_SITE_URL", "http://localhost:5173") 
YOUR_APP_NAME = os.getenv("YOUR_APP_NAME", "AI-Friendly Repo Chat")

def load_config():
    """Load configuration from config.yaml"""
    try:
        # Get the project root directory (4 levels up from llm_interface.py)
        project_root = Path(__file__).parent.parent.parent.parent
        config_path = project_root / 'config.yaml'
        if config_path.exists():
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
    except Exception as e:
        print(f"Warning: Could not load config.yaml: {e}")
    return {}

# Load configuration once at module level
config = load_config()

def _get_current_datetime() -> str:
    """Get the current date and time formatted for system prompts"""
    return datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

if not OPENROUTER_API_KEY:
    print("Warning: OPENROUTER_API_KEY not found in .env file. LLM calls will fail.")

client = None
if OPENROUTER_API_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

async def ask_llm(prompt_text: str, system_message: str = "You are a helpful assistant.", model_override: Optional[str] = None) -> str:
    """
    Sends a prompt to the configured LLM via OpenRouter and returns the response.
    """
    if not client:
        return "Error: OpenRouter client not initialized. Is OPENROUTER_API_KEY set in repo_src/backend/.env?"
    
    model_to_use = model_override or DEFAULT_MODEL_NAME
    
    # Add current date/time to system message if not already present
    if "Current date and time:" not in system_message:
        current_datetime = _get_current_datetime()
        system_message = f"Current date and time: {current_datetime}\n\n{system_message}"
    
    # Determine max_tokens based on whether this is the chat_model (execution model)
    # Only apply the config max_tokens to the chat_model, not the selector_model
    config_chat_model = config.get('llm', {}).get('chat_model', '')
    max_tokens_to_use = 2048  # Default value
    
    # Apply config max_tokens only if this is the chat_model (execution model)
    if model_to_use == config_chat_model:
        config_max_tokens = config.get('llm', {}).get('max_tokens')
        if config_max_tokens:
            max_tokens_to_use = config_max_tokens
            print(f"Using config max_tokens={max_tokens_to_use} for chat model {model_to_use}")
    
    try:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt_text}
        ]
        
        response = client.chat.completions.create(
            model=model_to_use,
            messages=messages,
            temperature=0.2, # Lower temperature for more factual answers based on context
            max_tokens=max_tokens_to_use,
            extra_headers={ "HTTP-Referer": YOUR_SITE_URL, "X-Title": YOUR_APP_NAME }
        )
        
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error calling OpenRouter API with model {model_to_use}: {e}")
        return f"Error: Failed to get response from LLM. Details: {str(e)}" 