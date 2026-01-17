"""
Manga Source Manager
Manages available manga scrapers and sources
"""
from typing import Dict, List, Optional
import requests
import logging
from manga_scrapers import (
    BaseMangaScraper, MangaDexScraper, MangakakalotScraper,
    ComicKScraper, MangaseeScraper, AsuraScansScraper,
    MangaFreakScraper, MangaBuddyScraper, MangaHereScraper, TCBScansScraper,
    MangaFireScraper
)

logger = logging.getLogger(__name__)


class SourceManager:
    """Manage manga sources and scrapers"""
    
    # Tachiyomi extension repository (for reference)
    EXTENSION_LIST_URL = "https://raw.githubusercontent.com/keiyoushi/extensions/repo/index.min.json"
    
    def __init__(self):
        """Initialize source manager and load available scrapers"""
        self.scrapers: Dict[str, BaseMangaScraper] = {}
        self._load_scrapers()
        logger.info(f"Loaded {len(self.scrapers)} manga scrapers")
    
    def _load_scrapers(self):
        """Load all available Python scrapers"""
        # Initialize all scrapers
        self.scrapers["MangaDex"] = MangaDexScraper()
        self.scrapers["Mangakakalot"] = MangakakalotScraper()
        self.scrapers["ComicK"] = ComicKScraper()
        self.scrapers["MangaFire"] = MangaFireScraper()
        self.scrapers["Mangasee123"] = MangaseeScraper()
        self.scrapers["AsuraScans"] = AsuraScansScraper()
        self.scrapers["MangaFreak"] = MangaFreakScraper()
        self.scrapers["MangaBuddy"] = MangaBuddyScraper()
        self.scrapers["MangaHere"] = MangaHereScraper()
        self.scrapers["TCBScans"] = TCBScansScraper()
    
    def get_available_sources(self) -> List[str]:
        """
        Get list of available manga sources.
        
        Returns:
            List of source names
        """
        return sorted(list(self.scrapers.keys()))
    
    def get_scraper(self, source_name: str) -> Optional[BaseMangaScraper]:
        """
        Get scraper by source name.
        
        Args:
            source_name: Name of the manga source
            
        Returns:
            Scraper instance or None if not found
        """
        return self.scrapers.get(source_name)
    
    def fetch_tachiyomi_extensions(self) -> List[Dict]:
        """
        Fetch Tachiyomi extension list (for informational purposes).
        
        This doesn't install extensions, just shows what's available.
        
        Returns:
            List of extension metadata
        """
        try:
            response = requests.get(self.EXTENSION_LIST_URL, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch Tachiyomi extensions: {e}")
            return []
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get list of Tachiyomi sources we have Python scrapers for.
        
        This matches our Python scrapers with Tachiyomi's extension list.
        
        Returns:
            List of supported source names
        """
        try:
            tachi_extensions = self.fetch_tachiyomi_extensions()
            supported = []
            
            for ext in tachi_extensions:
                for source in ext.get("sources", []):
                    source_name = source.get("name", "")
                    if source_name in self.scrapers:
                        supported.append(source_name)
            
            return sorted(set(supported))
        except Exception as e:
            logger.error(f"Failed to get supported extensions: {e}")
            return []
    
    def get_source_info(self) -> Dict[str, Dict]:
        """
        Get information about all available sources.
        
        Returns:
            Dictionary with source info
        """
        info = {}
        for name, scraper in self.scrapers.items():
            info[name] = {
                "name": name,
                "type": "API" if "api" in name.lower() else "Scraper",
                "available": True
            }
        return info
