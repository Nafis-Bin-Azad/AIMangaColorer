"""
Configuration settings for Manga Colorizer.
Working SD+ControlNet version.
"""
from pathlib import Path

# Prompts
DEFAULT_PROMPT = (
    "full color manga page, anime style coloring, clean lineart preserved, "
    "soft cel shading, consistent colors, detailed lighting, high quality"
)

DEFAULT_NEGATIVE_PROMPT = (
    "blurry, repainting lines, messy colors, color bleeding, oversaturated, "
    "artifacts, low quality, bad anatomy"
)

# Colorization parameters
COLORIZATION_PARAMS = {
    "steps": 25,
    "guidance_scale": 7.0,
    "strength": 0.45,
    "controlnet_conditioning_scale": 1.0,
    "max_side": 1024,
    "seed": None,
}

# Paths
BASE_DIR = Path(__file__).parent.parent
MODELS_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "output"
TEMP_DIR = OUTPUT_DIR / "temp"

# Ensure directories exist
MODELS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# Text detection
TEXT_DETECTION_PARAMS = {
    "white_thresh": 245,
    "min_area": 100
}

# Supported formats
SUPPORTED_FORMATS = [".png", ".jpg", ".jpeg", ".webp", ".bmp"]

# Server configuration
FLASK_HOST = "127.0.0.1"
FLASK_PORT = 5000
FLASK_DEBUG = False

# Logging
LOG_LEVEL = "INFO"
