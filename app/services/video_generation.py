import json
import os
import asyncio
import uuid
import websockets
from datetime import datetime
from fastapi import HTTPException
from app.core.config import UPLOAD_DIR, OUTPUT_DIR, COMFYUI_WS_URL
from app.dto.video_generation import VideoGenerationRequest

async def upload_image(file_content: bytes, filename: str) -> str:
    """Upload image to server and return the file path"""
    file_extension = os.path.splitext(filename)[1]
    unique_filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    with open(file_path, "wb") as buffer:
        buffer.write(file_content)
    
    return file_path

async def get_workflow(image_path: str, request: VideoGenerationRequest) -> dict:
    """Generate workflow JSON based on request parameters"""
    with open("workflows/image-to-video_api.json", "r") as f:
        workflow = json.load(f)
    
    # Update workflow parameters
    workflow["6"]["inputs"]["text"] = request.positive_prompt
    workflow["7"]["inputs"]["text"] = request.negative_prompt
    workflow["50"]["inputs"].update({
        "width": request.width,
        "height": request.height,
        "length": request.length
    })
    workflow["3"]["inputs"].update({
        "seed": request.seed or int(datetime.now().timestamp()),
        "steps": request.steps,
        "cfg": request.cfg,
        "sampler_name": request.sampler_name,
        "scheduler": request.scheduler
    })
    workflow["54"]["inputs"]["frame_rate"] = request.frame_rate
    workflow["52"]["inputs"]["image"] = os.path.basename(image_path)
    
    return workflow

async def queue_prompt(workflow: dict) -> str:
    """Queue the prompt in ComfyUI app and return prompt_id"""
    try:
        client_id = str(uuid.uuid4())
        ws_url = f"{COMFYUI_WS_URL}?clientId={client_id}"
        
        async with websockets.connect(ws_url) as websocket:
            # Send prompt
            await websocket.send(json.dumps({
                "prompt": workflow,
                "client_id": client_id
            }))
            
            # Wait for response
            response = await websocket.recv()
            response_data = json.loads(response)
            
            if "prompt_id" not in response_data:
                raise HTTPException(status_code=500, detail="Failed to queue prompt")
                
            return response_data["prompt_id"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to ComfyUI app: {str(e)}")

async def wait_for_completion(prompt_id: str) -> str:
    """Wait for the prompt to complete and return the output file path"""
    try:
        client_id = str(uuid.uuid4())
        ws_url = f"{COMFYUI_WS_URL}?clientId={client_id}"
        
        async with websockets.connect(ws_url) as websocket:
            while True:
                # Send status request
                await websocket.send(json.dumps({
                    "prompt_id": prompt_id,
                    "client_id": client_id
                }))
                
                # Wait for response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                if "outputs" in response_data:
                    outputs = response_data["outputs"]
                    if outputs:
                        # Get the first output file
                        for node_id, node_output in outputs.items():
                            if "images" in node_output:
                                return node_output["images"][0]["filename"]
                
                await asyncio.sleep(1)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get prompt status: {str(e)}") 