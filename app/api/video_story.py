from fastapi import APIRouter, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
import logging
import os
import json
from app.dto.video_story import VideoStoryRequest, VideoProcessingStatus
from app.services import video_story
from app.core.config import OUTPUT_DIR
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate-story-video")
async def generate_story_video(request: VideoStoryRequest):
    """
    Generate a complete video story from text
    """
    try:
        logger.info(f"Received request to generate story video: {request.text[:100]}...")
        
        # Start processing
        job_id = await video_story.generate_story_video(request)
        logger.info(f"Started video processing job: {job_id}")
        
        # Return job ID for status tracking
        return {
            "job_id": job_id,
            "message": "Video processing started. Use the job_id to check status."
        }
        
    except Exception as e:
        logger.error(f"Error starting video generation: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@router.get("/story-video-status/{job_id}")
async def get_story_video_status(job_id: str):
    """
    Get the status of a video processing job
    """
    try:
        status = video_story.get_job_status(job_id)
        
        response = {
            "job_id": status.id,
            "status": status.status,
            "progress": status.progress,
            "message": status.message
        }
        
        if status.output_file:
            response["output_file"] = status.output_file
            
        if status.audio_duration:
            response["audio_duration"] = status.audio_duration
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting job status: {str(e)}")
        return JSONResponse(
            status_code=404,
            content={"error": str(e)}
        )

@router.get("/story-video/{job_id}")
async def get_story_video(job_id: str):
    """
    Get the generated video for a job
    """
    try:
        status = video_story.get_job_status(job_id)
        
        if status.status != "completed":
            return JSONResponse(
                status_code=400,
                content={"error": "Video processing is not completed", "status": status.status}
            )
            
        if not status.output_file:
            return JSONResponse(
                status_code=404,
                content={"error": "Output file not found"}
            )
            
        file_path = os.path.join(OUTPUT_DIR, status.output_file)
        
        if not os.path.exists(file_path):
            return JSONResponse(
                status_code=404,
                content={"error": "Video file not found"}
            )
            
        return FileResponse(
            file_path,
            media_type="video/mp4",
            filename=status.output_file
        )
        
    except Exception as e:
        logger.error(f"Error getting video file: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@router.websocket("/story-video-ws/{job_id}")
async def websocket_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for real-time status updates
    """
    await websocket.accept()
    try:
        while True:
            try:
                status = video_story.get_job_status(job_id)
                await websocket.send_json({
                    "job_id": status.id,
                    "status": status.status,
                    "progress": status.progress,
                    "message": status.message,
                    "output_file": status.output_file,
                    "audio_duration": status.audio_duration
                })
                
                # If processing is complete or failed, stop sending updates
                if status.status in ["completed", "failed"]:
                    await asyncio.sleep(5)  # Send one more update after completion
                    break
                    
            except Exception as e:
                await websocket.send_json({"error": str(e)})
                break
                
            await asyncio.sleep(2)  # Send status update every 2 seconds
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for job_id: {job_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close() 