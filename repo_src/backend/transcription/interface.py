import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from the .env file in the backend directory
load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
# Using Whisper as a common, high-quality transcription model
TRANSCRIPTION_MODEL = os.getenv("OPENROUTER_TRANSCRIPTION_MODEL", "openai/whisper-1")

client = None
if OPENROUTER_API_KEY:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

async def transcribe_audio_file(file_path: str) -> str:
    """
    Sends an audio file to OpenRouter for transcription.
    """
    if not client:
        return "Error: OpenRouter client not initialized. Is OPENROUTER_API_KEY set?"
    
    try:
        with open(file_path, "rb") as audio_file:
            print(f"Transcribing {file_path} with model {TRANSCRIPTION_MODEL}...")
            transcription = client.audio.transcriptions.create(model=TRANSCRIPTION_MODEL, file=audio_file)
            return transcription.text
    except Exception as e:
        print(f"Error calling OpenRouter for transcription: {e}")
        return f"Error: Failed to get transcription. Details: {str(e)}" 