"""
Color Consistency Tracker for batch processing.
Maintains similar color schemes across multiple manga pages.
"""
import numpy as np
from PIL import Image
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class ColorConsistencyTracker:
    """
    Tracks dominant colors from previous pages to maintain consistency.
    Modifies prompts to encourage similar color schemes.
    """
    
    def __init__(self):
        self.color_history = []
        self.max_history = 5  # Track last 5 pages
        
    def extract_dominant_colors(self, image: Image.Image, k: int = 3) -> list:
        """
        Extract k dominant colors using percentile-based sampling.
        
        Args:
            image: Colorized image
            k: Number of colors to extract (not used directly)
            
        Returns:
            List of RGB color tuples
        """
        img_array = np.array(image.convert("RGB"))
        pixels = img_array.reshape(-1, 3)
        
        # Filter out pure white/black (likely backgrounds/lines)
        mask = (pixels.min(axis=1) > 20) & (pixels.max(axis=1) < 235)
        filtered = pixels[mask]
        
        if len(filtered) < 100:
            return []
        
        # Get percentiles as representative colors
        percentiles = [25, 50, 75]
        colors = [filtered[int(len(filtered) * p / 100)] for p in percentiles]
        
        return colors
    
    def update_from_result(self, colored_image: Image.Image):
        """
        Update color history from a colorized result.
        
        Args:
            colored_image: Newly colorized page
        """
        colors = self.extract_dominant_colors(colored_image)
        if colors:
            self.color_history.append(colors)
            if len(self.color_history) > self.max_history:
                self.color_history.pop(0)
            logger.info(f"Updated color history (tracking {len(self.color_history)} pages)")
    
    def get_color_guidance_prompt(self) -> Optional[str]:
        """
        Generate prompt addition based on color history.
        
        Returns:
            String to append to prompt, or None if no history
        """
        if not self.color_history:
            return None
        
        # Average recent colors
        all_colors = [c for page_colors in self.color_history for c in page_colors]
        if not all_colors:
            return None
        
        avg_color = np.mean(all_colors, axis=0).astype(int)
        r, g, b = avg_color
        
        # Describe color palette based on average
        if r > 140 and g < 100 and b < 100:
            palette = "warm red and orange tones"
        elif b > 140 and r < 100 and g < 100:
            palette = "cool blue tones"
        elif r > 120 and g > 120 and b < 80:
            palette = "warm yellow and beige tones"
        elif r > 100 and g < 80 and b > 100:
            palette = "purple and magenta tones"
        else:
            palette = "consistent balanced colors"
        
        return f", maintaining {palette} from previous pages"
    
    def reset(self):
        """Clear color history (e.g., for new chapter)."""
        self.color_history.clear()
        logger.info("Color consistency history reset")
