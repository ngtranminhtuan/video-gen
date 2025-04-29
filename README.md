# Video Story Generator API

A backend API for generating complete videos from text, including automatically generated audio and images.

## Key Features

- Convert text to speech using OpenAI TTS API
- Analyze text content and generate appropriate image prompts
- Create high-quality images from prompts using DALL-E
- Convert images to video using ComfyUI
- Combine videos and audio using FFmpeg
- Generate automatic captions from text content
- Track progress in real-time via WebSocket

## Setup

### Requirements

- Python 3.8+
- ComfyUI running on the same machine (default at `http://localhost:8188`)
- OpenAI API key
- FFmpeg (installed on your system)

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

1. Create a `.env.local` file in the root directory:
```
OPENAI_API_KEY=your_openai_api_key
COMFYUI_API_URL=http://localhost:8188
```

2. Make sure required directories exist:
```bash
mkdir -p uploads outputs workflows
```

3. Place the ComfyUI workflow file in the workflows directory:
```bash
# Example, if you have the workflow file
cp path/to/image-to-video_api.json workflows/
```

## Project Structure

```
video-gen/
├── app/                  # Main source code
│   ├── api/              # API endpoints
│   ├── core/             # Core configuration
│   ├── dto/              # Data Transfer Objects
│   ├── services/         # Business logic
│   └── utils/            # Utilities
├── data/                 # YAML configurations
│   ├── prompt_configs.yaml    # Prompt configurations
│   └── comfyui_configs.yaml   # ComfyUI configurations
├── uploads/              # Image storage
├── outputs/              # Video output
├── workflows/            # ComfyUI workflows
├── .env.local            # Local environment variables
└── requirements.txt      # Python dependencies
```

## Starting the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

## Using the API

### Generate Video from Text

**Endpoint:** `POST /api/v1/generate-story-video`

**Body:**
```json
{
  "text": "Have you ever wondered how someone's gaze can change your entire life? An emotionless look sometimes has more power than words.",
  "voice": "alloy",
  "tts_model": "tts-1",
  "image_prompt_count": 0,  
  "frame_rate": 8,
  "image_width": 848,
  "image_height": 480,
  "video_length": 81,
  "add_captions": true,
  "language": "english"
}
```

> Note: If `image_prompt_count` is 0, the number of images will be calculated based on audio duration (5 seconds/image)

**Response:**
```json
{
  "job_id": "8f7d5b1c-3c3d-4e6a-9f5a-b7f3e5a9d7c3",
  "message": "Video processing started. Use the job_id to check status."
}
```

### Check Status

**Endpoint:** `GET /api/v1/story-video-status/{job_id}`

**Response:**
```json
{
  "job_id": "8f7d5b1c-3c3d-4e6a-9f5a-b7f3e5a9d7c3",
  "status": "processing",
  "progress": 45.5,
  "message": "Generating image 3 of 18"
}
```

### Download Video

**Endpoint:** `GET /api/v1/story-video/{job_id}`

Returns the MP4 video file (only when processing is complete).

### Track Progress in Real-time

**WebSocket:** `ws://localhost:8000/api/v1/story-video-ws/{job_id}`

## Troubleshooting

### Workflow File Not Found

Make sure the workflow file is in the correct location:
```bash
cp path/to/image-to-video_api.json workflows/
```

### Cannot Connect to ComfyUI

Check:
- ComfyUI is running (default at `http://localhost:8188`)
- URL in `.env.local` and `comfyui_configs.yaml` is correct

### Cannot Generate Video

Check:
- FFmpeg is installed on your system
- The uploads and outputs directories exist and have write permissions

## Video Generation Process

1. Generate audio from text using OpenAI TTS
2. Analyze audio duration to calculate needed images
3. Generate image prompts from text using OpenAI
4. Create images from prompts using DALL-E
5. Convert images to video using ComfyUI (5s per video)
6. Combine video clips together
7. Add audio to video
8. Add captions if requested

## Expanding

The project is designed to be easily expandable:
- Add other TTS models besides OpenAI
- Add other image generation models besides DALL-E
- Customize ComfyUI workflow for different video effects
- Add advanced video editing capabilities