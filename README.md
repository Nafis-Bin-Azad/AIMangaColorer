# Manga Colorizer

Desktop application for colorizing black-and-white manga pages using **Manga Colorization v2** - a fast, non-diffusion colorizer with perfect text preservation.

## Features

- **Manga Colorization v2 Engine**: 30-60 seconds per page with perfect text preservation
- Desktop GUI built with Tkinter (no web dependencies)
- **Batch processing mode** for colorizing hundreds of pages
- **Manga browser & downloader** with MangaFire integration
- **Manga reader** with version switcher (original/colored)
- **Chapter selection** for targeted colorization
- Original ink preservation to keep lineart crisp
- Optimized for Mac M2/M3 (MPS), CUDA GPU, or CPU

## Requirements

- Python 3.9 or higher
- Mac with M2/M3 chip (MPS), CUDA GPU, or CPU
- ~4GB RAM for colorization
- ~600MB disk for models (downloaded automatically on first run)

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

4. Install Playwright browsers (for manga downloading):
```bash
python -m playwright install chromium
```

## Usage

### GUI Mode

Run the application:
```bash
python manga_colorizer_gui.py
# Or use the launcher:
./run.sh
```

The GUI has 4 tabs:

#### 1. Single Image Tab
- Click "Browse..." to select a manga page (PNG, JPG, etc.)
- Click "Colorize" to start (30-60 seconds per page)
- First run downloads models (~600MB)
- View result and click "Save As..." to save

#### 2. Batch Mode Tab
- Add files, folders, or ZIP archives
- Click "Start Batch" to process everything
- Outputs to folder or ZIP file

#### 3. Manga Browser Tab
- Search and download manga from MangaFire
- Download chapters to the `downloads/` folder
- Select chapters to colorize
- Track colorization progress

#### 4. Reader Tab
- Read downloaded manga
- Switch between original and colored versions
- Colorize individual chapters from the reader
- Track reading progress with bookmarks

### Batch Command Line

Process entire folders quickly:

```bash
# Colorize entire folder
python batch_colorize.py --input pages/ --output colored/

# Adjust ink preservation (lower = preserve more dark pixels)
python batch_colorize.py --input pages/ --output colored/ --ink-threshold 60

# Process higher resolution
python batch_colorize.py --input pages/ --output colored/ --max-side 1280
```

**Batch Performance**: 100-200 pages/hour

## Project Structure

```
AIMangaColorer/
├── manga_colorizer_gui.py       # Main Tkinter GUI application
├── manga_reader.py               # Manga reader component
├── manga_library.py              # Library management
├── manga_downloader.py           # MangaFire downloader
├── manga_scrapers.py             # Manga source scrapers
├── mcv2_engine.py                # Manga Colorization v2 engine
├── image_utils.py                # Image processing utilities
├── batch_colorize.py             # Batch processing script
├── batch_processor.py            # Batch processing engine
├── config.py                     # Configuration constants
├── requirements.txt              # Python dependencies
├── run.sh                        # Quick launcher script
├── third_party/                  # Vendored manga-colorization-v2 code
│   └── manga_colorization_v2/
├── sources/                      # MangaFire scraper implementation
│   └── tachiyomi_all_mangafire_v1_4_16/
├── downloads/                    # Downloaded manga
├── output/                       # Colorized manga
└── README.md                     # This file
```

## Configuration

Edit `config.py` to adjust parameters:

**Manga Colorization v2 Engine**:
- `size`: Processing size (default: 576, must be divisible by 32)
- `ink_threshold`: Ink preservation (default: 80, lower = preserve more dark pixels)
- `denoise`: Enable denoising (default: True)
- `denoise_sigma`: Denoising strength (default: 25)

## Models Used

**Manga Colorization v2**:
- **Repository**: qweasdd/manga-colorization-v2
- **Weights**: Auto-downloaded from Google Drive (~600MB)
- **Speed**: 30-60 seconds per page
- **Method**: Non-diffusion GAN-based colorization
- **Text Preservation**: Perfect (never redraws text)

All models are downloaded automatically on first run.

## Performance & Memory

**Manga Colorization v2**:
- Speed: 30-60 seconds per page
- Memory: ~4GB RAM
- Batch: 100-200 pages/hour
- Text: Perfect preservation (never redrawn)
- Works on Mac MPS, CUDA, or CPU

## Troubleshooting

**Models not downloading:**
- Check internet connection
- Google Drive download may require manual approval on first run
- Models are cached in `~/.cache/manga_colorization_v2/`

**Manga download not working:**
- Ensure Playwright is installed: `python -m playwright install chromium`
- Check internet connection
- MangaFire may be temporarily down

**Slow performance:**
- First run downloads models and is slower
- Reduce `max_side` in config.py (try 768)
- Ensure no other heavy applications are running
- Close browser tabs to free memory

**Text is blurred:**
- The ink preservation feature should prevent this
- Adjust `ink_threshold` in config.py (default: 80, lower = preserve more)

**Reader not showing colored version:**
- Ensure manga was colorized after the latest update
- Colored chapters are in `output/<manga_name>/<chapter>/`
- Re-colorize if needed to get the correct output structure

## License

See LICENSE file for details.

## Credits

- Manga Colorization v2 by qweasdd
- Tachiyomi MangaFire extension (Java source for Python port)
- Playwright for browser automation
