"""
Batch Processor for Manga Colorization
Handles zip extraction, natural sorting, and progress tracking
"""
import zipfile
import tempfile
import shutil
from pathlib import Path
from natsort import natsorted
import time
import logging
from PIL import Image
from config import MCV2_PARAMS, SD15_PARAMS, DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Process multiple manga images from files, zips, or folders"""
    
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    
    def __init__(self, engine, image_utils, engine_type='mcv2', progress_callback=None):
        """
        Initialize batch processor.
        
        Args:
            engine: MCV2Engine or SD15Pipeline instance
            image_utils: ImageUtils instance
            engine_type: 'mcv2' or 'sd15'
            progress_callback: function(stage, current, total, eta, thumbnail)
        """
        self.engine = engine
        self.image_utils = image_utils
        self.engine_type = engine_type
        self.progress_callback = progress_callback
        self.should_cancel = False
        self.start_time = None
        self.temp_dirs = []  # Track temp directories for cleanup
        
    def process_batch(self, input_items, output_path, output_format='auto'):
        """
        Process multiple inputs (files, zips, folders).
        
        Args:
            input_items: List of (type, path) tuples
                        type: 'file', 'zip', 'folder'
            output_path: Path to output folder or zip
            output_format: 'folder', 'zip', or 'auto'
            
        Returns:
            Number of successfully processed images
        """
        try:
            # Collect all images from all sources
            all_images = []
            
            for item_type, item_path in input_items:
                if item_type == 'file':
                    all_images.append(item_path)
                elif item_type == 'zip':
                    all_images.extend(self._extract_zip(item_path))
                elif item_type == 'folder':
                    all_images.extend(self._collect_from_folder(item_path))
            
            if not all_images:
                logger.warning("No images found in input items")
                return 0
            
            # Natural sort by filename (handles 1, 2, 10 correctly)
            all_images = natsorted(all_images, key=lambda p: p.name)
            
            logger.info(f"Found {len(all_images)} images to process")
            
            # Determine output format
            if output_format == 'auto':
                # Use zip if any input was a zip
                has_zip = any(item_type == 'zip' for item_type, _ in input_items)
                output_format = 'zip' if has_zip else 'folder'
            
            # Process all images
            results = []
            self.start_time = time.time()
            
            for idx, img_path in enumerate(all_images):
                if self.should_cancel:
                    logger.info("Batch processing cancelled by user")
                    break
                    
                # Calculate ETA
                if idx > 0:
                    elapsed = time.time() - self.start_time
                    avg_time = elapsed / idx
                    remaining = (len(all_images) - idx) * avg_time
                else:
                    remaining = 0
                
                # Load thumbnail for preview
                thumbnail = self._create_thumbnail(img_path)
                
                # Progress callback
                if self.progress_callback:
                    self.progress_callback(
                        stage=f"Processing {img_path.name}",
                        current=idx + 1,
                        total=len(all_images),
                        eta=remaining,
                        thumbnail=thumbnail
                    )
                
                # Colorize
                try:
                    colored = self._colorize_single(img_path)
                    results.append((img_path.stem, colored))
                except Exception as e:
                    logger.error(f"Failed to colorize {img_path.name}: {e}")
                    continue
            
            # Save results
            output_path = Path(output_path)
            if output_format == 'zip':
                self._create_output_zip(results, output_path)
            else:
                self._save_to_folder(results, output_path)
            
            logger.info(f"Batch processing complete: {len(results)} images saved")
            return len(results)
            
        finally:
            # Cleanup temp directories
            self._cleanup_temp_dirs()
    
    def _extract_zip(self, zip_path):
        """Extract zip file to temp directory and return image paths"""
        temp_dir = Path(tempfile.mkdtemp(prefix='manga_batch_'))
        self.temp_dirs.append(temp_dir)
        
        logger.info(f"Extracting {zip_path.name} to {temp_dir}")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Collect all images from extracted content
        return self._collect_from_folder(temp_dir)
    
    def _collect_from_folder(self, folder_path):
        """Recursively collect all image files from folder"""
        folder_path = Path(folder_path)
        images = []
        
        for ext in self.SUPPORTED_EXTENSIONS:
            images.extend(folder_path.rglob(f'*{ext}'))
        
        logger.info(f"Found {len(images)} images in {folder_path.name}")
        return images
    
    def _create_thumbnail(self, img_path, size=(150, 150)):
        """Create thumbnail for preview"""
        try:
            img = Image.open(img_path)
            img.thumbnail(size, Image.LANCZOS)
            return img
        except Exception as e:
            logger.error(f"Failed to create thumbnail for {img_path.name}: {e}")
            return None
    
    def _colorize_single(self, img_path):
        """Colorize a single image"""
        # Load image
        img = Image.open(img_path).convert("RGB")
        
        # Preprocess
        if self.engine_type == 'mcv2':
            processed, metadata = self.image_utils.preprocess(img, max_side=1024)
            
            # Colorize with MCV2
            colored = self.engine.colorize(
                processed,
                preserve_ink=MCV2_PARAMS["preserve_ink"],
                ink_threshold=MCV2_PARAMS["ink_threshold"],
                size=MCV2_PARAMS["size"],
                denoise=MCV2_PARAMS["denoise"],
                denoise_sigma=MCV2_PARAMS["denoise_sigma"]
            )
        else:
            # SD15 engine
            processed, metadata = self.image_utils.preprocess(
                img,
                max_side=SD15_PARAMS["max_side"]
            )
            
            # Extract lineart
            lineart = self.image_utils.extract_lineart(processed)
            if lineart.size != processed.size:
                lineart = lineart.resize(processed.size, Image.LANCZOS)
            
            # Detect text
            text_mask = self.image_utils.detect_text_bubbles(processed)
            
            # Colorize
            colored = self.engine.colorize(
                image=processed,
                control_image=lineart,
                mask=text_mask,
                prompt=DEFAULT_PROMPT,
                negative_prompt=DEFAULT_NEGATIVE_PROMPT,
                **SD15_PARAMS
            )
            
            # Preserve ink
            colored = self.image_utils.preserve_ink(processed, colored, ink_threshold=110)
        
        # Postprocess
        final = self.image_utils.postprocess(colored, metadata, restore_original_size=True)
        
        return final
    
    def _create_output_zip(self, results, output_path):
        """Create zip file with colored images"""
        output_path = Path(output_path)
        if not output_path.suffix:
            output_path = output_path.with_suffix('.zip')
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Creating output zip: {output_path}")
        
        with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for name, image in results:
                # Save to temp file then add to zip
                temp_img_path = Path(tempfile.gettempdir()) / f"{name}_colored.png"
                image.save(temp_img_path, "PNG")
                zipf.write(temp_img_path, f"{name}_colored.png")
                temp_img_path.unlink()  # Remove temp file
        
        logger.info(f"Saved {len(results)} images to {output_path}")
    
    def _save_to_folder(self, results, output_path):
        """Save colored images to folder"""
        output_path = Path(output_path)
        output_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Saving to folder: {output_path}")
        
        for name, image in results:
            output_file = output_path / f"{name}_colored.png"
            image.save(output_file, "PNG")
        
        logger.info(f"Saved {len(results)} images to {output_path}")
    
    def _has_zip_input(self, input_items):
        """Check if any input is a zip file"""
        return any(item_type == 'zip' for item_type, _ in input_items)
    
    def _cleanup_temp_dirs(self):
        """Clean up temporary directories"""
        for temp_dir in self.temp_dirs:
            try:
                shutil.rmtree(temp_dir)
                logger.debug(f"Cleaned up temp dir: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {temp_dir}: {e}")
        self.temp_dirs.clear()
    
    def cancel(self):
        """Cancel the batch processing"""
        self.should_cancel = True
        logger.info("Batch processing cancellation requested")
