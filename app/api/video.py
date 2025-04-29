from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from app.dto.video_generation import VideoGenerationRequest
from app.services import video_generation
from app.core.config import OUTPUT_DIR
import os

router = APIRouter()

@router.post("/generate-video")
async def generate_video(
    image: UploadFile = File(...),
    positive_prompt: str = Form(...),
    negative_prompt: str = Form(...),
    width: int = Form(848),
    height: int = Form(480),
    length: int = Form(81),
    frame_rate: int = Form(8),
    seed: int = Form(None),
    steps: int = Form(20),
    cfg: float = Form(6.0),
    sampler_name: str = Form("uni_pc"),
    scheduler: str = Form("simple")
):
    try:
        # Create request model
        request = VideoGenerationRequest(
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            length=length,
            frame_rate=frame_rate,
            seed=seed,
            steps=steps,
            cfg=cfg,
            sampler_name=sampler_name,
            scheduler=scheduler
        )
        
        # Upload image
        image_content = await image.read()
        image_path = await video_generation.upload_image(image_content, image.filename)
        
        # Generate workflow
        workflow = await video_generation.get_workflow(image_path, request)
        
        # Queue prompt
        prompt_id = await video_generation.queue_prompt(workflow)
        
        # Wait for completion
        output_file = await video_generation.wait_for_completion(prompt_id)
        
        # Return the generated video
        return FileResponse(
            os.path.join(OUTPUT_DIR, output_file),
            media_type="video/mp4",
            filename=output_file
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) 