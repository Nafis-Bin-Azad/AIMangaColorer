"""
Configuration constants for manga colorization
"""

# Manga Colorization v2 parameters
MCV2_PARAMS = {
    "preserve_ink": True,       # Overlay original black ink/text
    "ink_threshold": 80,        # Pixels darker than this = original ink (0-255)
    "size": 576,                # Processing size (must be divisible by 32)
    "denoise": True,            # Apply denoising
    "denoise_sigma": 25,        # Denoising strength
}

# Output directory
OUTPUT_DIR = "output"
