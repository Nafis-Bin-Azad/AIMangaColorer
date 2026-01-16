# Manga Colorizer

Simple desktop application for colorizing black-and-white manga pages with two engines: a **fast non-diffusion colorizer** (default) and **Stable Diffusion 1.5** (fallback).

## Features

- **Two colorization engines:**
  - **Fast (Manga v2)**: 30-60 seconds per page, preserves text perfectly
  - **SD1.5 (Fallback)**: 5-7 minutes per page, more flexible
- Desktop GUI built with Tkinter (no web dependencies)
- **Batch processing mode** for colorizing hundreds of pages
- Automatic text/bubble detection and protection
- Original ink preservation to keep lineart crisp
- Optimized for Mac M2 Pro (MPS) with low memory usage

## Requirements

- Python 3.9 or higher
- Mac with M2/M3 chip (MPS), CUDA GPU, or CPU
- **Fast Engine (MCV2)**: ~4GB RAM, ~600MB disk for models
- **SD1.5 Engine**: ~8GB RAM, ~2GB disk for models
- Models are downloaded automatically on first run

## Installation

1. Clone this repository or download the files

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

For Mac with Apple Silicon:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

## Usage

### GUI Mode (Single Images)

1. Run the application:
```bash
python manga_colorizer_gui.py
# Or use the launcher:
./run.sh
```

2. Select engine from dropdown:
   - **Fast (Manga v2)** - Default, 30-60 seconds, perfect text preservation
   - **SD1.5 (Slow, fallback)** - 5-7 minutes, more flexible

3. Click "Browse..." to select a manga page (PNG, JPG, etc.)

4. Click "Colorize" to start
   - First run downloads models (~600MB for Fast, ~2GB for SD1.5)
   - Fast engine: 30-60 seconds per page
   - SD1.5 engine: 5-7 minutes per page

5. View the result and click "Save As..." to save
   - Output is also automatically saved to the `output/` folder

### Batch Mode (Multiple Images)

Process entire folders quickly:

```bash
# Colorize entire folder with fast engine (default)
python batch_colorize.py --input pages/ --output colored/

# Use SD1.5 fallback
python batch_colorize.py --input pages/ --output colored/ --engine sd15

# Adjust ink preservation (lower = preserve more dark pixels)
python batch_colorize.py --input pages/ --output colored/ --ink-threshold 60

# Process higher resolution
python batch_colorize.py --input pages/ --output colored/ --max-side 1280
```

**Batch Performance:**
- Fast engine: 100-200 pages/hour
- SD1.5 engine: 10-15 pages/hour

## Project Structure

```
AIMangaColorer/
├── manga_colorizer_gui.py       # Main Tkinter GUI application
├── mcv2_engine.py                # Fast manga colorization v2 engine
├── sd_pipeline.py                # SD1.5 + ControlNet (fallback)
├── image_utils.py                # Image processing utilities
├── batch_colorize.py             # Batch processing script
├── config.py                     # Configuration constants
├── requirements.txt              # Python dependencies
├── run.sh                        # Quick launcher script
├── third_party/                  # Vendored manga-colorization-v2 code
│   └── manga_colorization_v2/
├── output/                       # Default output directory
└── README.md                     # This file
```

## Configuration

Edit `config.py` to adjust parameters:

**Fast Engine (MCV2)**:
- `size`: Processing size (default: 576, must be divisible by 32)
- `ink_threshold`: Ink preservation (default: 80, lower = preserve more dark pixels)
- `denoise`: Enable denoising (default: True)
- `denoise_sigma`: Denoising strength (default: 25)

**SD1.5 Engine (Fallback)**:
- `max_side`: Image resolution (default: 640)
- `steps`: Inference steps (default: 18, lower = faster)
- `guidance_scale`: CFG scale (default: 7.5)
- `strength`: Denoise strength (default: 0.85)

## Models Used

**Fast Engine (Manga Colorization v2)**:
- **Repository**: qweasdd/manga-colorization-v2
- **Weights**: Auto-downloaded from Google Drive (~600MB)
- **Speed**: 30-60 seconds per page
- **Method**: Non-diffusion GAN-based colorization

**SD1.5 Engine (Fallback)**:
- **Base Model**: `stablediffusionapi/anything-v5` (anime-focused SD1.5)
- **ControlNet**: `lllyasviel/control_v11p_sd15s2_lineart_anime`
- **Lineart Detector**: LineartAnimeDetector from controlnet-aux
- **Speed**: 5-7 minutes per page
- **Method**: Diffusion-based with lineart control

All models are downloaded automatically on first run.

## Performance & Memory

**Fast Engine (MCV2) - Recommended**:
- Speed: 30-60 seconds per page
- Memory: ~4GB RAM
- Batch: 100-200 pages/hour
- Text: Perfect preservation (never redrawn)

**SD1.5 Engine - Fallback**:
- Speed: 5-7 minutes per page
- Memory: ~8GB RAM (includes optimizations for Mac MPS)
- Batch: 10-15 pages/hour
- Text: Preserved via ink overlay

SD1.5 optimizations for Mac MPS:
- Attention slicing (reduces memory usage)
- VAE slicing (processes images in tiles)
- VAE float32 upcast (prevents black output on MPS)
- MPS cache clearing after each generation

If you encounter issues:
- **Use Fast engine (MCV2)** - solves most problems
- For SD1.5: reduce `max_side` in config.py (try 512)
- Close other applications

## Troubleshooting

**Models not downloading:**
- Check internet connection
- Ensure HuggingFace is accessible
- Try running with `HF_HUB_OFFLINE=0` environment variable

**Black output images:**
- Ensure you're using the latest version
- VAE is automatically upcast to float32 on MPS

**Slow performance:**
- First run downloads models and is slower
- Reduce `max_side` or `steps` in `config.py`
- Ensure no other heavy applications are running

**Text is blurred:**
- The ink preservation feature should prevent this
- Adjust `ink_threshold` in image_utils.py if needed (default: 110)

## License

See LICENSE file for details.

## Credits

- Stable Diffusion by Stability AI
- ControlNet by Lvmin Zhang
- Anime ControlNet models by lllyasviel
- Anything v5 model by stablediffusionapi
