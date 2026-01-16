"""
Batch Processor for handling ZIP files and multiple manga pages.
"""
import logging
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, Callable, Union

from PIL import Image

from .config import OUTPUT_DIR, TEMP_DIR, SUPPORTED_FORMATS

logger = logging.getLogger(__name__)


class BatchProcessor:
    """
    Handles batch processing of manga pages from ZIP files or directories.
    """
    
    def __init__(self, output_dir: Path = OUTPUT_DIR):
        """
        Initialize batch processor.
        
        Args:
            output_dir: Directory for output files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True, parents=True)
        self.temp_dir = None
    
    def is_zip_file(self, file_path: Union[str, Path]) -> bool:
        """
        Check if file is a ZIP archive.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if ZIP file
        """
        return Path(file_path).suffix.lower() == '.zip'
    
    def is_image_file(self, file_path: Union[str, Path]) -> bool:
        """
        Check if file is a supported image format.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if supported image
        """
        return Path(file_path).suffix.lower() in SUPPORTED_FORMATS
    
    def extract_zip(self, zip_path: Union[str, Path]) -> Path:
        """
        Extract ZIP file to temporary directory.
        
        Args:
            zip_path: Path to ZIP file
            
        Returns:
            Path to extraction directory
        """
        try:
            zip_path = Path(zip_path)
            logger.info(f"Extracting ZIP: {zip_path.name}")
            
            # Create temp directory
            self.temp_dir = Path(tempfile.mkdtemp(dir=TEMP_DIR))
            
            # Extract ZIP
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(self.temp_dir)
            
            logger.info(f"Extracted to: {self.temp_dir}")
            return self.temp_dir
            
        except Exception as e:
            logger.error(f"Failed to extract ZIP: {e}")
            raise
    
    def find_images_in_directory(self, directory: Union[str, Path]) -> List[Path]:
        """
        Recursively find all image files in directory.
        
        Args:
            directory: Directory to search
            
        Returns:
            List of image file paths (sorted)
        """
        directory = Path(directory)
        images = []
        
        for ext in SUPPORTED_FORMATS:
            images.extend(directory.rglob(f"*{ext}"))
            images.extend(directory.rglob(f"*{ext.upper()}"))
        
        # Sort by name for consistent ordering
        images = sorted(set(images), key=lambda p: p.name.lower())
        
        logger.info(f"Found {len(images)} images in {directory}")
        return images
    
    def get_input_files(self, input_path: Union[str, Path]) -> List[Path]:
        """
        Get list of input files from path (handles ZIP, directory, or single file).
        
        Args:
            input_path: Path to ZIP, directory, or image file
            
        Returns:
            List of image file paths
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input path not found: {input_path}")
        
        # Handle ZIP file
        if self.is_zip_file(input_path):
            extract_dir = self.extract_zip(input_path)
            return self.find_images_in_directory(extract_dir)
        
        # Handle directory
        elif input_path.is_dir():
            return self.find_images_in_directory(input_path)
        
        # Handle single file
        elif self.is_image_file(input_path):
            return [input_path]
        
        else:
            raise ValueError(f"Unsupported input type: {input_path}")
    
    def process_batch(
        self,
        input_files: List[Path],
        process_func: Callable[[Path], Optional[Image.Image]],
        output_subdir: Optional[str] = None,
        preserve_filenames: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> List[Path]:
        """
        Process a batch of image files.
        
        Args:
            input_files: List of input image paths
            process_func: Function that processes a single image (Path) -> PIL.Image
            output_subdir: Optional subdirectory within output_dir
            preserve_filenames: Whether to preserve original filenames
            progress_callback: Optional callback(current, total, filename)
            
        Returns:
            List of output file paths
        """
        if not input_files:
            logger.warning("No input files to process")
            return []
        
        # Setup output directory
        if output_subdir:
            output_path = self.output_dir / output_subdir
        else:
            output_path = self.output_dir
        output_path.mkdir(exist_ok=True, parents=True)
        
        total = len(input_files)
        output_files = []
        
        logger.info(f"Starting batch processing: {total} files")
        
        for i, input_file in enumerate(input_files, 1):
            try:
                logger.info(f"Processing {i}/{total}: {input_file.name}")
                
                # Call progress callback
                if progress_callback:
                    progress_callback(i, total, input_file.name)
                
                # Process the image
                result_image = process_func(input_file)
                
                if result_image is None:
                    logger.warning(f"Processing returned None for {input_file.name}")
                    continue
                
                # Determine output filename
                if preserve_filenames:
                    output_filename = input_file.stem + "_colored" + input_file.suffix
                else:
                    output_filename = f"output_{i:04d}.png"
                
                output_file = output_path / output_filename
                
                # Save result
                result_image.save(output_file)
                output_files.append(output_file)
                
                logger.info(f"Saved: {output_file.name}")
                
            except Exception as e:
                logger.error(f"Failed to process {input_file.name}: {e}")
                continue
        
        logger.info(f"Batch processing complete: {len(output_files)}/{total} successful")
        return output_files
    
    def create_output_zip(
        self,
        output_files: List[Path],
        zip_name: str = "colored_pages.zip"
    ) -> Path:
        """
        Create ZIP archive of output files.
        
        Args:
            output_files: List of file paths to include
            zip_name: Name of output ZIP file
            
        Returns:
            Path to created ZIP file
        """
        try:
            zip_path = self.output_dir / zip_name
            
            logger.info(f"Creating ZIP: {zip_path.name}")
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zip_ref:
                for file_path in output_files:
                    zip_ref.write(file_path, arcname=file_path.name)
            
            logger.info(f"ZIP created: {zip_path}")
            return zip_path
            
        except Exception as e:
            logger.error(f"Failed to create ZIP: {e}")
            raise
    
    def cleanup_temp(self) -> None:
        """Clean up temporary files and directories."""
        try:
            if self.temp_dir and self.temp_dir.exists():
                logger.info(f"Cleaning up temp directory: {self.temp_dir}")
                shutil.rmtree(self.temp_dir)
                self.temp_dir = None
                logger.info("Cleanup complete")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
    
    def process_from_path(
        self,
        input_path: Union[str, Path],
        process_func: Callable[[Path], Optional[Image.Image]],
        output_subdir: Optional[str] = None,
        create_zip: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> dict:
        """
        Complete processing pipeline from input path to output.
        
        Args:
            input_path: Path to ZIP, directory, or image file
            process_func: Function to process each image
            output_subdir: Optional output subdirectory
            create_zip: Whether to create output ZIP
            progress_callback: Optional progress callback
            
        Returns:
            Dictionary with results information
        """
        try:
            # Get input files
            input_files = self.get_input_files(input_path)
            
            if not input_files:
                return {
                    'success': False,
                    'error': 'No valid images found',
                    'input_count': 0,
                    'output_count': 0
                }
            
            # Process batch
            output_files = self.process_batch(
                input_files=input_files,
                process_func=process_func,
                output_subdir=output_subdir,
                progress_callback=progress_callback
            )
            
            result = {
                'success': True,
                'input_count': len(input_files),
                'output_count': len(output_files),
                'output_files': [str(f) for f in output_files],
                'output_dir': str(self.output_dir if not output_subdir else self.output_dir / output_subdir)
            }
            
            # Create ZIP if requested
            if create_zip and output_files:
                zip_path = self.create_output_zip(output_files)
                result['zip_file'] = str(zip_path)
            
            return result
            
        except Exception as e:
            logger.error(f"Error in process_from_path: {e}")
            return {
                'success': False,
                'error': str(e),
                'input_count': 0,
                'output_count': 0
            }
        
        finally:
            # Always cleanup temp files
            self.cleanup_temp()
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        self.cleanup_temp()
