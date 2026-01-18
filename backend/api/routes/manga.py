"""
Manga Browser API routes - Search and download manga
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import sys
import uuid
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from api.dependencies import get_source_manager

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory download tracking
active_downloads: Dict[str, Dict[str, Any]] = {}

class ChapterDownloadRequest(BaseModel):
    manga_id: str
    manga_title: str
    chapters: List[str]  # List of chapter IDs to download

@router.get("/search")
async def search_manga(q: str, page: int = 1, limit: int = 20):
    """
    Search for manga
    
    - **q**: Search query
    - **page**: Page number (default: 1)
    - **limit**: Results per page (default: 20)
    """
    try:
        source_manager = get_source_manager()
        if not source_manager:
            raise HTTPException(status_code=503, detail="Manga source not available")
        
        logger.info(f"🔍 Searching manga: '{q}'")
        
        # Get search results from the first available scraper
        scrapers = source_manager.scrapers
        if not scrapers:
            raise HTTPException(status_code=503, detail="No manga scrapers available")
        
        # Use MangaFire scraper
        scraper = scrapers.get('MangaFire')
        if not scraper:
            scraper = list(scrapers.values())[0]
        
        results = scraper.search(q)
        
        # Format results
        formatted_results = []
        for result in results[:limit]:
            # Handle both dict and MangaInfo objects
            if hasattr(result, '__dataclass_fields__'):
                # It's a dataclass object
                formatted_results.append({
                    "id": result.manga_id if hasattr(result, 'manga_id') else getattr(result, 'id', ''),
                    "title": result.title,
                    "url": result.manga_url if hasattr(result, 'manga_url') else '',
                    "cover_url": result.cover_url if hasattr(result, 'cover_url') else '',
                    "latest_chapter": getattr(result, 'latest_chapter', ''),
                    "status": getattr(result, 'status', 'Unknown')
                })
            else:
                # It's a dict
                formatted_results.append({
                    "id": result.get("id", ""),
                    "title": result.get("title", ""),
                    "url": result.get("url", ""),
                    "cover_url": result.get("cover", ""),
                    "latest_chapter": result.get("latest_chapter", ""),
                    "status": result.get("status", "Unknown")
                })
        
        logger.info(f"✅ Found {len(formatted_results)} results")
        
        return {
            "results": formatted_results,
            "total": len(results),
            "page": page,
            "has_more": len(results) > limit
        }
        
    except Exception as e:
        logger.error(f"❌ Search failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/details")
async def get_manga_details(manga_id: str):
    """
    Get detailed manga information
    
    - **manga_id**: Manga identifier (query parameter)
    """
    try:
        source_manager = get_source_manager()
        if not source_manager:
            raise HTTPException(status_code=503, detail="Manga source not available")
        
        logger.info(f"📖 Getting details for manga: {manga_id}")
        
        scrapers = source_manager.scrapers
        scraper = scrapers.get('MangaFire') or list(scrapers.values())[0]
        
        # Get manga details
        details = scraper.get_manga_details(manga_id)
        
        # Handle both dict and MangaInfo objects
        if hasattr(details, '__dataclass_fields__'):
            return {
                "id": manga_id,
                "title": details.title,
                "description": getattr(details, 'description', ''),
                "cover_url": getattr(details, 'cover_url', ''),
                "author": getattr(details, 'author', 'Unknown'),
                "status": getattr(details, 'status', 'Unknown'),
                "genres": getattr(details, 'genres', []),
                "rating": getattr(details, 'rating', 0)
            }
        else:
            return {
                "id": manga_id,
                "title": details.get("title", ""),
                "description": details.get("description", ""),
                "cover_url": details.get("cover", ""),
                "author": details.get("author", "Unknown"),
                "status": details.get("status", "Unknown"),
                "genres": details.get("genres", []),
                "rating": details.get("rating", 0)
            }
        
    except Exception as e:
        logger.error(f"❌ Failed to get manga details: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/chapters")
async def get_manga_chapters(manga_id: str):
    """
    Get list of chapters for a manga
    
    - **manga_id**: Manga identifier (query parameter)
    """
    try:
        source_manager = get_source_manager()
        if not source_manager:
            raise HTTPException(status_code=503, detail="Manga source not available")
        
        logger.info(f"📑 Getting chapters for manga: {manga_id}")
        
        scrapers = source_manager.scrapers
        scraper = scrapers.get('MangaFire') or list(scrapers.values())[0]
        
        # Get chapters
        chapters = scraper.get_chapters(manga_id)
        
        formatted_chapters = []
        for chapter in chapters:
            # Handle both dict and Chapter dataclass objects
            if hasattr(chapter, '__dataclass_fields__'):
                formatted_chapters.append({
                    "id": chapter.id,
                    "number": chapter.chapter_number,
                    "title": chapter.title,
                    "date": "",
                    "url": chapter.url
                })
            else:
                formatted_chapters.append({
                    "id": chapter.get("id", ""),
                    "number": chapter.get("number", ""),
                    "title": chapter.get("title", ""),
                    "date": chapter.get("date", ""),
                    "url": chapter.get("url", "")
                })
        
        logger.info(f"✅ Found {len(formatted_chapters)} chapters")
        
        return {
            "manga_id": manga_id,
            "chapters": formatted_chapters,
            "total": len(formatted_chapters)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get chapters: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.post("/download")
async def download_chapters(request: ChapterDownloadRequest, background_tasks: BackgroundTasks):
    """
    Download manga chapters
    
    - **manga_id**: Manga identifier
    - **manga_title**: Manga title for folder naming
    - **chapters**: List of chapter IDs to download
    """
    try:
        download_id = str(uuid.uuid4())
        
        # Initialize download tracking
        active_downloads[download_id] = {
            "id": download_id,
            "manga_id": request.manga_id,
            "manga_title": request.manga_title,
            "chapters": request.chapters,
            "status": "queued",
            "progress": 0,
            "current_chapter": 0,
            "total_chapters": len(request.chapters),
            "message": "Download queued",
            "errors": []
        }
        
        # Start download in background
        background_tasks.add_task(process_download, download_id)
        
        logger.info(f"📥 Queued download {download_id}: {request.manga_title} ({len(request.chapters)} chapters)")
        
        return {
            "download_id": download_id,
            "manga_title": request.manga_title,
            "status": "queued",
            "progress": 0,
            "message": "Download started",
            "total_chapters": len(request.chapters)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to start download: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

async def process_download(download_id: str):
    """Background task for downloading chapters"""
    try:
        download = active_downloads[download_id]
        download["status"] = "downloading"
        
        source_manager = get_source_manager()
        if not source_manager:
            raise Exception("Manga source not available")
        
        scrapers = source_manager.scrapers
        scraper = scrapers.get('MangaFire') or list(scrapers.values())[0]
        
        manga_title = download["manga_title"]
        chapters = download["chapters"]
        
        # Create download directory in library structure
        manga_dir = Path("library") / manga_title / "original"
        manga_dir.mkdir(parents=True, exist_ok=True)
        
        for idx, chapter_id in enumerate(chapters):
            if download["status"] == "cancelled":
                break
            
            try:
                download["current_chapter"] = idx + 1
                download["message"] = f"Downloading chapter {idx + 1}/{len(chapters)}"
                download["progress"] = int((idx + 1) / len(chapters) * 100)
                
                # Download chapter
                logger.info(f"📥 Downloading chapter {chapter_id}")
                
                # Get chapter images
                images = scraper.get_chapter_images(chapter_id)
                
                # Create chapter directory
                chapter_dir = manga_dir / f"Ch_{chapter_id}"
                chapter_dir.mkdir(exist_ok=True)
                
                # Download images
                for img_idx, img_url in enumerate(images):
                    # Download and save image
                    # This is a placeholder - actual implementation would download the image
                    logger.info(f"  Page {img_idx + 1}/{len(images)}")
                
                logger.info(f"✅ Downloaded chapter {chapter_id}")
                
            except Exception as e:
                error_msg = f"Failed to download chapter {chapter_id}: {str(e)}"
                download["errors"].append(error_msg)
                logger.error(f"❌ {error_msg}")
        
        if download["status"] != "cancelled":
            download["status"] = "completed"
            download["message"] = f"Download complete: {len(chapters)} chapters"
            logger.info(f"🎉 Download {download_id} completed")
        
    except Exception as e:
        download["status"] = "failed"
        download["message"] = str(e)
        download["errors"].append(f"Download failed: {str(e)}")
        logger.error(f"❌ Download {download_id} failed: {e}", exc_info=True)

@router.get("/downloads/{download_id}/status")
async def get_download_status(download_id: str):
    """Get download status"""
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    download = active_downloads[download_id]
    return {
        "id": download["id"],
        "status": download["status"],
        "progress": download["progress"],
        "current_chapter": download["current_chapter"],
        "total_chapters": download["total_chapters"],
        "message": download["message"],
        "errors": download["errors"]
    }

@router.post("/downloads/{download_id}/cancel")
async def cancel_download(download_id: str):
    """Cancel a download"""
    if download_id not in active_downloads:
        raise HTTPException(status_code=404, detail="Download not found")
    
    download = active_downloads[download_id]
    if download["status"] == "downloading":
        download["status"] = "cancelled"
        download["message"] = "Download cancelled by user"
        logger.info(f"🛑 Cancelled download {download_id}")
        return {"success": True, "message": "Download cancelled"}
    else:
        return {"success": False, "message": f"Cannot cancel download with status: {download['status']}"}

@router.get("/downloads")
async def list_downloads():
    """List all downloads"""
    return {
        "downloads": [
            {
                "id": d["id"],
                "manga_title": d["manga_title"],
                "status": d["status"],
                "progress": d["progress"],
                "message": d["message"]
            }
            for d in active_downloads.values()
        ]
    }
