"""
Batch Processing API routes
"""
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from pathlib import Path
import uuid
import asyncio
import logging
import sys

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from api.dependencies import get_mcv2_engine, get_image_utils
from core.batch_processor import BatchProcessor
from core.config import MCV2_PARAMS
from PIL import Image

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory batch job storage
batch_jobs: Dict[str, Dict[str, Any]] = {}

class BatchItem(BaseModel):
    id: Optional[str] = None  # Item identifier
    name: Optional[str] = None  # Display name
    type: Optional[str] = 'file'  # 'file', 'folder', 'zip'
    path: str  # File or folder path
    manga_title: Optional[str] = None  # For saving to library structure
    chapter_id: Optional[str] = None   # For saving to library structure

class BatchCreateRequest(BaseModel):
    items: List[BatchItem]
    ink_threshold: int = 80
    max_side: int = 1024
    output_format: str = 'folder'  # 'folder' or 'zip'

class BatchStatus(BaseModel):
    id: str
    status: str
    progress: int
    current: int
    total: int
    message: str
    errors: List[str] = []

@router.post("/create")
async def create_batch(request: BatchCreateRequest):
    """
    Create a new batch processing job
    
    - **items**: List of files/folders to process
    - **ink_threshold**: Global ink threshold
    - **max_side**: Processing resolution
    - **output_format**: Output as 'folder' or 'zip'
    """
    try:
        batch_id = str(uuid.uuid4())
        
        # Count total images
        total_images = 0
        for item in request.items:
            item_path = Path(item.path)
            if item.type == 'file' and item_path.exists():
                total_images += 1
            elif item.type == 'folder' and item_path.exists():
                extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
                total_images += len([f for f in item_path.rglob('*') 
                                    if f.suffix.lower() in extensions])
        
        # Initialize job
        batch_jobs[batch_id] = {
            "id": batch_id,
            "status": "created",
            "progress": 0,
            "current": 0,
            "total": total_images,
            "message": "Batch job created",
            "items": [item.dict() for item in request.items],
            "settings": {
                "ink_threshold": request.ink_threshold,
                "max_side": request.max_side,
                "output_format": request.output_format
            },
            "errors": [],
            "results": []
        }
        
        logger.info(f"📦 Created batch job {batch_id} with {total_images} images")
        
        return {"batch_id": batch_id, "total_images": total_images}
        
    except Exception as e:
        logger.error(f"❌ Failed to create batch: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )

@router.post("/{batch_id}/start")
async def start_batch(batch_id: str, background_tasks: BackgroundTasks):
    """
    Start processing a batch job
    """
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    if batch_jobs[batch_id]["status"] in ["processing", "completed"]:
        raise HTTPException(status_code=400, detail=f"Batch is already {batch_jobs[batch_id]['status']}")
    
    batch_jobs[batch_id]["status"] = "processing"
    batch_jobs[batch_id]["message"] = "Starting batch processing..."
    
    background_tasks.add_task(process_batch, batch_id)
    
    logger.info(f"🚀 Started batch job {batch_id}")
    
    return {"success": True, "message": "Batch processing started"}

async def process_batch(batch_id: str):
    """Background task for batch processing"""
    try:
        job = batch_jobs[batch_id]
        mcv2_engine = get_mcv2_engine()
        image_utils = get_image_utils()
        
        settings = job["settings"]
        items = job["items"]
        
        # Collect all image paths
        all_images = []
        for item in items:
            item_path = Path(item["path"])
            if item["type"] == "file" and item_path.exists():
                all_images.append(item_path)
            elif item["type"] == "folder" and item_path.exists():
                extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp'}
                all_images.extend([f for f in item_path.rglob('*') 
                                  if f.suffix.lower() in extensions])
        
        # Determine output directory based on metadata
        # If manga_title and chapter_id are provided, save to library structure
        first_item = items[0] if items else {}
        manga_title = first_item.get("manga_title")
        chapter_id = first_item.get("chapter_id")
        
        if manga_title and chapter_id:
            # Save to library structure
            output_dir = Path("library") / manga_title / "colored" / chapter_id
            logger.info(f"📚 Saving to library: {output_dir}")
        else:
            # Save to regular output folder
            output_dir = Path("output") / f"batch_{batch_id}"
            logger.info(f"📁 Saving to output: {output_dir}")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Process each image
        for idx, img_path in enumerate(all_images):
            if job["status"] == "cancelled":
                break
                
            try:
                job["current"] = idx + 1
                job["message"] = f"Processing {img_path.name}..."
                job["progress"] = int((idx + 1) / len(all_images) * 100)
                
                # Load and process image
                img = Image.open(img_path).convert("RGB")
                processed, metadata = image_utils.preprocess(img, max_side=settings["max_side"])
                
                # Colorize
                colored = mcv2_engine.colorize(
                    processed,
                    preserve_ink=MCV2_PARAMS["preserve_ink"],
                    ink_threshold=settings["ink_threshold"],
                    size=MCV2_PARAMS["size"],
                    denoise=MCV2_PARAMS["denoise"],
                    denoise_sigma=MCV2_PARAMS["denoise_sigma"]
                )
                
                # Postprocess
                final = image_utils.postprocess(colored, metadata, restore_original_size=True)
                
                # Save result - maintain original filename but change to PNG
                if manga_title and chapter_id:
                    # Keep original filename for library structure
                    output_path = output_dir / f"{img_path.stem}.png"
                else:
                    # Add _colored suffix for regular output
                    output_path = output_dir / f"{img_path.stem}_colored.png"
                
                final.save(output_path, "PNG")
                
                job["results"].append({
                    "input": str(img_path),
                    "output": str(output_path),
                    "success": True
                })
                
                logger.info(f"✅ Processed {idx + 1}/{len(all_images)}: {img_path.name}")
                
            except Exception as e:
                error_msg = f"Failed to process {img_path.name}: {str(e)}"
                job["errors"].append(error_msg)
                job["results"].append({
                    "input": str(img_path),
                    "error": str(e),
                    "success": False
                })
                logger.error(f"❌ {error_msg}")
        
        if job["status"] != "cancelled":
            job["status"] = "completed"
            job["message"] = f"Completed {len([r for r in job['results'] if r['success']])}/{len(all_images)} images"
            logger.info(f"🎉 Batch {batch_id} completed")
        
    except Exception as e:
        job["status"] = "failed"
        job["message"] = str(e)
        job["errors"].append(f"Batch processing failed: {str(e)}")
        logger.error(f"❌ Batch {batch_id} failed: {e}", exc_info=True)

@router.get("/{batch_id}/status")
async def get_batch_status(batch_id: str):
    """Get batch job status"""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    job = batch_jobs[batch_id]
    return {
        "id": job["id"],
        "status": job["status"],
        "progress": job["progress"],
        "current": job["current"],
        "total": job["total"],
        "message": job["message"],
        "errors": job["errors"]
    }

@router.get("/{batch_id}/results")
async def get_batch_results(batch_id: str):
    """Get detailed batch results"""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    job = batch_jobs[batch_id]
    return {
        "id": batch_id,
        "status": job["status"],
        "results": job["results"],
        "successful": len([r for r in job["results"] if r.get("success")]),
        "failed": len([r for r in job["results"] if not r.get("success")]),
        "errors": job["errors"]
    }

@router.post("/{batch_id}/cancel")
async def cancel_batch(batch_id: str):
    """Cancel a running batch job"""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    job = batch_jobs[batch_id]
    if job["status"] == "processing":
        job["status"] = "cancelled"
        job["message"] = "Batch processing cancelled by user"
        logger.info(f"🛑 Cancelled batch {batch_id}")
        return {"success": True, "message": "Batch cancelled"}
    else:
        return {"success": False, "message": f"Cannot cancel batch with status: {job['status']}"}

@router.delete("/{batch_id}")
async def delete_batch(batch_id: str):
    """Delete a batch job"""
    if batch_id not in batch_jobs:
        raise HTTPException(status_code=404, detail="Batch job not found")
    
    del batch_jobs[batch_id]
    logger.info(f"🗑️  Deleted batch {batch_id}")
    return {"success": True, "message": "Batch deleted"}

@router.get("/")
async def list_batches():
    """List all batch jobs"""
    return {
        "batches": [
            {
                "id": job["id"],
                "status": job["status"],
                "progress": job["progress"],
                "total": job["total"],
                "message": job["message"]
            }
            for job in batch_jobs.values()
        ]
    }
