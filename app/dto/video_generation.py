from pydantic import BaseModel
from typing import Optional

class VideoGenerationRequest(BaseModel):
    positive_prompt: str
    negative_prompt: str
    width: int = 848
    height: int = 480
    length: int = 81
    frame_rate: int = 8
    seed: Optional[int] = None
    steps: int = 20
    cfg: float = 6.0
    sampler_name: str = "uni_pc"
    scheduler: str = "simple" 