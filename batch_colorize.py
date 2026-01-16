#!/usr/bin/env python3
"""
Batch Manga Colorization Script
Process entire folders quickly using manga-colorization-v2 or SD1.5
"""
import argparse
from pathlib import Path
from tqdm import tqdm
from PIL import Image
import logging

from mcv2_engine import MangaColorizationV2Engine
from sd_pipeline import SD15Pipeline
from image_utils import ImageUtils
from config import MCV2_PARAMS, SD15_PARAMS, DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Batch colorize manga pages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Colorize folder with fast engine
  python batch_colorize.py --input pages/ --output colored/
  
  # Use SD1.5 fallback
  python batch_colorize.py --input pages/ --output colored/ --engine sd15
  
  # Adjust ink preservation threshold
  python batch_colorize.py --input pages/ --output colored/ --ink-threshold 60
        """
    )
    
    parser.add_argument("--input", required=True, help="Input folder with manga pages")
    parser.add_argument("--output", required=True, help="Output folder for colored pages")
    parser.add_argument("--engine", default="mcv2", choices=["mcv2", "sd15"], 
                        help="Colorization engine (mcv2=fast, sd15=slow)")
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
    print(f"Engine: {args.engine.upper()}")
    print(f"Output: {output_dir}")
    print()
    
    # Load engine once (reused for all images)
    if args.engine == "mcv2":
        print("Loading Fast Colorizer (Manga v2)...")
        engine = MangaColorizationV2Engine()
        engine.ensure_weights()
        engine.load_model()
        print("Fast engine ready!")
    else:
        print("Loading SD1.5 engine (this may take a while)...")
        engine = SD15Pipeline()
        engine.load_models()
        print("SD1.5 engine ready!")
    
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
            
            # Colorize based on engine
            if args.engine == "mcv2":
                colored = engine.colorize(
                    processed,
                    preserve_ink=True,
                    ink_threshold=args.ink_threshold,
                    size=MCV2_PARAMS["size"],
                    denoise=MCV2_PARAMS["denoise"],
                    denoise_sigma=MCV2_PARAMS["denoise_sigma"]
                )
            else:
                # SD1.5 fallback
                lineart = utils.extract_lineart(processed)
                if lineart.size != processed.size:
                    lineart = lineart.resize(processed.size, Image.LANCZOS)
                
                text_mask = utils.detect_text_bubbles(processed)
                
                colored = engine.colorize(
                    image=processed,
                    control_image=lineart,
                    mask=text_mask,
                    prompt=DEFAULT_PROMPT,
                    negative_prompt=DEFAULT_NEGATIVE_PROMPT,
                    **SD15_PARAMS
                )
                
                colored = utils.preserve_ink(processed, colored, ink_threshold=110)
            
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
