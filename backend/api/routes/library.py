"""
Library and Reader API routes
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from api.dependencies import get_manga_library

logger = logging.getLogger(__name__)
router = APIRouter()

class ProgressUpdate(BaseModel):
    manga: str
    chapter: str
    page: int
    total_pages: int = 0

class BookmarkRequest(BaseModel):
    manga: str
    chapter: str
    page: int

@router.get("/manga")
async def list_manga():
    """Get list of all downloaded manga"""
    try:
        library = get_manga_library()
        manga_list = library.scan_library()
        
        formatted_manga = []
        for manga in manga_list:
            # Get progress info
            progress = library.progress.get(manga.title, {})
            
            formatted_manga.append({
                "title": manga.title,
                "path": str(manga.path),
                "chapters": manga.chapters,
                "total_chapters": manga.total_chapters,
                "last_read": manga.last_read,
                "progress": len(progress),
                "has_cover": (manga.cover_path.exists() if manga.cover_path else False)
            })
        
        logger.info(f"📚 Listed {len(formatted_manga)} manga")
        
        return {
            "manga": formatted_manga,
            "total": len(formatted_manga)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to list manga: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/manga/{manga_title}/chapters")
async def list_chapters(manga_title: str):
    """Get list of chapters for a manga"""
    try:
        library = get_manga_library()
        manga_path = library.library_dir / manga_title / "original"
        
        if not manga_path.exists():
            raise HTTPException(status_code=404, detail="Manga not found")
        
        # Get chapters
        chapters = sorted([
            d.name for d in manga_path.iterdir()
            if d.is_dir() and d.name.startswith('Ch_')
        ])
        
        formatted_chapters = []
        for chapter in chapters:
            chapter_path = manga_path / chapter
            
            # Count pages
            extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
            pages = sorted([f for f in chapter_path.iterdir() 
                           if f.suffix.lower() in extensions])
            
            # Check if colored version exists
            has_colored = library.has_colored_version(manga_title, chapter)
            
            # Get progress
            progress = library.progress.get(manga_title, {}).get(chapter)
            
            formatted_chapters.append({
                "id": chapter,
                "name": chapter,
                "pages": len(pages),
                "has_colored": has_colored,
                "last_page": progress.page if progress else 0,
                "last_read": progress.last_read if progress else None  # Already a string
            })
        
        logger.info(f"📑 Listed {len(formatted_chapters)} chapters for {manga_title}")
        
        return {
            "manga_title": manga_title,
            "chapters": formatted_chapters,
            "total": len(formatted_chapters)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to list chapters: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/manga/{manga_title}/chapter/{chapter_id}/pages")
async def get_chapter_pages(manga_title: str, chapter_id: str, colored: bool = False):
    """Get list of page URLs for a chapter"""
    try:
        library = get_manga_library()
        
        # Get pages
        pages = library.get_chapter_pages(manga_title, chapter_id, use_colored=colored)
        
        if not pages:
            raise HTTPException(status_code=404, detail="No pages found")
        
        # Convert paths to API URLs
        page_urls = []
        for idx, page_path in enumerate(pages):
            page_urls.append({
                "index": idx,
                "url": f"/api/library/page?path={str(page_path)}",
                "filename": page_path.name
            })
        
        logger.info(f"📄 Retrieved {len(page_urls)} pages for {manga_title}/{chapter_id} (colored: {colored})")
        
        return {
            "manga_title": manga_title,
            "chapter_id": chapter_id,
            "is_colored": colored,
            "pages": page_urls,
            "total": len(page_urls)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to get pages: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/page")
async def serve_page(path: str):
    """Serve a manga page image"""
    try:
        page_path = Path(path)
        
        if not page_path.exists():
            raise HTTPException(status_code=404, detail="Page not found")
        
        # Security check - ensure path is within allowed directories
        allowed_dirs = [Path("library"), Path("output")]
        if not any(page_path.is_relative_to(d) for d in allowed_dirs if d.exists()):
            raise HTTPException(status_code=403, detail="Access denied")
        
        return FileResponse(page_path)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to serve page: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.post("/progress")
async def save_progress(update: ProgressUpdate):
    """Save reading progress"""
    try:
        library = get_manga_library()
        
        library.save_progress(
            update.manga,
            update.chapter,
            update.page,
            total_pages=update.total_pages or 100
        )
        
        logger.info(f"💾 Saved progress: {update.manga}/{update.chapter} page {update.page}")
        
        return {"success": True, "message": "Progress saved"}
        
    except Exception as e:
        logger.error(f"❌ Failed to save progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/progress/{manga_title}")
async def get_progress(manga_title: str):
    """Get reading progress for a manga"""
    try:
        library = get_manga_library()
        
        progress = library.progress.get(manga_title, {})
        
        formatted_progress = []
        for chapter, prog in progress.items():
            formatted_progress.append({
                "chapter": chapter,
                "page": prog.page,
                "total_pages": prog.total_pages,
                "percentage": int((prog.page / prog.total_pages * 100)) if prog.total_pages > 0 else 0,
                "last_read": prog.last_read.isoformat()
            })
        
        return {
            "manga_title": manga_title,
            "progress": formatted_progress,
            "total_chapters": len(formatted_progress)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get progress: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.post("/bookmark")
async def toggle_bookmark(request: BookmarkRequest):
    """Toggle bookmark for a page"""
    try:
        library = get_manga_library()
        
        bookmarks = library.get_bookmarks(request.manga, request.chapter)
        
        if request.page in bookmarks:
            library.remove_bookmark(request.manga, request.chapter, request.page)
            bookmarked = False
            logger.info(f"🔖 Removed bookmark: {request.manga}/{request.chapter} page {request.page}")
        else:
            library.add_bookmark(request.manga, request.chapter, request.page)
            bookmarked = True
            logger.info(f"🔖 Added bookmark: {request.manga}/{request.chapter} page {request.page}")
        
        return {
            "success": True,
            "bookmarked": bookmarked
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to toggle bookmark: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/bookmarks/{manga_title}")
async def get_bookmarks(manga_title: str, chapter: Optional[str] = None):
    """Get bookmarks for a manga or specific chapter"""
    try:
        library = get_manga_library()
        
        if chapter:
            bookmarks = library.get_bookmarks(manga_title, chapter)
            return {
                "manga_title": manga_title,
                "chapter": chapter,
                "bookmarks": list(bookmarks)
            }
        else:
            # Get all bookmarks for the manga
            all_bookmarks = library.bookmarks.get(manga_title, {})
            formatted = []
            for chap, pages in all_bookmarks.items():
                formatted.append({
                    "chapter": chap,
                    "pages": list(pages)
                })
            
            return {
                "manga_title": manga_title,
                "bookmarks": formatted
            }
        
    except Exception as e:
        logger.error(f"❌ Failed to get bookmarks: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/history")
async def get_history(limit: int = 20):
    """Get reading history"""
    try:
        library = get_manga_library()
        
        # Get recent reads from history
        history = library.history[-limit:] if len(library.history) > limit else library.history
        history.reverse()  # Most recent first
        
        formatted_history = []
        for entry in history:
            formatted_history.append({
                "manga": entry.manga,
                "chapter": entry.chapter,
                "timestamp": entry.timestamp.isoformat()
            })
        
        return {
            "history": formatted_history,
            "total": len(library.history)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get history: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.get("/stats")
async def get_library_stats():
    """Get library statistics"""
    try:
        library = get_manga_library()
        
        manga_list = library.scan_library()
        total_chapters = sum(len(m.chapters) for m in manga_list)
        
        # Count total pages
        total_pages = 0
        for manga in manga_list:
            manga_path = Path(manga.path)
            original_path = manga_path / "original"
            if original_path.exists():
                for chapter_dir in original_path.iterdir():
                    if chapter_dir.is_dir() and chapter_dir.name.startswith('Ch_'):
                        extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
                        pages = [f for f in chapter_dir.iterdir() if f.suffix.lower() in extensions]
                        total_pages += len(pages)
        
        return {
            "total_manga": len(manga_list),
            "total_chapters": total_chapters,
            "total_pages": total_pages,
            "manga_in_progress": len(library.progress),
            "total_bookmarks": sum(len(chapters) for chapters in library.bookmarks.values()),
            "history_entries": len(library.history)
        }
        
    except Exception as e:
        logger.error(f"❌ Failed to get stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )
