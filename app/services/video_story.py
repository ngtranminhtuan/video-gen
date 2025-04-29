import os
import uuid
import asyncio
import json
import aiofiles
import math
import logging
import websockets
from datetime import datetime
from fastapi import HTTPException
from typing import List, Dict
import base64

from app.dto.video_story import VideoStoryRequest, VideoProcessingStatus, ImagePrompt
from app.services import tts
from app.utils import audio, ai
from app.utils.config import COMFYUI_CONFIG, PROMPT_CONFIG
from app.core.config import UPLOAD_DIR, OUTPUT_DIR

logger = logging.getLogger(__name__)

# Get WebSocket URL from config
COMFYUI_WS_URL = COMFYUI_CONFIG.get("connection", {}).get("ws_url", "ws://127.0.0.1:8188/ws")
WORKFLOW_FILE = COMFYUI_CONFIG.get("paths", {}).get("workflow_file", "workflows/image-to-video_api.json")

# In-memory storage for status tracking
processing_jobs: Dict[str, VideoProcessingStatus] = {}

async def generate_story_video(request: VideoStoryRequest) -> str:
    """Generate a complete video story from text"""
    # Create job ID and initialize status
    job_id = str(uuid.uuid4())
    status = VideoProcessingStatus(
        id=job_id,
        status="processing",
        progress=0,
        message="Initializing job"
    )
    processing_jobs[job_id] = status
    
    # Start processing in background task
    asyncio.create_task(process_video_job(job_id, request))
    
    return job_id

async def process_video_job(job_id: str, request: VideoStoryRequest):
    """Process video generation job"""
    status = processing_jobs[job_id]
    
    try:
        # Step 1: Generate audio from text
        status.message = "Generating audio from text"
        status.progress = 5
        logger.info(f"Job {job_id}: Generating audio")
        
        tts_request = tts.TTSRequest(
            text=request.text,
            voice=request.voice,
            model=request.tts_model,
            response_format="mp3"
        )
        
        audio_filename = await tts.generate_speech(tts_request)
        audio_path = os.path.join(OUTPUT_DIR, audio_filename)
        
        # Step 2: Get audio duration
        status.message = "Analyzing audio duration"
        status.progress = 15
        audio_duration = audio.get_audio_duration(audio_path)
        status.audio_duration = audio_duration
        logger.info(f"Job {job_id}: Audio duration is {audio_duration} seconds")
        
        # Step 3: Calculate number of images needed (5 seconds per image)
        if request.image_prompt_count <= 0:
            num_images = math.ceil(audio_duration / 5)
            logger.info(f"Job {job_id}: Calculated {num_images} images needed for {audio_duration} seconds")
        else:
            num_images = request.image_prompt_count
            logger.info(f"Job {job_id}: Using requested image count: {num_images}")
        
        # Step 4: Generate image prompts from text
        status.message = "Generating image prompts"
        status.progress = 25
        image_prompts = await ai.generate_image_prompts(request.text, num_images)
        status.image_prompts = image_prompts
        logger.info(f"Job {job_id}: Generated {len(image_prompts)} image prompts")
        
        # Log the first few prompts for debugging
        for i, prompt in enumerate(image_prompts[:3]):
            logger.info(f"Job {job_id}: Prompt {i}: {prompt.prompt[:100]}...")
        
        # Step 5: Generate images from prompts
        status.message = "Generating images"
        status.progress = 35
        image_paths = []
        
        for i, prompt in enumerate(image_prompts):
            try:
                logger.info(f"Job {job_id}: Generating image {i+1}/{len(image_prompts)}")
                
                # Update progress
                status.progress = 35 + (i / len(image_prompts) * 30)
                status.message = f"Generating image {i+1} of {len(image_prompts)}"
                
                # Generate image from DALL-E
                image_bytes = await ai.generate_image(prompt.prompt)
                
                # Save image
                image_filename = f"{job_id}_{i}.png"
                image_path = os.path.join(UPLOAD_DIR, image_filename)
                async with aiofiles.open(image_path, 'wb') as f:
                    await f.write(image_bytes)
                    
                image_paths.append(image_path)
                logger.info(f"Job {job_id}: Saved image to {image_path}")
                
            except Exception as e:
                logger.error(f"Job {job_id}: Error generating image {i}: {str(e)}")
                # Continue with other images even if one fails
        
        # Step 6: Generate videos from images
        status.message = "Generating videos from images"
        status.progress = 65
        video_paths = []
        
        for i, image_path in enumerate(image_paths):
            try:
                logger.info(f"Job {job_id}: Generating video {i+1}/{len(image_paths)}")
                
                # Update progress
                status.progress = 65 + (i / len(image_paths) * 20)
                status.message = f"Generating video {i+1} of {len(image_paths)}"
                
                # Get corresponding prompt
                prompt = image_prompts[i] if i < len(image_prompts) else None
                
                # Generate workflow for image
                workflow = await get_workflow(image_path, request, prompt)
                
                # Generate video
                video_filename = await generate_video_from_image(workflow)
                video_path = os.path.join(OUTPUT_DIR, video_filename)
                video_paths.append(video_path)
                logger.info(f"Job {job_id}: Generated video at {video_path}")
                
            except Exception as e:
                logger.error(f"Job {job_id}: Error generating video {i}: {str(e)}")
                # Continue with other videos even if one fails
        
        # Add the first video again if we need more to match audio duration
        if len(video_paths) > 0:
            # Each video is 5 seconds, calculate how many extra videos we need
            total_video_duration = len(video_paths) * 5
            if total_video_duration < audio_duration:
                extra_videos_needed = math.ceil((audio_duration - total_video_duration) / 5)
                for _ in range(extra_videos_needed):
                    video_paths.append(video_paths[0])  # Repeat the first video
                logger.info(f"Job {job_id}: Added {extra_videos_needed} extra video clips to match audio duration")
        
        # Step 7: Combine videos with audio
        status.message = "Combining videos with audio"
        status.progress = 85
        
        output_filename = f"{job_id}_final.mp4"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        combined_path = audio.combine_audio_video(audio_path, video_paths, output_path)
        logger.info(f"Job {job_id}: Combined video and audio at {combined_path}")
        
        # Step 8: Add captions if requested
        if request.add_captions:
            status.message = "Adding captions with speech alignment"
            status.progress = 95
            
            # Add captions to video with text-audio alignment
            captioned_filename = f"{job_id}_captioned.mp4"
            captioned_path = os.path.join(OUTPUT_DIR, captioned_filename)
            
            final_path = await audio.add_captions(combined_path, request.text, audio_path, captioned_path)
            logger.info(f"Job {job_id}: Added aligned captions, final video at {final_path}")
        else:
            final_path = combined_path
        
        # Step 9: Update status to completed
        status.status = "completed"
        status.progress = 100
        status.message = "Video generation completed"
        status.output_file = os.path.basename(final_path)
        logger.info(f"Job {job_id}: Completed successfully")
        
    except Exception as e:
        # Update status on failure
        status.status = "failed"
        status.message = f"Error: {str(e)}"
        logger.error(f"Job {job_id} failed: {str(e)}")

