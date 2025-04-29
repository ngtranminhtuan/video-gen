import os
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

def load_yaml_config(filename):
    """Load a YAML configuration file"""
    try:
        config_path = os.path.join(os.getcwd(), 'data', filename)
        logger.info(f"Loading config from {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        return config
    except Exception as e:
        logger.error(f"Error loading config file {filename}: {str(e)}")
        raise Exception(f"Failed to load configuration file {filename}: {str(e)}")

# Load configurations once at import time
try:
    PROMPT_CONFIG = load_yaml_config('prompt_configs.yaml')
    COMFYUI_CONFIG = load_yaml_config('comfyui_configs.yaml')
    
    logger.info("Configurations loaded successfully")
except Exception as e:
    logger.error(f"Failed to load configurations: {str(e)}")
    # Create default configurations
    PROMPT_CONFIG = {}
    COMFYUI_CONFIG = {} 