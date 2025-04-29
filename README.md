# Video Generation API

A FastAPI-based backend service for generating videos from images using ComfyUI's image-to-video workflow.

## Features

- Convert images to videos using AI
- Customizable video generation parameters
- RESTful API interface
- Asynchronous processing
- File upload and download support

## Prerequisites

- Python 3.8+
- ComfyUI running on localhost:8188
- Required Python packages (see requirements.txt)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/video-gen.git
cd video-gen
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
video-gen/
├── app/
│   ├── api/            # API endpoints
│   ├── core/           # Core configuration
│   ├── dto/            # Data transfer objects
│   ├── services/       # Business logic
│   └── utils/          # Utility functions
├── workflows/          # ComfyUI workflow templates
├── uploads/           # Temporary image storage
└── outputs/           # Generated video storage
```

## Usage

1. Start ComfyUI:
```bash
# Make sure ComfyUI is running on http://localhost:8188
```

2. Start the API server:
```bash
python -m app.main
```

3. Access the API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API Endpoints

### Generate Video
```
POST /api/v1/generate-video
```

**Parameters:**
- `image`: Image file (required)
- `positive_prompt`: Text prompt for desired video content (required)
- `negative_prompt`: Text prompt for undesired elements (required)
- `width`: Video width (default: 848)
- `height`: Video height (default: 480)
- `length`: Video length in frames (default: 81)
- `frame_rate`: Frames per second (default: 8)
- `seed`: Random seed for generation (optional)
- `steps`: Number of diffusion steps (default: 20)
- `cfg`: Classifier-free guidance scale (default: 6.0)
- `sampler_name`: Sampler name (default: "uni_pc")
- `scheduler`: Scheduler name (default: "simple")

**Response:**
- Returns the generated video file

## Development

### Adding New Features

1. Create new DTO models in `app/dto/`
2. Add business logic in `app/services/`
3. Create API endpoints in `app/api/`
4. Update configuration in `app/core/` if needed

### Testing

```bash
# Run tests (when implemented)
pytest
```

## License

MIT License

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request