async def get_workflow(image_path: str, request: VideoStoryRequest, prompt: ImagePrompt = None) -> dict:
    """Generate workflow JSON for image-to-video conversion"""
    try:
        # Load workflow from file
        workflow_path = os.path.join(os.getcwd(), WORKFLOW_FILE)
        with open(workflow_path, "r") as f:
            workflow = json.load(f)
        
        # Get node IDs from config
        nodes = COMFYUI_CONFIG.get("workflow", {}).get("nodes", {})
        positive_prompt_node = nodes.get("positive_prompt", 6)
        negative_prompt_node = nodes.get("negative_prompt", 7)
        sampler_node = nodes.get("sampler", 3)
        video_settings_node = nodes.get("video_settings", 50)
        frame_rate_node = nodes.get("frame_rate", 54)
        image_loader_node = nodes.get("image_loader", 52)
        
        # Set prompts
        positive_text = prompt.prompt if prompt and prompt.prompt else "high quality, detailed, cinematic scene"
        negative_text = prompt.negative_prompt if prompt and prompt.negative_prompt else PROMPT_CONFIG.get("video_gen", {}).get("default_negative_prompt", "")
        
        workflow[str(positive_prompt_node)]["inputs"]["text"] = positive_text
        workflow[str(negative_prompt_node)]["inputs"]["text"] = negative_text
        
        # Set video parameters
        workflow[str(video_settings_node)]["inputs"].update({
            "width": request.image_width,
            "height": request.image_height,
            "length": request.video_length
        })
        
        # Set sampler parameters
        workflow[str(sampler_node)]["inputs"].update({
            "seed": request.seed or int(datetime.now().timestamp()),
            "steps": request.steps,
            "cfg": request.cfg,
            "sampler_name": request.sampler_name,
            "scheduler": request.scheduler
        })
        
        # Set frame rate
        workflow[str(frame_rate_node)]["inputs"]["frame_rate"] = request.frame_rate
        
        # Set input image
        workflow[str(image_loader_node)]["inputs"]["image"] = os.path.basename(image_path)
        
        return workflow
    except Exception as e:
        logger.error(f"Error generating workflow: {str(e)}")
        raise Exception(f"Failed to generate workflow: {str(e)}")

async def generate_video_from_image(workflow: dict) -> str:
    """Generate video from image using ComfyUI"""
    client_id = str(uuid.uuid4())
    client_param = COMFYUI_CONFIG.get("connection", {}).get("client_param", "clientId")
    poll_interval = COMFYUI_CONFIG.get("connection", {}).get("poll_interval", 1)
    timeout = COMFYUI_CONFIG.get("connection", {}).get("timeout", 300)
    
    ws_url = f"{COMFYUI_WS_URL}?{client_param}={client_id}"
    logger.info(f"Connecting to ComfyUI WebSocket at {ws_url}")
    
    start_time = datetime.now()
    
    try:
        async with websockets.connect(ws_url) as websocket:
            # Queue prompt
            await websocket.send(json.dumps({
                "prompt": workflow,
                "client_id": client_id
            }))
            
            # Get prompt ID
            response = await websocket.recv()
            data = json.loads(response)
            
            if "prompt_id" not in data:
                raise Exception("Failed to queue prompt")
                
            prompt_id = data["prompt_id"]
            logger.info(f"Queued prompt with ID: {prompt_id}")
            
            # Wait for completion
            while True:
                # Check for timeout
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    raise Exception(f"Timeout after {timeout} seconds waiting for workflow completion")
                
                # Send status request
                await websocket.send(json.dumps({
                    "prompt_id": prompt_id,
                    "client_id": client_id
                }))
                
                # Get status
                try:
                    response = await websocket.recv()
                    data = json.loads(response)
                except Exception as e:
                    logger.warning(f"Error receiving WebSocket response: {str(e)}")
                    await asyncio.sleep(poll_interval)
                    continue
                
                if "outputs" in data:
                    outputs = data["outputs"]
                    if outputs:
                        # Get the first output file
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                return node_output["images"][0]["filename"]
                
                await asyncio.sleep(poll_interval)
    except Exception as e:
        logger.error(f"Error generating video: {str(e)}")
        raise Exception(f"Failed to generate video: {str(e)}")

def get_job_status(job_id: str) -> VideoProcessingStatus:
    """Get the status of a video processing job"""
    if job_id not in processing_jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    
    return processing_jobs[job_id] 