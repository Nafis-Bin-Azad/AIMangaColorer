"""
Manga Downloader
Download manga chapters from various sources
"""
from pathlib import Path
from PIL import Image
import logging
from typing import List, Optional, Callable
from manga_scrapers import BaseMangaScraper, Chapter

logger = logging.getLogger(__name__)


class MangaDownloader:
    """Download manga chapters from a scraper"""
    
    def __init__(self, scraper: BaseMangaScraper, download_dir: Path):
        """
        Initialize manga downloader.
        
        Args:
            scraper: Manga scraper instance
            download_dir: Base directory for downloads
        """
        self.scraper = scraper
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.should_cancel = False
    
    def download_chapter(
        self,
        chapter: Chapter,
        manga_title: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Path:
        """
        Download a single chapter.
        
        Args:
            chapter: Chapter to download
            manga_title: Title of the manga (for folder naming)
            progress_callback: Optional callback(current, total, url)
            
        Returns:
            Path to chapter directory
        """
        # Create chapter folder
        safe_manga = self._sanitize_filename(manga_title)
        safe_chapter = self._sanitize_filename(f"Ch_{chapter.chapter_number}")
        chapter_dir = self.download_dir / safe_manga / safe_chapter
        chapter_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Downloading {manga_title} - Chapter {chapter.chapter_number}")
        
        try:
            # Get image URLs
            image_urls = self.scraper.get_chapter_images(chapter.id)
            logger.info(f"Found {len(image_urls)} pages")
            
            # Download images
            for idx, url in enumerate(image_urls):
                if self.should_cancel:
                    logger.info("Download cancelled by user")
                    break
                
                if progress_callback:
                    progress_callback(idx + 1, len(image_urls), url)
                
                try:
                    img = self.scraper.download_image(url)
                    img_path = chapter_dir / f"{idx+1:03d}.jpg"
                    
                    # Convert to RGB if needed
                    if img.mode in ('RGBA', 'LA', 'P'):
                        rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                        img = rgb_img
                    
                    img.save(img_path, "JPEG", quality=95)
                    logger.debug(f"Downloaded page {idx+1}/{len(image_urls)}")
                    
                except Exception as e:
                    logger.error(f"Failed to download page {idx+1}: {e}")
                    continue
            
            logger.info(f"Chapter downloaded to {chapter_dir}")
            return chapter_dir
            
        except Exception as e:
            logger.error(f"Failed to download chapter: {e}")
            raise
    
    def download_multiple_chapters(
        self,
        chapters: List[Chapter],
        manga_title: str,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Path]:
        """
        Download multiple chapters.
        
        Args:
            chapters: List of chapters to download
            manga_title: Title of the manga
            progress_callback: Optional callback(current, total, chapter_name)
            
        Returns:
            List of paths to downloaded chapter directories
        """
        downloaded = []
        
        for i, chapter in enumerate(chapters):
            if self.should_cancel:
                logger.info("Batch download cancelled")
                break
            
            if progress_callback:
                progress_callback(
                    i + 1,
                    len(chapters),
                    f"Chapter {chapter.chapter_number}"
                )
            
            try:
                chapter_dir = self.download_chapter(chapter, manga_title)
                downloaded.append(chapter_dir)
            except Exception as e:
                logger.error(f"Failed to download chapter {chapter.chapter_number}: {e}")
                continue
        
        return downloaded
    
    def cancel(self):
        """Cancel ongoing download"""
        self.should_cancel = True
        logger.info("Download cancellation requested")
    
    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """
        Remove invalid filename characters.
        
        Args:
            name: Original filename
            
        Returns:
            Sanitized filename
        """
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        # Remove leading/trailing spaces and dots
        name = name.strip('. ')
        # Limit length
        return name[:200] if len(name) > 200 else name
