"""
Image Processing Utilities
Handles preprocessing, ink preservation, and postprocessing for manga colorization
"""
import logging
import numpy as np
from PIL import Image
from pathlib import Path

logger = logging.getLogger(__name__)


def _round8(x: int) -> int:
    """Round down to nearest multiple of 8 for compatibility."""
    return max(8, x - (x % 8))


class ImageUtils:
    """
    Image processing utilities for manga colorization.
    Handles preprocessing, ink preservation, and postprocessing.
    """
    
    def __init__(self):
        """Initialize image utilities"""
        pass
    
    def preprocess(self, image: Image.Image, max_side: int = 1024):
        """
        Resize image for processing.
        Ensures dimensions are multiples of 8 and <= max_side.
        
        Args:
            image: Input image
            max_side: Maximum dimension size
            
        Returns:
            Tuple of (processed_image, metadata)
        """
        orig_w, orig_h = image.size
        
        # Scale to fit max_side
        scale = min(max_side / max(orig_w, orig_h), 1.0)
        new_w = _round8(int(orig_w * scale))
        new_h = _round8(int(orig_h * scale))
        
        processed = image
        if (new_w, new_h) != (orig_w, orig_h):
            processed = image.resize((new_w, new_h), Image.LANCZOS)
            logger.info(f"Resized from {orig_w}x{orig_h} to {new_w}x{new_h}")
        
        # Ensure RGB mode
        processed = processed.convert("RGB")
        
        metadata = {
            "original_size": (orig_w, orig_h),
            "processed_size": (new_w, new_h),
        }
        return processed, metadata
    
    def preserve_ink(
        self,
        original: Image.Image,
        colored: Image.Image,
        ink_threshold: int = 110
    ) -> Image.Image:
        """
        Overlay original black ink (lineart + text) on top of the colored output.
        This preserves text, bubbles, and lineart.
        
        Args:
            original: Original grayscale manga page (RGB)
            colored: Colorized output (RGB)
            ink_threshold: Luminance threshold (pixels darker than this = ink)
            
        Returns:
            Colored image with original ink/text preserved
        """
        if original.size != colored.size:
            original = original.resize(colored.size, Image.LANCZOS)
        
        orig_l = original.convert("L")
        colored_rgb = colored.convert("RGB")
        
        # Create ink mask: pixels darker than threshold
        ink = (np.array(orig_l) < ink_threshold).astype("uint8") * 255
        ink_mask = Image.fromarray(ink, mode="L")
        
        # Composite: where mask is 255 (ink), use original; else use colored
        result = Image.composite(original.convert("RGB"), colored_rgb, ink_mask)
        logger.info("Preserved original ink and text")
        return result
    
    def postprocess(
        self,
        colored: Image.Image,
        metadata: dict,
        restore_original_size: bool = True
    ) -> Image.Image:
        """
        Postprocess colorized image.
        
        Args:
            colored: Colorized image
            metadata: Metadata from preprocessing
            restore_original_size: Whether to restore original dimensions
            
        Returns:
            Final processed image
        """
        if not restore_original_size:
            return colored
        
        orig_size = metadata.get("original_size")
        if orig_size and colored.size != orig_size:
            logger.info(f"Restoring original size: {orig_size}")
            return colored.resize(orig_size, Image.LANCZOS)
        
        return colored
