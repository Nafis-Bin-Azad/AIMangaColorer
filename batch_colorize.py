#!/usr/bin/env python3
"""
Batch Manga Colorization Script
Process entire folders quickly using Manga Colorization v2
"""
import argparse
from pathlib import Path
from tqdm import tqdm
from PIL import Image
import logging
import sys

# Add backend to path for imports
backend_dir = Path(__file__).parent / 'backend'
sys.path.insert(0, str(backend_dir))

from core.mcv2_engine import MangaColorizationV2Engine
from core.image_utils import ImageUtils
from core.config import MCV2_PARAMS

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Batch colorize manga pages using Manga Colorization v2",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Colorize folder
  python batch_colorize.py --input pages/ --output colored/
  
  # Adjust ink preservation threshold
  python batch_colorize.py --input pages/ --output colored/ --ink-threshold 60
        """
    )
    
    parser.add_argument("--input", required=True, help="Input folder with manga pages")
    parser.add_argument("--output", required=True, help="Output folder for colored pages")
    parser.add_argument("--ink-threshold", type=int, default=80,
                        help="Ink preservation threshold (0-255, lower=more ink)")
    parser.add_argument("--max-side", type=int, default=1024,
                        help="Maximum image dimension for processing")
    
    args = parser.parse_args()
    
    # Validate paths
    input_dir = Path(args.input)
    if not input_dir.exists():
        print(f"Error: Input directory '{input_dir}' does not exist")
        return 1
    
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all images
    extensions = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    images = [f for f in input_dir.iterdir() 
              if f.is_file() and f.suffix.lower() in extensions]
    
    if not images:
        print(f"No images found in '{input_dir}'")
        return 1
    
    print(f"Found {len(images)} images to colorize")
    print(f"Engine: Manga Colorization v2")
    print(f"Output: {output_dir}")
    print()
    
    # Load engine once (reused for all images)
    print("Loading Manga Colorization v2 Engine...")
    engine = MangaColorizationV2Engine()
    engine.ensure_weights()
    engine.load_model()
    print("Engine ready!")
    
    # Initialize utilities
    utils = ImageUtils()
    
    # Process all images
    successful = 0
    failed = 0
    
    for img_path in tqdm(images, desc="Colorizing pages"):
        try:
            # Load image
            img = Image.open(img_path).convert("RGB")
            
            # Preprocess
            processed, metadata = utils.preprocess(img, max_side=args.max_side)
            
            # Colorize
            colored = engine.colorize(
                processed,
                preserve_ink=True,
                ink_threshold=args.ink_threshold,
                size=MCV2_PARAMS["size"],
                denoise=MCV2_PARAMS["denoise"],
                denoise_sigma=MCV2_PARAMS["denoise_sigma"]
            )
            
            # Postprocess
            final = utils.postprocess(colored, metadata, restore_original_size=True)
            
            # Save
            output_path = output_dir / f"{img_path.stem}_colored.png"
            final.save(output_path, "PNG")
            
            successful += 1
            
        except Exception as e:
            logger.error(f"Failed to colorize {img_path.name}: {e}")
            failed += 1
            continue
    
    # Summary
    print()
    print("=" * 50)
    print(f"Batch colorization complete!")
    print(f"Successful: {successful}/{len(images)}")
    print(f"Failed: {failed}/{len(images)}")
    print(f"Output directory: {output_dir}")
    print("=" * 50)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    exit(main())
