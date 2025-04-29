from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, FileResponse
import logging
import os
from app.dto.tts import TTSRequest
from app.services import tts
from app.core.config import OUTPUT_DIR

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/text-to-speech")
async def text_to_speech(request: TTSRequest):
    """
    Convert text to speech using OpenAI TTS API
    """
    try:
        logger.info(f"Received TTS request with voice: {request.voice}, model: {request.model}")
        
        # Generate speech
        filename = await tts.generate_speech(request)
        logger.info(f"Generated speech file: {filename}")
        
        # Return the audio file
        file_path = os.path.join(OUTPUT_DIR, filename)
        logger.info(f"Returning file: {file_path}")
        
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            return JSONResponse(
                status_code=404,
                content={"error": f"Generated file not found: {filename}"}
            )
        
        return FileResponse(
            file_path,
            media_type=f"audio/{request.response_format}",
            filename=filename
        )
    except Exception as e:
        logger.error(f"Error in text_to_speech endpoint: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@router.get("/test")
async def test_endpoint():
    """Simple test endpoint to verify API is working"""
    return {"status": "ok", "message": "TTS API is running"} 