"""
Image Processor for manga pages.
Handles loading, preprocessing, postprocessing, and saving.
"""
from pathlib import Path
from PIL import Image
import logging

logger = logging.getLogger(__name__)


def _round8(x: int) -> int:
    """Round down to nearest multiple of 8 (SD requirement)."""
    return max(8, x - (x % 8))


class ImageProcessor:
    """Handles image loading, preprocessing, and postprocessing for SD."""
    
    def load_image(self, path: Path):
        """
        Load image from path.
        
        Args:
            path: Path to image file
            
        Returns:
            PIL Image in RGB mode, or None on error
        """
        try:
            return Image.open(path).convert("RGB")
        except Exception as e:
            logger.error(f"Load failed {path}: {e}")
            return None

    def preprocess_for_sd(self, image: Image.Image, max_side: int = 1024):
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
            logger.debug(f"Resized from {orig_w}x{orig_h} to {new_w}x{new_h}")

        metadata = {
            "original_size": (orig_w, orig_h),
            "processed_size": (new_w, new_h),
        }
        return processed, metadata

    def postprocess_result(self, colored: Image.Image, metadata: dict, restore_original_size: bool = True):
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
            logger.debug(f"Restoring size to {orig_size}")
            return colored.resize(orig_size, Image.LANCZOS)
        return colored

    def composite_with_mask(self, colored: Image.Image, original: Image.Image, mask_l: Image.Image):
        """
        Composite colored image with original using mask.
        
        Args:
            colored: Colorized image
            original: Original grayscale image
            mask_l: Mask (L mode) - 255 = use original, 0 = use colored
            
        Returns:
            Composited image
        """
        # PIL.Image.composite: where mask is 255, use first image (original)
        return Image.composite(original, colored, mask_l)

    def save_image(self, image: Image.Image, output_path: Path):
        """
        Save image to disk.
        
        Args:
            image: Image to save
            output_path: Output file path
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        logger.info(f"Image saved: {output_path.name}")

    def create_comparison(self, original: Image.Image, colored: Image.Image, out_path: Path):
        """
        Create side-by-side comparison image.
        
        Args:
            original: Original image
            colored: Colorized image
            out_path: Output path for comparison
        """
        w1, h1 = original.size
        w2, h2 = colored.size
        out = Image.new("RGB", (w1 + w2, max(h1, h2)), (255, 255, 255))
        out.paste(original, (0, 0))
        out.paste(colored, (w1, 0))
        self.save_image(out, out_path)
        logger.info(f"Comparison saved: {out_path.name}")
