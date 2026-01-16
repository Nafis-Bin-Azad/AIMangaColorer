"""
Image Processing Utilities
Combines image preprocessing, lineart extraction, text detection, and ink preservation
"""
import logging
import numpy as np
from PIL import Image, ImageFilter
from pathlib import Path

logger = logging.getLogger(__name__)

# Import lineart detector if available
try:
    from controlnet_aux import LineartAnimeDetector
except Exception:
    LineartAnimeDetector = None


def _round8(x: int) -> int:
    """Round down to nearest multiple of 8 (SD requirement)."""
    return max(8, x - (x % 8))


class ImageUtils:
    """
    All-in-one image processing utilities for manga colorization.
    Handles preprocessing, lineart extraction, text detection, and ink preservation.
    """
    
    def __init__(self):
        """Initialize utils with lineart detector"""
        self.lineart_detector = None
        
        if LineartAnimeDetector is not None:
            try:
                self.lineart_detector = LineartAnimeDetector.from_pretrained("lllyasviel/Annotators")
                logger.info("LineartAnimeDetector loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load LineartAnimeDetector: {e}")
    
    def preprocess(self, image: Image.Image, max_side: int = 640):
        """
        Resize image for SD processing.
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
    
    def extract_lineart(self, image: Image.Image, enhance_lines: bool = True) -> Image.Image:
        """
        Extract lineart for ControlNet conditioning.
        
        Args:
            image: Input manga page (RGB)
            enhance_lines: Whether to enhance line detection
            
        Returns:
            Lineart image (RGB)
        """
        if self.lineart_detector is None:
            logger.info("Using fallback edge detection for lineart")
            return self._fallback_lineart(image)
        
        try:
            lineart = self.lineart_detector(image)
            if not isinstance(lineart, Image.Image):
                lineart = Image.fromarray(np.array(lineart))
            
            lineart = lineart.convert("RGB")
            
            if enhance_lines:
                lineart = lineart.filter(ImageFilter.EDGE_ENHANCE_MORE)
            
            logger.info("Extracted lineart using anime detector")
            return lineart
        except Exception as e:
            logger.error(f"Lineart detection failed: {e}, using fallback")
            return self._fallback_lineart(image)
    
    def _fallback_lineart(self, img: Image.Image) -> Image.Image:
        """Fallback edge detection using PIL filters."""
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edges = edges.filter(ImageFilter.EDGE_ENHANCE_MORE)
        return edges.convert("RGB")
    
    def detect_text_bubbles(
        self,
        image: Image.Image,
        white_thresh: int = 245,
        dark_thresh: int = 180,
        text_dilate: int = 31,
        bubble_dilate: int = 9,
        max_coverage: float = 0.35
    ) -> Image.Image | None:
        """
        Detect speech bubbles based on proximity to dark text.
        Returns mask or None if coverage is too high.
        
        Args:
            image: Input image (RGB)
            white_thresh: Threshold for white bubble candidates
            dark_thresh: Threshold for dark text/ink
            text_dilate: Expansion radius for text region detection
            bubble_dilate: Expansion radius for bubble mask
            max_coverage: Maximum allowed mask coverage (0-1)
            
        Returns:
            Mask image (L mode) or None if too aggressive
        """
        img_l = image.convert("L")
        arr = np.array(img_l)
        
        # White bubble candidates
        white = arr >= white_thresh
        
        # Text/ink candidates
        dark = arr <= dark_thresh
        
        # Expand dark pixels to capture bubble region around text
        dark_img = Image.fromarray((dark.astype("uint8") * 255), mode="L")
        dark_near = dark_img.filter(ImageFilter.MaxFilter(text_dilate))
        dark_near_arr = np.array(dark_near) > 0
        
        # Bubble mask = white pixels close to text
        mask_arr = (white & dark_near_arr).astype("uint8") * 255
        mask = Image.fromarray(mask_arr, mode="L")
        
        # Expand and soften edges
        mask = mask.filter(ImageFilter.MaxFilter(bubble_dilate))
        mask = mask.filter(ImageFilter.GaussianBlur(1.0))
        
        coverage = np.mean(np.array(mask) > 0)
        logger.info(f"Text mask coverage: {coverage:.3f}")
        
        if coverage > max_coverage:
            logger.warning(f"Text mask too large ({coverage:.2%}), skipping protection")
            return None
        
        return mask
    
    def preserve_ink(
        self,
        original: Image.Image,
        colored: Image.Image,
        ink_threshold: int = 110
    ) -> Image.Image:
        """
        Overlay original black ink (lineart + text) on top of the colored output.
        This prevents SD from destroying text, bubbles, and lineart.
        
        Args:
            original: Original grayscale manga page (RGB)
            colored: SD colorized output (RGB)
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
            colored: Colorized image from SD
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
