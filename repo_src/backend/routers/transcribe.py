from fastapi import APIRouter, UploadFile, File, HTTPException
import os
import shutil
from pathlib import Path

from ..transcription.interface import transcribe_audio_file
from ..transcription.logic import save_transcript

router = APIRouter(
    prefix="/api/transcribe",
    tags=["transcription"],
)

@router.post("/")
async def create_transcription(file: UploadFile = File(...)):
    """
    Receives an audio file, transcribes it, and saves the transcript.
    """
    if not file.content_type or not file.content_type.startswith("audio/"):
        raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")

    # Create a temporary directory to save the upload
    temp_dir = "temp_audio"
    os.makedirs(temp_dir, exist_ok=True)
    temp_file_path = os.path.join(temp_dir, file.filename or "audio.tmp")

    try:
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        transcript_text = await transcribe_audio_file(temp_file_path)

        if "Error:" in transcript_text or not transcript_text.strip():
             raise HTTPException(status_code=500, detail=f"Transcription failed: {transcript_text}")

        save_transcript(transcript_text)

        return {"status": "success", "transcript_preview": transcript_text[:100] + "..."}
    finally:
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path) 