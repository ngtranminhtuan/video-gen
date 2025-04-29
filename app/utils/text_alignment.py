import os
import logging
import json
import subprocess
import tempfile
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

class TextSegment:
    """Represents a segment of text with timing information"""
    def __init__(self, text: str, start: float, end: float):
        self.text = text
        self.start = start
        self.end = end
    
    def to_srt_format(self, index: int) -> str:
        """Convert to SRT format"""
        return f"{index}\n{format_time_srt(self.start)} --> {format_time_srt(self.end)}\n{self.text}\n\n"
    
    def __repr__(self):
        return f"<TextSegment '{self.text}' ({self.start:.2f} - {self.end:.2f})>"

def format_time_srt(seconds: float) -> str:
    """Format time in SRT format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"

def split_text_into_sentences(text: str) -> List[str]:
    """Split text into sentences for alignment"""
    import re
    # Split on sentence endings (.!?) followed by space or end of string
    sentences = re.split(r'([.!?])\s+|([.!?])$', text)
    # Clean up and combine the sentences
    result = []
    buffer = ""
    for item in sentences:
        if item in ['.', '!', '?', None]:
            if buffer:
                buffer += item if item else '.'
                result.append(buffer.strip())
                buffer = ""
        else:
            buffer += item
    
    # Add any remaining text
    if buffer:
        result.append(buffer.strip())
    
    return [s for s in result if s.strip()]

async def align_text_with_audio(text: str, audio_path: str) -> List[TextSegment]:
    """Align text with audio file using available tools"""
    try:
        # First try whisperx if available (simpler installation)
        try:
            return await align_with_whisperx(audio_path, text)
        except ImportError:
            logger.info("WhisperX not available, trying aeneas...")
        
        # Try aeneas if available
        try:
            return align_with_aeneas(audio_path, text)
        except (ImportError, subprocess.CalledProcessError):
            logger.info("Aeneas not available or failed, using fallback method...")
        
        # Fallback to duration-based alignment
        return fallback_alignment(text, audio_path)
    except Exception as e:
        logger.error(f"Error in text alignment: {str(e)}")
        return fallback_alignment(text, audio_path)

async def align_with_whisperx(audio_path: str, text: str) -> List[TextSegment]:
    """Align text using WhisperX (GPU recommended)"""
    try:
        import whisperx
        import torch
        
        # Load ASR model
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = whisperx.load_model("base", device)
        
        # Transcribe audio
        result = model.transcribe(audio_path)
        
        # Load alignment model
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device=device)
        
        # Align whisper output
        result = whisperx.align(result["segments"], model_a, metadata, audio_path, device)
        
        # Get aligned segments
        segments = []
        for segment in result["segments"]:
            segments.append(TextSegment(
                text=segment["text"],
                start=segment["start"],
                end=segment["end"]
            ))
        
        if not segments:
            raise ValueError("No segments returned from WhisperX")
            
        return segments
    except Exception as e:
        logger.error(f"WhisperX alignment error: {str(e)}")
        raise ImportError("WhisperX alignment failed")

def align_with_aeneas(audio_path: str, text: str) -> List[TextSegment]:
    """Align text with audio using aeneas"""
    try:
        from aeneas.executetask import ExecuteTask
        from aeneas.task import Task
        
        # Create temporary text file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as temp_text:
            temp_text.write(text)
            text_file = temp_text.name
        
        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as temp_output:
            output_file = temp_output.name
        
        # Configure the alignment task
        config_string = "task_language=vie|is_text_type=plain|os_task_file_format=json"
        task = Task(config_string=config_string)
        task.audio_file_path_absolute = audio_path
        task.text_file_path_absolute = text_file
        task.sync_map_file_path_absolute = output_file
        
        # Execute the task and get alignment
        ExecuteTask(task).execute()
        task.output_sync_map_file()
        
        # Read the output file
        with open(output_file, "r") as f:
            alignment = json.load(f)
        
        # Parse the results
        segments = []
        for fragment in alignment["fragments"]:
            segments.append(TextSegment(
                text=fragment["lines"][0],
                start=float(fragment["begin"]),
                end=float(fragment["end"])
            ))
        
        # Clean up temporary files
        os.unlink(text_file)
        os.unlink(output_file)
        
        return segments
    except Exception as e:
        logger.error(f"Aeneas alignment error: {str(e)}")
        raise ImportError("Aeneas alignment failed")

def fallback_alignment(text: str, audio_path: str) -> List[TextSegment]:
    """Fallback method: divide text by characters and distribute over audio duration"""
    try:
        logger.info("Using fallback text alignment method")
        
        # Get audio duration
        import subprocess
        cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            audio_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        audio_duration = float(result.stdout.strip())
        
        # Split text into sentences
        sentences = split_text_into_sentences(text)
        
        # Calculate character count
        total_chars = sum(len(s) for s in sentences)
        chars_per_second = total_chars / audio_duration if total_chars > 0 else 1
        
        # Create segments
        segments = []
        current_time = 0
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            # Calculate duration based on character count
            segment_duration = len(sentence) / chars_per_second
            
            # Add some minimum duration
            segment_duration = max(segment_duration, 1.5)
            
            # Create segment
            segments.append(TextSegment(
                text=sentence,
                start=current_time,
                end=current_time + segment_duration
            ))
            
            # Update time
            current_time += segment_duration
        
        # Scale to match audio duration if needed
        if segments and segments[-1].end > audio_duration:
            scale_factor = audio_duration / segments[-1].end
            for segment in segments:
                segment.start *= scale_factor
                segment.end *= scale_factor
        
        return segments
    except Exception as e:
        logger.error(f"Fallback alignment error: {str(e)}")
        # Return very basic segmentation
        return [TextSegment(text=text, start=0, end=30)]

def generate_srt_file(segments: List[TextSegment], output_path: str) -> str:
    """Generate SRT file from aligned segments"""
    srt_content = ""
    
    for i, segment in enumerate(segments, 1):
        srt_content += segment.to_srt_format(i)
    
    # Write to file
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)
    
    return output_path 