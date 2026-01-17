"""
Manga Library Manager
Manages downloaded manga library, reading progress, bookmarks, and history
"""
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional
import json
from datetime import datetime
from PIL import Image
import logging

logger = logging.getLogger(__name__)


@dataclass
class ReadingProgress:
    """Reading progress for a chapter"""
    manga_title: str
    chapter: str
    page: int
    total_pages: int
    last_read: str  # ISO timestamp
    
    def to_dict(self):
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data):
        return cls(**data)


@dataclass
class MangaEntry:
    """Manga entry in library"""
    title: str
    path: Path
    chapters: List[str]
    cover_path: Optional[Path]
    last_read: Optional[str]
    total_chapters: int
    
    def to_dict(self):
        return {
            'title': self.title,
            'path': str(self.path),
            'chapters': self.chapters,
            'cover_path': str(self.cover_path) if self.cover_path else None,
            'last_read': self.last_read,
            'total_chapters': self.total_chapters
        }


class MangaLibrary:
    """Manage downloaded manga library and reading progress"""
    
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
    
    def __init__(self, downloads_dir: Path, data_file: Path):
        """
        Initialize manga library.
        
        Args:
            downloads_dir: Directory containing downloaded manga
            data_file: JSON file for storing progress and bookmarks
        """
        self.downloads_dir = Path(downloads_dir)
        self.data_file = Path(data_file)
        self.progress: Dict[str, Dict[str, ReadingProgress]] = {}
        self.bookmarks: Dict[str, Dict[str, List[int]]] = {}
        self.history: List[Dict] = []
        self.load_data()
    
    def scan_library(self) -> List[MangaEntry]:
        """
        Scan downloads folder for manga.
        
        Returns:
            List of manga entries
        """
        manga_list = []
        
        if not self.downloads_dir.exists():
            logger.info("Downloads directory does not exist")
            return manga_list
        
        # Each manga is a folder in downloads/
        for manga_dir in self.downloads_dir.iterdir():
            if not manga_dir.is_dir():
                continue
            
            try:
                # Find chapters (folders starting with Ch_)
                chapters = sorted([
                    d.name for d in manga_dir.iterdir()
                    if d.is_dir() and d.name.startswith('Ch_')
                ])
                
                if not chapters:
                    continue
                
                # Get or generate cover
                cover_path = self.generate_cover(manga_dir)
                
                # Get last read time
                last_read = None
                if manga_dir.name in self.progress:
                    latest = max(
                        self.progress[manga_dir.name].values(),
                        key=lambda p: p.last_read
                    )
                    last_read = latest.last_read
                
                manga_entry = MangaEntry(
                    title=manga_dir.name,
                    path=manga_dir,
                    chapters=chapters,
                    cover_path=cover_path,
                    last_read=last_read,
                    total_chapters=len(chapters)
                )
                
                manga_list.append(manga_entry)
                
            except Exception as e:
                logger.error(f"Error scanning manga {manga_dir.name}: {e}")
                continue
        
        return manga_list
    
    def generate_cover(self, manga_path: Path) -> Optional[Path]:
        """
        Generate cover thumbnail from first page of first chapter.
        
        Args:
            manga_path: Path to manga directory
            
        Returns:
            Path to cover thumbnail or None
        """
        cover_path = manga_path / "cover_thumb.jpg"
        
        # Use existing cover if available
        if cover_path.exists():
            return cover_path
        
        try:
            # Find first chapter
            chapters = sorted([d for d in manga_path.iterdir() if d.is_dir() and d.name.startswith('Ch_')])
            if not chapters:
                return None
            
            # Get first page
            first_chapter = chapters[0]
            pages = sorted([
                f for f in first_chapter.iterdir()
                if f.suffix.lower() in self.SUPPORTED_EXTENSIONS
            ])
            
            if not pages:
                return None
            
            # Create thumbnail
            img = Image.open(pages[0])
            img.thumbnail((200, 300), Image.Resampling.LANCZOS)
            img.save(cover_path, "JPEG", quality=90)
            
            logger.info(f"Generated cover for {manga_path.name}")
            return cover_path
            
        except Exception as e:
            logger.error(f"Failed to generate cover for {manga_path.name}: {e}")
            return None
    
    def has_colored_version(self, manga_title: str, chapter: str = None) -> bool:
        """
        Check if colored version exists for this manga.
        
        Args:
            manga_title: Title of manga
            chapter: Optional specific chapter to check
            
        Returns:
            True if colored version exists
        """
        colored_base_path = self.downloads_dir.parent / "output" / f"{manga_title}_colored"
        
        if not colored_base_path.exists():
            return False
        
        # If checking specific chapter
        if chapter:
            chapter_path = colored_base_path / chapter
            if chapter_path.exists() and chapter_path.is_dir():
                return any(
                    f.suffix.lower() in self.SUPPORTED_EXTENSIONS
                    for f in chapter_path.iterdir()
                    if f.is_file()
                )
        
        # Check if any colored files exist (chapter-organized or flat)
        return any(
            f.suffix.lower() in self.SUPPORTED_EXTENSIONS
            for f in colored_base_path.rglob('*')
            if f.is_file()
        )
    
    def get_chapter_pages(self, manga_title: str, chapter: str, use_colored: bool = False) -> List[Path]:
        """
        Get list of page paths for a chapter.
        
        Args:
            manga_title: Title of manga
            chapter: Chapter name (e.g., "Ch_001")
            use_colored: If True, try to load colored version first
            
        Returns:
            Sorted list of page paths
        """
        # Check for colored version first if requested
        if use_colored:
            # Try chapter-organized colored structure first
            colored_path = self.downloads_dir.parent / "output" / f"{manga_title}_colored" / chapter
            if colored_path.exists():
                colored_files = sorted([
                    f for f in colored_path.iterdir()
                    if f.suffix.lower() in self.SUPPORTED_EXTENSIONS
                ])
                if colored_files:
                    logger.info(f"Loading colored version from {colored_path}")
                    return colored_files
            
            # Fallback: try flat colored structure (legacy)
            flat_colored_path = self.downloads_dir.parent / "output" / f"{manga_title}_colored"
            if flat_colored_path.exists() and flat_colored_path.is_dir():
                colored_files = sorted([
                    f for f in flat_colored_path.iterdir()
                    if f.suffix.lower() in self.SUPPORTED_EXTENSIONS and f.is_file()
                ])
                if colored_files:
                    logger.info(f"Loading colored version from flat structure: {flat_colored_path}")
                    return colored_files
        
        # Fallback to original
        chapter_path = self.downloads_dir / manga_title / chapter
        
        if not chapter_path.exists():
            return []
        
        pages = sorted([
            f for f in chapter_path.iterdir()
            if f.suffix.lower() in self.SUPPORTED_EXTENSIONS
        ])
        
        return pages
    
    def get_progress(self, manga_title: str, chapter: str) -> Optional[ReadingProgress]:
        """
        Get reading progress for a chapter.
        
        Args:
            manga_title: Title of manga
            chapter: Chapter name
            
        Returns:
            ReadingProgress or None
        """
        if manga_title in self.progress:
            return self.progress[manga_title].get(chapter)
        return None
    
    def save_progress(self, manga_title: str, chapter: str, page: int, total_pages: int):
        """
        Save reading progress.
        
        Args:
            manga_title: Title of manga
            chapter: Chapter name
            page: Current page number
            total_pages: Total pages in chapter
        """
        if manga_title not in self.progress:
            self.progress[manga_title] = {}
        
        self.progress[manga_title][chapter] = ReadingProgress(
            manga_title=manga_title,
            chapter=chapter,
            page=page,
            total_pages=total_pages,
            last_read=datetime.now().isoformat()
        )
        
        self.save_data()
        logger.debug(f"Saved progress: {manga_title} - {chapter} - Page {page}/{total_pages}")
    
    def add_bookmark(self, manga_title: str, chapter: str, page: int):
        """
        Add bookmark for a page.
        
        Args:
            manga_title: Title of manga
            chapter: Chapter name
            page: Page number to bookmark
        """
        if manga_title not in self.bookmarks:
            self.bookmarks[manga_title] = {}
        
        if chapter not in self.bookmarks[manga_title]:
            self.bookmarks[manga_title][chapter] = []
        
        if page not in self.bookmarks[manga_title][chapter]:
            self.bookmarks[manga_title][chapter].append(page)
            self.bookmarks[manga_title][chapter].sort()
            self.save_data()
            logger.info(f"Added bookmark: {manga_title} - {chapter} - Page {page}")
    
    def remove_bookmark(self, manga_title: str, chapter: str, page: int):
        """
        Remove bookmark for a page.
        
        Args:
            manga_title: Title of manga
            chapter: Chapter name
            page: Page number to remove bookmark from
        """
        if manga_title in self.bookmarks:
            if chapter in self.bookmarks[manga_title]:
                if page in self.bookmarks[manga_title][chapter]:
                    self.bookmarks[manga_title][chapter].remove(page)
                    self.save_data()
                    logger.info(f"Removed bookmark: {manga_title} - {chapter} - Page {page}")
    
    def get_bookmarks(self, manga_title: str, chapter: str) -> List[int]:
        """
        Get bookmarks for a chapter.
        
        Args:
            manga_title: Title of manga
            chapter: Chapter name
            
        Returns:
            List of bookmarked page numbers
        """
        if manga_title in self.bookmarks:
            return self.bookmarks[manga_title].get(chapter, [])
        return []
    
    def add_to_history(self, manga_title: str, chapter: str):
        """
        Add to reading history.
        
        Args:
            manga_title: Title of manga
            chapter: Chapter name
        """
        history_entry = {
            'manga_title': manga_title,
            'chapter': chapter,
            'timestamp': datetime.now().isoformat()
        }
        
        # Remove duplicate if exists
        self.history = [h for h in self.history 
                       if not (h['manga_title'] == manga_title and h['chapter'] == chapter)]
        
        # Add to front
        self.history.insert(0, history_entry)
        
        # Keep only last 50
        self.history = self.history[:50]
        
        self.save_data()
    
    def get_history(self, limit: int = 20) -> List[Dict]:
        """
        Get recent reading history.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of history entries
        """
        return self.history[:limit]
    
    def load_data(self):
        """Load progress and bookmarks from file"""
        if not self.data_file.exists():
            return
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Load progress
            progress_data = data.get('progress', {})
            self.progress = {}
            for manga_title, chapters in progress_data.items():
                self.progress[manga_title] = {}
                for chapter, prog_dict in chapters.items():
                    self.progress[manga_title][chapter] = ReadingProgress.from_dict(prog_dict)
            
            # Load bookmarks
            self.bookmarks = data.get('bookmarks', {})
            
            # Load history
            self.history = data.get('history', [])
            
            logger.info("Loaded library data")
            
        except Exception as e:
            logger.error(f"Failed to load library data: {e}")
    
    def save_data(self):
        """Save progress and bookmarks to file"""
        try:
            # Convert progress to dict
            progress_data = {}
            for manga_title, chapters in self.progress.items():
                progress_data[manga_title] = {}
                for chapter, prog in chapters.items():
                    progress_data[manga_title][chapter] = prog.to_dict()
            
            data = {
                'progress': progress_data,
                'bookmarks': self.bookmarks,
                'history': self.history
            }
            
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.debug("Saved library data")
            
        except Exception as e:
            logger.error(f"Failed to save library data: {e}")
