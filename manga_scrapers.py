"""
Manga Scrapers Framework
Unified interface for downloading manga from multiple sources
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional
import requests
from PIL import Image
import io
import logging
from bs4 import BeautifulSoup
import re
from urllib.parse import quote, urljoin

logger = logging.getLogger(__name__)


@dataclass
class MangaInfo:
    """Information about a manga series"""
    id: str
    title: str
    description: str
    cover_url: str
    authors: List[str]
    genres: List[str]
    status: str  # "ongoing", "completed", etc.
    source: str


@dataclass
class Chapter:
    """Information about a manga chapter"""
    id: str
    manga_id: str
    title: str
    chapter_number: str
    url: str
    pages: int = 0


class BaseMangaScraper(ABC):
    """Base class for all manga scrapers"""
    
    @property
    @abstractmethod
    def source_name(self) -> str:
        """Name of the manga source"""
        pass
    
    @abstractmethod
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        """
        Search for manga by title.
        
        Args:
            query: Search query
            page: Page number for pagination
            
        Returns:
            List of manga matching the search
        """
        pass
    
    @abstractmethod
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        """
        Get detailed information about a manga.
        
        Args:
            manga_id: Unique identifier for the manga
            
        Returns:
            Detailed manga information
        """
        pass
    
    @abstractmethod
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        """
        Get list of chapters for a manga.
        
        Args:
            manga_id: Unique identifier for the manga
            
        Returns:
            List of chapters
        """
        pass
    
    @abstractmethod
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        """
        Get image URLs for a chapter.
        
        Args:
            chapter_id: Unique identifier for the chapter
            
        Returns:
            List of image URLs
        """
        pass
    
    def download_image(self, url: str) -> Image.Image:
        """
        Download a single image.
        
        Args:
            url: Image URL
            
        Returns:
            PIL Image object
        """
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=30)
            response.raise_for_status()
            return Image.open(io.BytesIO(response.content))
        except Exception as e:
            logger.error(f"Failed to download image from {url}: {e}")
            raise
    
    def get_headers(self) -> Dict[str, str]:
        """Get HTTP headers for requests"""
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }


class MangaDexScraper(BaseMangaScraper):
    """
    MangaDex scraper using API v5.
    Official API documentation: https://api.mangadex.org/docs/
    """
    
    BASE_URL = "https://api.mangadex.org"
    
    @property
    def source_name(self) -> str:
        return "MangaDex"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        """Search MangaDex for manga"""
        url = f"{self.BASE_URL}/manga"
        params = {
            "title": query,
            "limit": 20,
            "offset": (page - 1) * 20,
            "includes[]": ["cover_art", "author"],
            "order[relevance]": "desc",
            "contentRating[]": ["safe", "suggestive", "erotica"],
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for manga in data.get("data", []):
                try:
                    results.append(self._parse_manga(manga))
                except Exception as e:
                    logger.warning(f"Failed to parse manga: {e}")
                    continue
            
            return results
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        """Get detailed manga information"""
        url = f"{self.BASE_URL}/manga/{manga_id}"
        params = {"includes[]": ["cover_art", "author"]}
        
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        return self._parse_manga(data["data"])
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        """Get chapter list for a manga"""
        url = f"{self.BASE_URL}/manga/{manga_id}/feed"
        params = {
            "translatedLanguage[]": ["en"],
            "order[chapter]": "asc",
            "limit": 500,
            "contentRating[]": ["safe", "suggestive", "erotica"],
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            chapters = []
            for ch in data.get("data", []):
                try:
                    chapters.append(self._parse_chapter(ch, manga_id))
                except Exception as e:
                    logger.warning(f"Failed to parse chapter: {e}")
                    continue
            
            return chapters
        except Exception as e:
            logger.error(f"Failed to get chapters: {e}")
            raise
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        """Get image URLs for a chapter"""
        url = f"{self.BASE_URL}/at-home/server/{chapter_id}"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            base_url = data["baseUrl"]
            chapter_hash = data["chapter"]["hash"]
            images = data["chapter"]["data"]
            
            # Build image URLs
            image_urls = []
            for img in images:
                image_urls.append(f"{base_url}/data/{chapter_hash}/{img}")
            
            return image_urls
        except Exception as e:
            logger.error(f"Failed to get chapter images: {e}")
            raise
    
    def _parse_manga(self, data: dict) -> MangaInfo:
        """Parse manga data from API response"""
        attrs = data["attributes"]
        
        # Get title (prefer English)
        title_obj = attrs.get("title", {})
        title = title_obj.get("en") or list(title_obj.values())[0] if title_obj else "Unknown"
        
        # Get description (prefer English)
        desc_obj = attrs.get("description", {})
        description = desc_obj.get("en", "No description available")
        
        # Get cover URL
        cover_url = ""
        for rel in data.get("relationships", []):
            if rel["type"] == "cover_art":
                cover_filename = rel["attributes"]["fileName"]
                cover_url = f"https://uploads.mangadex.org/covers/{data['id']}/{cover_filename}"
                break
        
        # Get authors
        authors = []
        for rel in data.get("relationships", []):
            if rel["type"] == "author":
                authors.append(rel["attributes"].get("name", "Unknown"))
        
        # Get genres/tags
        genres = [tag["attributes"]["name"]["en"] for tag in attrs.get("tags", [])]
        
        return MangaInfo(
            id=data["id"],
            title=title,
            description=description,
            cover_url=cover_url,
            authors=authors,
            genres=genres[:5],  # Limit to 5 genres
            status=attrs.get("status", "unknown"),
            source=self.source_name
        )
    
    def _parse_chapter(self, data: dict, manga_id: str) -> Chapter:
        """Parse chapter data from API response"""
        attrs = data["attributes"]
        
        chapter_num = attrs.get("chapter", "0")
        title = attrs.get("title", "")
        pages = attrs.get("pages", 0)
        
        return Chapter(
            id=data["id"],
            manga_id=manga_id,
            title=title,
            chapter_number=chapter_num,
            url=f"https://mangadex.org/chapter/{data['id']}",
            pages=pages
        )


class MangakakalotScraper(BaseMangaScraper):
    """
    Scraper for Mangakakalot/Manganato (same network).
    Uses web scraping with BeautifulSoup.
    """
    
    BASE_URL = "https://mangakakalot.com"
    SEARCH_URL = "https://mangakakalot.com/search/story/"
    
    @property
    def source_name(self) -> str:
        return "Mangakakalot"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        """Search Mangakakalot for manga"""
        search_query = quote(query.replace(" ", "_"))
        url = f"{self.SEARCH_URL}{search_query}"
        
        try:
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            results = []
            
            # Find search results
            story_items = soup.find_all('div', class_='story_item')
            
            for item in story_items[:20]:  # Limit to 20 results
                try:
                    # Get title and link
                    title_elem = item.find('h3', class_='story_name')
                    if not title_elem or not title_elem.find('a'):
                        continue
                    
                    link = title_elem.find('a')
                    title = link.text.strip()
                    manga_url = link['href']
                    manga_id = manga_url  # Use URL as ID
                    
                    # Get cover
                    cover_elem = item.find('img')
                    cover_url = cover_elem['src'] if cover_elem else ""
                    
                    # Get authors
                    authors = []
                    author_elem = item.find('span', text=re.compile(r'Author'))
                    if author_elem and author_elem.find_next('a'):
                        authors = [author_elem.find_next('a').text.strip()]
                    
                    # Get status
                    status = "unknown"
                    status_elem = item.find('em', class_='story_status')
                    if status_elem:
                        status_text = status_elem.text.lower()
                        if 'ongoing' in status_text:
                            status = 'ongoing'
                        elif 'completed' in status_text:
                            status = 'completed'
                    
                    results.append(MangaInfo(
                        id=manga_id,
                        title=title,
                        description="",  # Not available in search results
                        cover_url=cover_url,
                        authors=authors,
                        genres=[],
                        status=status,
                        source=self.source_name
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse search result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        """Get detailed manga information"""
        # manga_id is the full URL
        try:
            response = requests.get(manga_id, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Title
            title_elem = soup.find('h1')
            title = title_elem.text.strip() if title_elem else "Unknown"
            
            # Cover
            cover_elem = soup.find('div', class_='manga-info-pic')
            cover_url = ""
            if cover_elem and cover_elem.find('img'):
                cover_url = cover_elem.find('img')['src']
            
            # Description
            description = ""
            desc_elem = soup.find('div', id='noidungm')
            if desc_elem:
                description = desc_elem.text.strip()
            
            # Authors and status
            authors = []
            status = "unknown"
            info_list = soup.find_all('li', class_='a-h')
            for li in info_list:
                text = li.text.lower()
                if 'author' in text:
                    author_links = li.find_all('a')
                    authors = [a.text.strip() for a in author_links]
                elif 'status' in text:
                    if 'ongoing' in text:
                        status = 'ongoing'
                    elif 'completed' in text:
                        status = 'completed'
            
            # Genres
            genres = []
            genre_elems = soup.find_all('a', class_='a-h')
            genres = [g.text.strip() for g in genre_elems[:5]]
            
            return MangaInfo(
                id=manga_id,
                title=title,
                description=description,
                cover_url=cover_url,
                authors=authors,
                genres=genres,
                status=status,
                source=self.source_name
            )
            
        except Exception as e:
            logger.error(f"Failed to get manga details: {e}")
            raise
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        """Get chapter list for a manga"""
        try:
            response = requests.get(manga_id, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            chapters = []
            
            # Find chapter list
            chapter_list = soup.find('div', class_='chapter-list')
            if not chapter_list:
                return chapters
            
            chapter_rows = chapter_list.find_all('div', class_='row')
            
            for row in chapter_rows:
                try:
                    link_elem = row.find('a')
                    if not link_elem:
                        continue
                    
                    chapter_url = link_elem['href']
                    chapter_title = link_elem.text.strip()
                    
                    # Extract chapter number
                    chapter_num = "0"
                    match = re.search(r'chapter[_\s]+(\d+(?:\.\d+)?)', chapter_title.lower())
                    if match:
                        chapter_num = match.group(1)
                    
                    chapters.append(Chapter(
                        id=chapter_url,
                        manga_id=manga_id,
                        title=chapter_title,
                        chapter_number=chapter_num,
                        url=chapter_url,
                        pages=0
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse chapter: {e}")
                    continue
            
            # Reverse to get ascending order
            chapters.reverse()
            
            return chapters
            
        except Exception as e:
            logger.error(f"Failed to get chapters: {e}")
            raise
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        """Get image URLs for a chapter"""
        # chapter_id is the chapter URL
        try:
            response = requests.get(chapter_id, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            image_urls = []
            
            # Find image container
            container = soup.find('div', class_='container-chapter-reader')
            if not container:
                return image_urls
            
            # Get all images
            images = container.find_all('img')
            
            for img in images:
                if 'src' in img.attrs:
                    image_urls.append(img['src'])
            
            return image_urls
            
        except Exception as e:
            logger.error(f"Failed to get chapter images: {e}")
            raise


class ComicKScraper(BaseMangaScraper):
    """
    ComicK.io scraper using their API.
    API documentation: https://api.comick.io
    """
    
    BASE_URL = "https://api.comick.io"
    
    @property
    def source_name(self) -> str:
        return "ComicK"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        """Search ComicK for manga"""
        url = f"{self.BASE_URL}/v1.0/search"
        params = {
            "q": query,
            "limit": 20,
            "page": page
        }
        
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data:
                try:
                    # Get cover URL
                    cover_url = ""
                    if 'cover' in item and item['cover']:
                        cover_url = f"https://meo.comick.pictures/{item['cover']}"
                    elif 'md_covers' in item and item['md_covers']:
                        cover_url = f"https://meo.comick.pictures/{item['md_covers'][0]['b2key']}"
                    
                    # Get status
                    status = "unknown"
                    if 'status' in item:
                        status_val = item['status']
                        if status_val == 1:
                            status = 'ongoing'
                        elif status_val == 2:
                            status = 'completed'
                    
                    results.append(MangaInfo(
                        id=item.get('slug', ''),
                        title=item.get('title', 'Unknown'),
                        description=item.get('desc', ''),
                        cover_url=cover_url,
                        authors=[item.get('author', '')] if 'author' in item else [],
                        genres=[],
                        status=status,
                        source=self.source_name
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse search result: {e}")
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        """Get detailed manga information"""
        url = f"{self.BASE_URL}/comic/{manga_id}"
        
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            comic = data.get('comic', {})
            
            # Cover URL
            cover_url = ""
            if 'md_covers' in comic and comic['md_covers']:
                cover_url = f"https://meo.comick.pictures/{comic['md_covers'][0]['b2key']}"
            
            # Status
            status = "unknown"
            if 'status' in comic:
                status_val = comic['status']
                if status_val == 1:
                    status = 'ongoing'
                elif status_val == 2:
                    status = 'completed'
            
            # Authors
            authors = []
            if 'mu_comics' in comic and comic['mu_comics']:
                for mu in comic['mu_comics']:
                    if 'mu_comic_authors' in mu:
                        for author_data in mu['mu_comic_authors']:
                            if 'mu_people' in author_data:
                                authors.append(author_data['mu_people'].get('name', ''))
            
            # Genres
            genres = []
            if 'md_comic_md_genres' in comic:
                for genre_data in comic['md_comic_md_genres']:
                    if 'md_genres' in genre_data:
                        genres.append(genre_data['md_genres'].get('name', ''))
            
            return MangaInfo(
                id=manga_id,
                title=comic.get('title', 'Unknown'),
                description=comic.get('desc', ''),
                cover_url=cover_url,
                authors=authors,
                genres=genres[:5],
                status=status,
                source=self.source_name
            )
            
        except Exception as e:
            logger.error(f"Failed to get manga details: {e}")
            raise
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        """Get chapter list for a manga"""
        url = f"{self.BASE_URL}/comic/{manga_id}/chapters"
        params = {"lang": "en"}
        
        try:
            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            chapters = []
            for ch_data in data.get('chapters', []):
                try:
                    chapter_num = str(ch_data.get('chap', '0'))
                    title = ch_data.get('title', '')
                    
                    chapters.append(Chapter(
                        id=ch_data.get('hid', ''),
                        manga_id=manga_id,
                        title=title,
                        chapter_number=chapter_num,
                        url=f"https://comick.io/comic/{manga_id}/{ch_data.get('hid', '')}",
                        pages=0
                    ))
                    
                except Exception as e:
                    logger.warning(f"Failed to parse chapter: {e}")
                    continue
            
            # Sort by chapter number
            chapters.sort(key=lambda c: float(c.chapter_number) if c.chapter_number.replace('.', '').isdigit() else 0)
            
            return chapters
            
        except Exception as e:
            logger.error(f"Failed to get chapters: {e}")
            raise
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        """Get image URLs for a chapter"""
        url = f"{self.BASE_URL}/chapter/{chapter_id}"
        
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            image_urls = []
            chapter = data.get('chapter', {})
            
            for img_data in chapter.get('md_images', []):
                image_url = f"https://meo.comick.pictures/{img_data.get('b2key', '')}"
                image_urls.append(image_url)
            
            return image_urls
            
        except Exception as e:
            logger.error(f"Failed to get chapter images: {e}")
            raise


class MangaseeScraper(BaseMangaScraper):
    """Mangasee123 scraper using web scraping"""
    
    BASE_URL = "https://mangasee123.com"
    
    @property
    def source_name(self) -> str:
        return "Mangasee123"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        """Search Mangasee for manga"""
        # Mangasee uses a POST endpoint for search
        url = f"{self.BASE_URL}/_search.php"
        
        try:
            response = requests.post(
                url,
                headers=self.get_headers(),
                data={"search": query},
                timeout=15
            )
            response.raise_for_status()
            
            # Parse JSON response
            data = response.json()
            results = []
            
            for item in data[:20]:
                try:
                    manga_id = item.get('i', '')
                    manga_url = f"{self.BASE_URL}/manga/{manga_id}"
                    title = item.get('s', 'Unknown')
                    
                    # Get authors as list
                    authors = []
                    if 'a' in item and item['a']:
                        authors = [item['a']] if isinstance(item['a'], str) else item['a']
                    
                    # Get genres
                    genres = item.get('g', []) if isinstance(item.get('g'), list) else []
                    
                    results.append(MangaInfo(
                        id=manga_url,
                        title=title,
                        description="",
                        cover_url="",
                        authors=authors,
                        genres=genres[:5],
                        status=item.get('ps', 'unknown'),
                        source=self.source_name
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse search result: {e}")
                    continue
            
            return results
        except Exception as e:
            logger.error(f"Mangasee search failed: {e}")
            # Return empty instead of raising to allow other sources to work
            return []
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        return MangaInfo(id=manga_id, title="Unknown", description="", cover_url="",
                        authors=[], genres=[], status="unknown", source=self.source_name)
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        try:
            response = requests.get(manga_id, headers=self.get_headers(), timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            chapters = []
            
            chapter_divs = soup.find_all('a', class_='ChapterLink')
            for link in chapter_divs:
                try:
                    chapter_url = urljoin(self.BASE_URL, link['href'])
                    chapter_title = link.text.strip()
                    match = re.search(r'(\d+(?:\.\d+)?)', chapter_title)
                    chapter_num = match.group(1) if match else "0"
                    
                    chapters.append(Chapter(
                        id=chapter_url, manga_id=manga_id, title=chapter_title,
                        chapter_number=chapter_num, url=chapter_url, pages=0
                    ))
                except Exception as e:
                    continue
            
            return chapters
        except Exception as e:
            logger.error(f"Failed to get chapters: {e}")
            raise
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        # Mangasee uses JavaScript, basic scraping may not work
        return []


class AsuraScansScraper(BaseMangaScraper):
    """AsuraScans scraper"""
    
    BASE_URL = "https://asuracomic.net"
    
    @property
    def source_name(self) -> str:
        return "AsuraScans"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        # AsuraScans often blocks scrapers, implement with caution
        return []
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        return MangaInfo(id=manga_id, title="Unknown", description="", cover_url="",
                        authors=[], genres=[], status="unknown", source=self.source_name)
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        return []
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        return []


# Additional simplified scrapers
class MangaFreakScraper(BaseMangaScraper):
    """MangaFreak scraper (simplified)"""
    BASE_URL = "https://mangafreak.net"
    
    @property
    def source_name(self) -> str:
        return "MangaFreak"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        # Simplified implementation - returns empty for now
        return []
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        return MangaInfo(id=manga_id, title="Unknown", description="", cover_url="",
                        authors=[], genres=[], status="unknown", source=self.source_name)
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        return []
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        return []


class MangaBuddyScraper(BaseMangaScraper):
    """MangaBuddy scraper (simplified)"""
    BASE_URL = "https://mangabuddy.com"
    
    @property
    def source_name(self) -> str:
        return "MangaBuddy"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        return []
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        return MangaInfo(id=manga_id, title="Unknown", description="", cover_url="",
                        authors=[], genres=[], status="unknown", source=self.source_name)
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        return []
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        return []


class MangaHereScraper(BaseMangaScraper):
    """MangaHere scraper (simplified)"""
    BASE_URL = "https://www.mangahere.cc"
    
    @property
    def source_name(self) -> str:
        return "MangaHere"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        return []
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        return MangaInfo(id=manga_id, title="Unknown", description="", cover_url="",
                        authors=[], genres=[], status="unknown", source=self.source_name)
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        return []
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        return []


class TCBScansScraper(BaseMangaScraper):
    """TCBScans scraper (One Piece and popular ongoing series)"""
    BASE_URL = "https://tcbscans.com"
    
    @property
    def source_name(self) -> str:
        return "TCBScans"
    
    def search(self, query: str, page: int = 1) -> List[MangaInfo]:
        return []
    
    def get_manga_details(self, manga_id: str) -> MangaInfo:
        return MangaInfo(id=manga_id, title="Unknown", description="", cover_url="",
                        authors=[], genres=[], status="unknown", source=self.source_name)
    
    def get_chapters(self, manga_id: str) -> List[Chapter]:
        return []
    
    def get_chapter_images(self, chapter_id: str) -> List[str]:
        return []


# MangaFire Scraper - Try enhanced version, fallback to basic
try:
    from sources.tachiyomi_all_mangafire_v1_4_16.python.mangafire_scraper import TachiyomiMangaFireScraper
    
    class MangaFireScraper(TachiyomiMangaFireScraper):
        """Enhanced MangaFire scraper with VRF tokens and image descrambling"""
        pass
    
    logger.info("Using enhanced Tachiyomi-based MangaFire scraper")

except (ImportError, Exception) as e:
    logger.warning(f"Enhanced MangaFire scraper not available: {e}. Using basic version.")
    
    # Basic fallback implementation (same logic as enhanced version)
    class MangaFireScraper(BaseMangaScraper):
        """Basic MangaFire scraper (limited functionality)"""
        
        BASE_URL = "https://mangafire.to"
        
        @property
        def source_name(self) -> str:
            return "MangaFire"
        
        def get_headers(self) -> Dict[str, str]:
            """Get headers - simplified to avoid anti-bot detection"""
            return {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        
        def search(self, query: str, page: int = 1) -> List[MangaInfo]:
            """
            Search using /type/manga endpoint (no VRF required).
            Supports direct URLs or search queries.
            """
            try:
                # Check if query is a direct URL
                if query.startswith('http'):
                    logger.info("Direct URL provided, fetching manga details")
                    return [self.get_manga_details(query)]
                
                url = f"{self.BASE_URL}/type/manga"
                params = {'page': page}
                if query:
                    params['keyword'] = query
                
                response = requests.get(url, params=params, headers=self.get_headers(), timeout=20)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                results = []
                
                # Use Tachiyomi selector
                for item in soup.select('.original.card-lg .unit .inner'):
                    try:
                        link = item.select_one('.info > a')
                        if not link:
                            continue
                        
                        manga_url = urljoin(self.BASE_URL, link.get('href', ''))
                        title = link.get_text(strip=True)
                        
                        img = item.select_one('img')
                        cover_url = img.get('src', '') if img else ""
                        if cover_url and not cover_url.startswith('http'):
                            cover_url = urljoin(self.BASE_URL, cover_url)
                        
                        results.append(MangaInfo(
                            id=manga_url,
                            title=title,
                            description="",
                            cover_url=cover_url,
                            authors=[],
                            genres=[],
                            status="unknown",
                            source=self.source_name
                        ))
                    except Exception as e:
                        logger.warning(f"Failed to parse manga item: {e}")
                        continue
                
                logger.info(f"MangaFire search returned {len(results)} results")
                return results
            except Exception as e:
                logger.error(f"MangaFire search failed: {e}")
                return []
        
        def get_manga_details(self, manga_id: str) -> MangaInfo:
            """Get manga details"""
            try:
                response = requests.get(manga_id, headers=self.get_headers(), timeout=20)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, 'html.parser')
                
                title_elem = soup.select_one('h1')
                title = title_elem.get_text(strip=True) if title_elem else "Unknown"
                
                return MangaInfo(
                    id=manga_id,
                    title=title,
                    description="",
                    cover_url="",
                    authors=[],
                    genres=[],
                    status="unknown",
                    source=self.source_name
                )
            except Exception as e:
                logger.error(f"Failed to get details: {e}")
                return MangaInfo(id=manga_id, title="Unknown", description="", cover_url="",
                               authors=[], genres=[], status="unknown", source=self.source_name)
        
        def get_chapters(self, manga_id: str) -> List[Chapter]:
            """Get chapters (basic implementation)"""
            logger.warning("MangaFire chapter listing requires enhanced scraper")
            return []
        
        def get_chapter_images(self, chapter_id: str) -> List[str]:
            """Get chapter images (not supported in basic version)"""
            logger.warning("MangaFire image extraction requires enhanced scraper with Playwright")
            return []
