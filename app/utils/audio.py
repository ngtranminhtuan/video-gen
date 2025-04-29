import subprocess
import os
import logging
from typing import Tuple, List
from app.utils.text_alignment import align_text_with_audio, generate_srt_file, TextSegment, fallback_alignment

logger = logging.getLogger(__name__)

def get_audio_duration(file_path: str) -> float:
    """Get duration of an audio file in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe', 
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip())
        logger.info(f"Audio duration: {duration} seconds")
        
        return duration
    except Exception as e:
        logger.error(f"Error getting audio duration: {str(e)}")
        raise Exception(f"Failed to get audio duration: {str(e)}")

def combine_audio_video(audio_path: str, video_paths: list, output_path: str) -> str:
    """Combine audio and multiple video segments into a single video file"""
    try:
        # Create temporary file list
        temp_file_list = os.path.join(os.path.dirname(output_path), "filelist.txt")
        with open(temp_file_list, "w") as f:
            for video_path in video_paths:
                f.write(f"file '{video_path}'\n")
        
        # Concatenate videos
        concat_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-f', 'concat',
            '-safe', '0',
            '-i', temp_file_list,
            '-c', 'copy',
            os.path.join(os.path.dirname(output_path), "temp_concat.mp4")
        ]
        
        logger.info(f"Concatenating videos with command: {' '.join(concat_cmd)}")
        subprocess.run(concat_cmd, check=True)
        
        # Add audio
        audio_cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', os.path.join(os.path.dirname(output_path), "temp_concat.mp4"),
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac',
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest',
            output_path
        ]
        
        logger.info(f"Adding audio with command: {' '.join(audio_cmd)}")
        subprocess.run(audio_cmd, check=True)
        
        # Clean up temporary files
        if os.path.exists(temp_file_list):
            os.remove(temp_file_list)
        if os.path.exists(os.path.join(os.path.dirname(output_path), "temp_concat.mp4")):
            os.remove(os.path.join(os.path.dirname(output_path), "temp_concat.mp4"))
        
        return output_path
    except Exception as e:
        logger.error(f"Error combining audio and video: {str(e)}")
        raise Exception(f"Failed to combine audio and video: {str(e)}")

async def add_captions(video_path: str, text: str, audio_path: str, output_path: str) -> str:
    """Add captions to video using FFmpeg with text-audio alignment"""
    try:
        logger.info(f"Adding captions to video: {video_path}")
        
        # Align text with audio to get accurate timings
        logger.info("Aligning text with audio...")
        try:
            segments = await align_text_with_audio(text, audio_path)
            logger.info(f"Successfully aligned {len(segments)} text segments with audio")
        except Exception as e:
            logger.warning(f"Advanced alignment failed: {str(e)}, falling back to basic method")
            segments = fallback_alignment(text, audio_path)
        
        # Create SRT file
        subtitle_path = os.path.join(os.path.dirname(output_path), "subtitles.srt")
        generate_srt_file(segments, subtitle_path)
        logger.info(f"Generated subtitle file: {subtitle_path}")
        
        # Add subtitles to video
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output file if it exists
            '-i', video_path,
            '-vf', f"subtitles={subtitle_path}:force_style='Fontname=Arial,FontSize=24,PrimaryColour=&H00FFFFFF,BackColour=&H80000000,BorderStyle=4,Alignment=2'",
            '-c:a', 'copy',
            output_path
        ]
        
        logger.info(f"Adding captions with command: {' '.join(cmd)}")
        subprocess.run(cmd, check=True)
        
        # Clean up
        if os.path.exists(subtitle_path):
            os.remove(subtitle_path)
        
        return output_path
    except Exception as e:
        logger.error(f"Error adding captions: {str(e)}")
        raise Exception(f"Failed to add captions: {str(e)}")

def generate_srt_from_text(text: str, duration: float) -> str:
    """
    Generate SRT format captions from text (legacy method)
    Simple implementation: split text into roughly equal segments based on duration
    """
    lines = text.split('.')
    lines = [line.strip() + '.' for line in lines if line.strip()]
    
    total_chars = sum(len(line) for line in lines)
    chars_per_second = total_chars / duration
    
    srt_content = ""
    current_index = 1
    start_time = 0
    
    buffer = ""
    buffer_chars = 0
    
    for line in lines:
        if buffer_chars + len(line) < chars_per_second * 5:  # Try to keep segments ~5 seconds
            buffer += " " + line if buffer else line
            buffer_chars += len(line)
        else:
            # Calculate timing for this segment
            segment_duration = buffer_chars / chars_per_second
            end_time = start_time + segment_duration
            
            # Format times as SRT requires (HH:MM:SS,mmm)
            start_formatted = format_srt_time(start_time)
            end_formatted = format_srt_time(end_time)
            
            # Add entry
            srt_content += f"{current_index}\n{start_formatted} --> {end_formatted}\n{buffer}\n\n"
            
            # Reset for next segment
            current_index += 1
            start_time = end_time
            buffer = line
            buffer_chars = len(line)
    
    # Add the last segment if there's anything left
    if buffer:
        segment_duration = buffer_chars / chars_per_second
        end_time = start_time + segment_duration
        
        start_formatted = format_srt_time(start_time)
        end_formatted = format_srt_time(end_time)
        
        srt_content += f"{current_index}\n{start_formatted} --> {end_formatted}\n{buffer}\n\n"
    
    return srt_content

def format_srt_time(seconds: float) -> str:
    """Format seconds as HH:MM:SS,mmm for SRT files"""
    hours = int(seconds // 3600)
    seconds %= 3600
    minutes = int(seconds // 60)
    seconds %= 60
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}" 