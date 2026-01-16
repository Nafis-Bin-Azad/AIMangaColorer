"""
Manga Colorization v2 Engine
Fast non-diffusion manga colorizer with automatic weight download and ink preservation
"""
import torch
import gdown
from pathlib import Path
import sys
import logging
import numpy as np
from PIL import Image
import zipfile

logger = logging.getLogger(__name__)


class MangaColorizationV2Engine:
    """
    Fast non-diffusion manga colorizer that preserves text/lineart.
    Based on qweasdd/manga-colorization-v2
    """
    
    # Google Drive file IDs for model weights
    WEIGHTS_URLS = {
        "generator_extractor": "1qmxUEKADkEM4iYLp1fpPLLKnfZ6tcF-t",
        "denoiser": "161oyQcYpdkVdw8gKz_MA8RD-Wtg9XDp3"
    }
    
    def __init__(self):
        """Initialize the engine with device detection"""
        # Detect device
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        
        self.model = None
        self.weights_dir = Path(__file__).parent / "third_party" / "manga_colorization_v2"
        
        logger.info(f"MCV2 Engine initialized on device: {self.device}")
    
    def ensure_weights(self):
        """Download model weights from Google Drive if not present"""
        networks_dir = self.weights_dir / "networks"
        denoising_dir = self.weights_dir / "denoising" / "models"
        
        networks_dir.mkdir(parents=True, exist_ok=True)
        denoising_dir.mkdir(parents=True, exist_ok=True)
        
        # Check for required files
        gen_zip = networks_dir / "generator.zip"
        extractor_pth = networks_dir / "extractor.pth"
        denoiser_pth = denoising_dir / "denoiser.pth"
        
        # Download generator + extractor (combined in one zip)
        if not gen_zip.exists():
            logger.info("Downloading generator/extractor weights (~500MB)...")
            logger.info("This is a one-time download, please wait...")
            try:
                # Download directly as generator.zip (it's already in PyTorch zip format)
                gdown.download(
                    id=self.WEIGHTS_URLS["generator_extractor"],
                    output=str(gen_zip),
                    quiet=False
                )
                logger.info("Generator/extractor weights downloaded successfully")
            except Exception as e:
                logger.error(f"Failed to download generator/extractor: {e}")
                raise RuntimeError(f"Weight download failed: {e}")
        
        # Download denoiser
        if not denoiser_pth.exists():
            logger.info("Downloading denoiser weights (~100MB)...")
            try:
                gdown.download(
                    id=self.WEIGHTS_URLS["denoiser"],
                    output=str(denoiser_pth),
                    quiet=False
                )
                logger.info("Denoiser weights downloaded successfully")
            except Exception as e:
                logger.error(f"Failed to download denoiser: {e}")
                raise RuntimeError(f"Denoiser download failed: {e}")
        
        logger.info("All weights present")
    
    def load_model(self):
        """Load the colorization model"""
        if self.model is not None:
            logger.info("Model already loaded")
            return
        
        # Add vendored code directory to path (so imports like 'networks.models' work)
        mcv2_path = Path(__file__).parent / "third_party" / "manga_colorization_v2"
        if str(mcv2_path) not in sys.path:
            sys.path.insert(0, str(mcv2_path))
        
        logger.info("Loading MangaColorizator model...")
        
        try:
            # Import from vendored code
            from colorizator import MangaColorizator
            
            # IMPORTANT: The vendored code uses relative paths for denoiser models
            # We need to temporarily change to the mcv2 directory
            import os
            original_cwd = os.getcwd()
            os.chdir(str(mcv2_path))
            
            try:
                # Set paths relative to weights_dir (now we're in mcv2_path)
                generator_path = "networks/generator.zip"
                extractor_path = "networks/extractor.pth"  # Not used but required by API
                
                # Initialize model
                self.model = MangaColorizator(
                    device=self.device,
                    generator_path=generator_path,
                    extractor_path=extractor_path
                )
                
                logger.info("Model loaded successfully")
            finally:
                # Restore original working directory
                os.chdir(original_cwd)
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}", exc_info=True)
            raise RuntimeError(f"Model loading failed: {e}")
    
    def colorize(
        self,
        image_pil: Image.Image,
        preserve_ink: bool = True,
        ink_threshold: int = 80,
        size: int = 576,
        denoise: bool = True,
        denoise_sigma: int = 25
    ) -> Image.Image:
        """
        Colorize a manga page.
        
        Args:
            image_pil: PIL Image (RGB or L mode)
            preserve_ink: Whether to overlay original black ink/text
            ink_threshold: Pixels darker than this = original ink (0-255)
            size: Processing size (must be divisible by 32)
            denoise: Whether to apply denoising
            denoise_sigma: Denoising strength
            
        Returns:
            Colored PIL Image (RGB)
        """
        if self.model is None:
            raise RuntimeError("Model not loaded. Call load_model() first.")
        
        # Ensure size is divisible by 32
        if size % 32 != 0:
            size = (size // 32) * 32
            logger.warning(f"Size adjusted to {size} (must be divisible by 32)")
        
        # Convert to RGB if grayscale
        if image_pil.mode != "RGB":
            image_pil = image_pil.convert("RGB")
        
        # Store original for ink preservation
        original_pil = image_pil.copy()
        
        # Convert PIL to numpy for the model
        image_np = np.array(image_pil)
        
        # Set the image in the model
        self.model.set_image(
            image_np,
            size=size,
            apply_denoise=denoise,
            denoise_sigma=denoise_sigma
        )
        
        # Colorize (no hints = automatic colorization)
        colored_np = self.model.colorize()
        
        # Convert back to PIL
        colored_np = (colored_np * 255).astype(np.uint8)
        colored_pil = Image.fromarray(colored_np, mode='RGB')
        
        # Resize back to original size if different
        if colored_pil.size != original_pil.size:
            colored_pil = colored_pil.resize(original_pil.size, Image.LANCZOS)
        
        # Preserve original ink/text
        if preserve_ink:
            colored_pil = self._preserve_original_ink(
                original_pil,
                colored_pil,
                threshold=ink_threshold
            )
        
        return colored_pil
    
    def _preserve_original_ink(
        self,
        original: Image.Image,
        colored: Image.Image,
        threshold: int = 80
    ) -> Image.Image:
        """
        Overlay original black ink (lineart + text) on colored output.
        
        Args:
            original: Original grayscale/RGB manga page
            colored: Colorized output
            threshold: Pixels darker than this are considered ink (0-255)
            
        Returns:
            Colored image with original ink preserved
        """
        # Convert to grayscale to detect dark pixels
        gray = original.convert("L")
        gray_np = np.array(gray)
        
        # Create ink mask: True where pixels are darker than threshold
        ink_mask = gray_np < threshold
        
        # Convert images to numpy arrays
        original_np = np.array(original.convert("RGB"))
        colored_np = np.array(colored.convert("RGB"))
        
        # Apply mask: where ink_mask is True, use original pixels
        result_np = colored_np.copy()
        result_np[ink_mask] = original_np[ink_mask]
        
        # Convert back to PIL
        result = Image.fromarray(result_np, mode='RGB')
        
        logger.info("Preserved original ink and text")
        return result
