"""
ControlNet Processor for manga lineart extraction.
Uses LineartAnimeDetector with fallback to edge detection.
"""
import numpy as np
from PIL import Image, ImageFilter
import logging

logger = logging.getLogger(__name__)

try:
    from controlnet_aux import LineartAnimeDetector
except Exception:
    LineartAnimeDetector = None


class ControlNetProcessor:
    """
    Produces a ControlNet conditioning image (lineart) from the input page.
    """
    
    def __init__(self, use_anime_model: bool = True):
        self.use_anime_model = use_anime_model
        self.detector = None

        if LineartAnimeDetector is not None:
            try:
                # Uses HF annotators - downloads once
                self.detector = LineartAnimeDetector.from_pretrained("lllyasviel/Annotators")
                logger.info("LineartAnimeDetector loaded successfully")
            except Exception as e:
                logger.warning(f"Failed to load LineartAnimeDetector: {e}")
                self.detector = None

    def _fallback_lineart(self, img: Image.Image) -> Image.Image:
        """Fallback edge detection using PIL filters."""
        gray = img.convert("L")
        edges = gray.filter(ImageFilter.FIND_EDGES)
        edges = edges.filter(ImageFilter.EDGE_ENHANCE_MORE)
        return edges.convert("RGB")

    def process_for_controlnet(self, image: Image.Image, enhance_lines: bool = True):
        """
        Extract lineart for ControlNet conditioning.
        
        Args:
            image: Input manga page
            enhance_lines: Whether to enhance line detection
            
        Returns:
            Tuple of (debug_image, lineart_image)
        """
        if self.detector is None:
            logger.info("Using fallback edge detection")
            return None, self._fallback_lineart(image)

        try:
            lineart = self.detector(image)
            if not isinstance(lineart, Image.Image):
                lineart = Image.fromarray(np.array(lineart))

            lineart = lineart.convert("RGB")

            if enhance_lines:
                # Strengthen lines slightly
                lineart = lineart.filter(ImageFilter.EDGE_ENHANCE_MORE)

            return None, lineart
        except Exception as e:
            logger.error(f"Lineart detection failed: {e}, using fallback")
            return None, self._fallback_lineart(image)
