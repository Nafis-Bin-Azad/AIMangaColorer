"""
Configuration constants for manga colorization
"""

# Engine selection
DEFAULT_ENGINE = "mcv2"  # "mcv2" (fast, default) or "sd15" (slow, fallback)

# Manga Colorization v2 parameters (FAST engine)
MCV2_PARAMS = {
    "preserve_ink": True,       # Overlay original black ink/text
    "ink_threshold": 80,        # Pixels darker than this = original ink (0-255)
    "size": 576,                # Processing size (must be divisible by 32)
    "denoise": True,            # Apply denoising
    "denoise_sigma": 25,        # Denoising strength
}

# SD1.5 parameters (FALLBACK engine - slow but flexible)
SD15_PARAMS = {
    "steps": 18,                            # Inference steps
    "guidance_scale": 7.5,                  # CFG scale
    "strength": 0.85,                       # Denoise strength (higher = more color)
    "controlnet_conditioning_scale": 0.8,   # ControlNet influence
    "max_side": 640,                        # Max image dimension
    "seed": 12345,                          # Fixed seed for reproducibility
}

# Legacy - kept for backwards compatibility
COLORIZATION_PARAMS = SD15_PARAMS

# Default prompts for SD1.5 engine
DEFAULT_PROMPT = (
    "full color anime manga page, vibrant colors, clean cel shading, "
    "consistent character colors, high quality coloring"
)

DEFAULT_NEGATIVE_PROMPT = (
    "grayscale, monochrome, black and white, "
    "text, letters, words, watermark, logo, signature, "
    "blurry, repainting lines, messy colors, color bleeding, "
    "artifacts, low quality, bad anatomy"
)

# Output directory
OUTPUT_DIR = "output"
