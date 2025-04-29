from pydantic import BaseModel
from typing import Literal

class TTSRequest(BaseModel):
    text: str
    voice: Literal["alloy", "echo", "fable", "onyx", "nova", "shimmer"] = "alloy"
    model: Literal["tts-1", "tts-1-hd"] = "tts-1"
    response_format: Literal["mp3", "opus", "aac", "flac"] = "mp3" 