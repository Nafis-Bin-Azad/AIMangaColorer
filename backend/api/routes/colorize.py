"""
Colorize API routes - Single image colorization
"""
from fastapi import APIRouter, File, UploadFile, Form, HTTPException
from PIL import Image
import io
import base64
import logging
import sys
from pathlib import Path

backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from api.dependencies import get_mcv2_engine, get_image_utils
from core.config import MCV2_PARAMS

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/colorize")
async def colorize_image(
    file: UploadFile = File(...),
    ink_threshold: int = Form(80),
    max_side: int = Form(1024)
):
    """
    Colorize a single manga page
    
    - **file**: Image file to colorize
    - **ink_threshold**: Ink preservation threshold (40-120)
    - **max_side**: Maximum dimension for processing (512-1536)
    """
    try:
        # Get engine and utils
        mcv2_engine = get_mcv2_engine()
        image_utils = get_image_utils()
        
        # Read uploaded image
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert("RGB")
        
        # Preprocess
        processed, metadata = image_utils.preprocess(image, max_side=max_side)
        
        # Colorize
        logger.info(f"Colorizing image: {file.filename}")
        colored = mcv2_engine.colorize(
            processed,
            preserve_ink=MCV2_PARAMS["preserve_ink"],
            ink_threshold=ink_threshold,
            size=MCV2_PARAMS["size"],
            denoise=MCV2_PARAMS["denoise"],
            denoise_sigma=MCV2_PARAMS["denoise_sigma"]
        )
        
        # Postprocess
        final = image_utils.postprocess(colored, metadata, restore_original_size=True)
        
        # Convert to base64
        buffered = io.BytesIO()
        final.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode()
        
        logger.info("✅ Colorization complete")
        
        return {
            "success": True,
            "image": f"data:image/png;base64,{img_str}",
            "original_size": metadata["original_size"],
            "processed_size": metadata["processed_size"],
            "filename": file.filename
        }
        
    except Exception as e:
        logger.error(f"❌ Colorization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail={
                "error": str(e),
                "type": type(e).__name__
            }
        )
