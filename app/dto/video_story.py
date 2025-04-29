from pydantic import BaseModel
from typing import Optional, List

class VideoStoryRequest(BaseModel):
    """Request model for generating a complete video story from text"""
    text: str
    voice: str = "nova"
    tts_model: str = "tts-1"
    image_prompt_count: int = 0  # If 0, will be calculated based on audio duration
    frame_rate: int = 8
    image_width: int = 848
    image_height: int = 480
    video_length: int = 81
    seed: Optional[int] = None
    steps: int = 20
    cfg: float = 6.0
    sampler_name: str = "uni_pc"
    scheduler: str = "simple"
    add_captions: bool = True
    language: str = "vietnamese"  # Language of the input text for caption generation

class ImagePrompt(BaseModel):
    """Model for an image prompt generated from the story"""
    prompt: str
    negative_prompt: str = "Overexposure, static, blurred details, subtitles, paintings, pictures, still, overall gray, worst quality, low quality, JPEG compression residue, ugly, mutilated, redundant fingers, poorly painted hands, poorly painted faces, deformed, disfigured, deformed limbs, fused fingers, cluttered background, three legs, a lot of people in the background, upside down"
    index: int
    
class VideoProcessingStatus(BaseModel):
    """Model for tracking video processing status"""
    id: str
    status: str  # "processing", "completed", "failed"
    progress: float  # 0-100
    message: str
    output_file: Optional[str] = None
    audio_duration: Optional[float] = None
    image_prompts: Optional[List[ImagePrompt]] = None 