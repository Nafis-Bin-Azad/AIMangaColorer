"""
Main Manga Colorizer - Stable Diffusion + ControlNet implementation.
Mac M2 Pro / MPS ready with color consistency tracking.
"""
import logging
from pathlib import Path
from typing import Optional, Callable, Union

from PIL import Image

from .model_manager import ModelManager
from .pipeline import ColorizationPipeline
from .controlnet_processor import ControlNetProcessor
from .text_detector import TextDetector
from .image_processor import ImageProcessor
from .batch_processor import BatchProcessor
from .color_consistency import ColorConsistencyTracker
from .config import (
    DEFAULT_PROMPT,
    DEFAULT_NEGATIVE_PROMPT,
    COLORIZATION_PARAMS,
    OUTPUT_DIR
)

logger = logging.getLogger(__name__)


class MangaColorizer:
    """
    Stable Diffusion + ControlNet manga colorizer (Mac M2 Pro / MPS ready).
    """

    def __init__(
        self,
        model_name: str = "sd15",  # "sd15" or "sdxl"
        enable_text_detection: bool = True,
        output_dir: Union[str, Path] = OUTPUT_DIR
    ):
        self.model_name = model_name
        self.enable_text_detection = enable_text_detection
        self.output_dir = Path(output_dir)

        logger.info("Initializing Manga Colorizer (working SD+ControlNet version)")
        self.model_manager = ModelManager()
        self.pipeline = ColorizationPipeline(self.model_manager)
        self.controlnet_processor = ControlNetProcessor(use_anime_model=True)
        self.text_detector = TextDetector() if enable_text_detection else None
        self.image_processor = ImageProcessor()
        self.batch_processor = BatchProcessor(output_dir=self.output_dir)

        self.prompt = DEFAULT_PROMPT
        self.negative_prompt = DEFAULT_NEGATIVE_PROMPT
        self.colorization_params = COLORIZATION_PARAMS.copy()

        logger.info("Manga Colorizer initialized ✅")

    def initialize_model(self, model_name: Optional[str] = None) -> None:
        """
        Initialize the SD+ControlNet pipeline.
        
        Args:
            model_name: Optional model name override ("sd15" or "sdxl")
        """
        if model_name:
            self.model_name = model_name

        logger.info(f"Initializing pipeline model: {self.model_name}")
        self.pipeline.initialize_pipeline(self.model_name)
        logger.info("Pipeline initialized successfully ✅")

    def set_prompt(self, prompt: str, negative_prompt: Optional[str] = None) -> None:
        """
        Set custom prompts.
        
        Args:
            prompt: Main prompt
            negative_prompt: Optional negative prompt
        """
        self.prompt = prompt
        if negative_prompt is not None:
            self.negative_prompt = negative_prompt
        logger.info("Prompts updated")

    def set_params(self, **kwargs) -> None:
        """
        Update colorization parameters.
        
        Args:
            **kwargs: Parameter key-value pairs
        """
        self.colorization_params.update(kwargs)
        logger.info(f"Parameters updated: {kwargs}")

    def colorize_single_image(
        self,
        image_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        save_comparison: bool = False,
        progress_callback: Optional[Callable] = None,
        color_tracker: Optional[ColorConsistencyTracker] = None
    ) -> dict:
        """
        Colorize a single manga page.
        
        Args:
            image_path: Path to input image
            output_path: Optional output path
            save_comparison: Whether to save side-by-side comparison
            progress_callback: Optional progress callback
            color_tracker: Optional color consistency tracker for batch processing
            
        Returns:
            Dictionary with result information
        """
        try:
            image_path = Path(image_path)
            logger.info(f"Colorizing: {image_path.name}")

            # Ensure model ready
            if self.pipeline.pipeline is None:
                self.initialize_model()

            original_image = self.image_processor.load_image(image_path)
            if original_image is None:
                return {"success": False, "error": "Failed to load image"}

            processed_image, metadata = self.image_processor.preprocess_for_sd(
                original_image,
                max_side=self.colorization_params.get("max_side", 1024)
            )

            # Extract ControlNet lineart
            _, lineart = self.controlnet_processor.process_for_controlnet(
                processed_image,
                enhance_lines=True
            )
            
            # Ensure lineart matches processed_image dimensions exactly
            if lineart.size != processed_image.size:
                lineart = lineart.resize(processed_image.size, Image.LANCZOS)

            # Text protection
            text_mask = None
            boxes = []
            if self.text_detector:
                text_mask, boxes = self.text_detector.detect_and_mask(processed_image)
                logger.info(f"Text protection active")

            # Build prompt with color consistency if available
            current_prompt = self.prompt
            if color_tracker:
                color_guidance = color_tracker.get_color_guidance_prompt()
                if color_guidance:
                    current_prompt = self.prompt + color_guidance
                    logger.info(f"Using color guidance: {color_guidance}")

            # Colorize with SD+ControlNet
            colored_image = self.pipeline.colorize(
                image=processed_image,
                control_image=lineart,
                mask=text_mask,
                prompt=current_prompt,
                negative_prompt=self.negative_prompt,
                progress_callback=progress_callback,
                steps=self.colorization_params.get("steps", 25),
                guidance_scale=self.colorization_params.get("guidance_scale", 7.0),
                strength=self.colorization_params.get("strength", 0.45),
                controlnet_conditioning_scale=self.colorization_params.get("controlnet_conditioning_scale", 1.0),
                seed=self.colorization_params.get("seed", None),
            )

            final_image = self.image_processor.postprocess_result(
                colored_image,
                metadata,
                restore_original_size=True
            )

            # Update color tracker if provided
            if color_tracker:
                color_tracker.update_from_result(final_image)

            if output_path is None:
                output_filename = image_path.stem + "_colored.png"
                output_path = self.output_dir / output_filename
            else:
                output_path = Path(output_path)

            self.image_processor.save_image(final_image, output_path)

            result = {
                "success": True,
                "input_path": str(image_path),
                "output_path": str(output_path),
                "output_filename": output_path.name,
                "text_regions_protected": len(boxes) if boxes else 0,
            }

            if save_comparison:
                comparison_path = output_path.parent / (output_path.stem + "_comparison.png")
                self.image_processor.create_comparison(original_image, final_image, comparison_path)
                result["comparison_path"] = str(comparison_path)

            logger.info(f"Colorization complete: {output_path.name}")
            return result

        except Exception as e:
            logger.error(f"Failed to colorize image: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def colorize_batch(
        self,
        input_path: Union[str, Path],
        create_zip: bool = False,
        enable_color_consistency: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """
        Colorize multiple images from directory or ZIP.
        
        Args:
            input_path: Path to directory or ZIP file
            create_zip: Whether to create output ZIP
            enable_color_consistency: Whether to maintain color consistency across pages
            progress_callback: Optional callback(current, total, filename)
            
        Returns:
            Dictionary with batch results
        """
        try:
            input_path = Path(input_path)
            logger.info(f"Starting batch colorization: {input_path}")

            # Ensure model is initialized
            if self.pipeline.pipeline is None:
                self.initialize_model()

            # Initialize color tracker for batch consistency
            color_tracker = ColorConsistencyTracker() if enable_color_consistency else None

            def process_single_page(page_path: Path) -> Optional[Image.Image]:
                """Process a single page and return the colored image."""
                try:
                    original = self.image_processor.load_image(page_path)
                    if original is None:
                        return None

                    processed, metadata = self.image_processor.preprocess_for_sd(
                        original,
                        max_side=self.colorization_params.get("max_side", 1024)
                    )

                    _, lineart = self.controlnet_processor.process_for_controlnet(processed, enhance_lines=True)
                    
                    # Ensure lineart matches processed dimensions exactly
                    if lineart.size != processed.size:
                        lineart = lineart.resize(processed.size, Image.LANCZOS)

                    text_mask = None
                    if self.text_detector:
                        text_mask, _ = self.text_detector.detect_and_mask(processed)

                    # Build prompt with color consistency
                    current_prompt = self.prompt
                    if color_tracker:
                        color_guidance = color_tracker.get_color_guidance_prompt()
                        if color_guidance:
                            current_prompt = self.prompt + color_guidance

                    colored = self.pipeline.colorize(
                        image=processed,
                        control_image=lineart,
                        mask=text_mask,
                        prompt=current_prompt,
                        negative_prompt=self.negative_prompt,
                        steps=self.colorization_params.get("steps", 25),
                        guidance_scale=self.colorization_params.get("guidance_scale", 7.0),
                        strength=self.colorization_params.get("strength", 0.45),
                        controlnet_conditioning_scale=self.colorization_params.get("controlnet_conditioning_scale", 1.0),
                        seed=self.colorization_params.get("seed", None),
                    )

                    final = self.image_processor.postprocess_result(colored, metadata, restore_original_size=True)

                    # Update color tracker
                    if color_tracker:
                        color_tracker.update_from_result(final)

                    return final

                except Exception as e:
                    logger.error(f"Failed to process {page_path.name}: {e}")
                    return None

            # Process batch
            results = self.batch_processor.process_batch(
                input_path=input_path,
                process_func=process_single_page,
                create_zip=create_zip,
                progress_callback=progress_callback
            )

            logger.info(f"Batch colorization complete: {results.get('total_processed', 0)} images")
            return results

        except Exception as e:
            logger.error(f"Batch colorization failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "total_processed": 0,
                "output_files": []
            }

    def unload(self) -> None:
        """Unload the colorizer and free memory."""
        logger.info("Unloading colorizer")
        if self.pipeline:
            self.pipeline.unload()
        logger.info("Colorizer unloaded")

    def get_model_info(self) -> dict:
        """Get current model and configuration information."""
        info = {
            "model_name": self.model_name,
            "text_detection_enabled": self.enable_text_detection,
            "prompt": self.prompt,
            "negative_prompt": self.negative_prompt,
            "parameters": self.colorization_params,
            "output_dir": str(self.output_dir),
        }
        info.update(self.model_manager.get_model_info())
        return info

    def list_available_models(self) -> list:
        """List available model options."""
        return ["sd15", "sdxl"]
