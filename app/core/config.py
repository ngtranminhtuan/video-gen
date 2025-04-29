import os
import logging
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

# Load environment variables from .env.local file
env_file = '.env.local'
if os.path.exists(env_file):
    load_dotenv(env_file)
    logger.info(f"Loaded environment from {env_file}")
else:
    logger.warning(f"Environment file {env_file} not found, using default values")

# ComfyUI Configuration
COMFYUI_WS_URL = "ws://127.0.0.1:8188/ws"  # WebSocket URL for direct app connection
COMFYUI_API_URL = os.getenv("COMFYUI_API_URL", "http://localhost:8188")

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)
logger.info(f"Created directories: {UPLOAD_DIR}, {OUTPUT_DIR}") 