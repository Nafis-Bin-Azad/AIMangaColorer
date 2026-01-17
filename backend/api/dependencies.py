"""
Shared dependencies for API routes
"""
import sys
from pathlib import Path
from typing import Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from core.mcv2_engine import MangaColorizationV2Engine
from core.image_utils import ImageUtils
from core.batch_processor import BatchProcessor
from core.manga_library import MangaLibrary
try:
    from core.manga_source_manager import SourceManager as MangaSourceManager
except ImportError:
    MangaSourceManager = None

# Global instances
_mcv2_engine: Optional[MangaColorizationV2Engine] = None
_image_utils: Optional[ImageUtils] = None
_manga_library: Optional[MangaLibrary] = None
_source_manager: Optional[MangaSourceManager] = None

def get_mcv2_engine() -> MangaColorizationV2Engine:
    """Get or initialize MCV2 engine"""
    global _mcv2_engine
    if _mcv2_engine is None:
        _mcv2_engine = MangaColorizationV2Engine()
        _mcv2_engine.ensure_weights()
        _mcv2_engine.load_model()
    return _mcv2_engine

def get_image_utils() -> ImageUtils:
    """Get or initialize image utilities"""
    global _image_utils
    if _image_utils is None:
        _image_utils = ImageUtils()
    return _image_utils

def get_manga_library() -> MangaLibrary:
    """Get or initialize manga library"""
    global _manga_library
    if _manga_library is None:
        library_dir = Path("library")
        data_file = Path("manga_data.json")
        _manga_library = MangaLibrary(library_dir, data_file)
    return _manga_library

def get_source_manager():
    """Get or initialize source manager"""
    global _source_manager
    if _source_manager is None and MangaSourceManager:
        _source_manager = MangaSourceManager()
    return _source_manager
