import os
import uuid
import aiofiles
import logging
import sys
from openai import AsyncOpenAI
from fastapi import HTTPException
from app.core.config import OUTPUT_DIR
from app.dto.tts import TTSRequest

logger = logging.getLogger(__name__)

# Check OpenAI API key
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.warning("OpenAI API key not found in environment variables")
else:
    # Hide most of the API key for security
    visible_part = api_key[:8] + "..." + api_key[-4:]
    logger.info(f"Found OpenAI API key: {visible_part}")

try:
    client = AsyncOpenAI(api_key=api_key)
    logger.info("Successfully initialized AsyncOpenAI client")
except Exception as e:
    logger.error(f"Failed to initialize AsyncOpenAI client: {str(e)}")
    raise

async def generate_speech(request: TTSRequest) -> str:
    """Generate speech from text using OpenAI TTS API"""
    try:
        logger.info(f"Generating speech for text: {request.text[:50]}...")
        logger.info(f"Parameters: voice={request.voice}, model={request.model}, format={request.response_format}")
        
        # Generate unique filename
        filename = f"{uuid.uuid4()}.{request.response_format}"
        output_path = os.path.join(OUTPUT_DIR, filename)
        logger.info(f"Output will be saved to: {output_path}")
        
        # Call OpenAI TTS API
        try:
            logger.info("Calling OpenAI TTS API...")
            response = await client.audio.speech.create(
                model=request.model,
                voice=request.voice,
                input=request.text,
                response_format=request.response_format
            )
            logger.info("Successfully received response from OpenAI TTS API")
        except Exception as e:
            logger.error(f"Error calling OpenAI TTS API: {str(e)}")
            raise Exception(f"OpenAI API error: {str(e)}")
        
        # Save the audio file asynchronously
        try:
            # In newer OpenAI versions, response is already bytes, no need to await .read()
            content = response.content
            content_length = len(content) if content else 0
            logger.info(f"Response content length: {content_length} bytes")
            
            if not content or content_length == 0:
                logger.error("Empty response from OpenAI")
                raise Exception("Empty response from OpenAI")
                
            async with aiofiles.open(output_path, 'wb') as f:
                await f.write(content)
            logger.info(f"Successfully wrote content to {output_path}")
            
            if not os.path.exists(output_path):
                logger.error(f"File does not exist after writing: {output_path}")
                raise Exception(f"Failed to save audio file: {output_path}")
                
            file_size = os.path.getsize(output_path)
            logger.info(f"File saved with size: {file_size} bytes")
            
            return filename
        except Exception as e:
            logger.error(f"Error saving audio file: {str(e)}")
            raise Exception(f"File saving error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to generate speech: {str(e)}")
        raise Exception(f"Failed to generate speech: {str(e)}") 