# Manga Colorizer

Modern desktop application for colorizing black-and-white manga pages using **Manga Colorization v2** - a fast, non-diffusion colorizer with perfect text preservation.

## Features

- **Electron Desktop App** - Modern React-based UI with FastAPI Python backend
- **Manga Colorization v2 Engine**: 30-60 seconds per page with perfect text preservation
- **Single Image Mode** - Upload and colorize individual pages
- **Batch Processing** - Process hundreds of pages with drag-and-drop
- **Manga Browser** - Search and download from MangaFire
- **Manga Reader** - Read with version switcher (original/colored)
- **Chapter Selection** - Targeted colorization
- Original ink preservation to keep lineart crisp
- Optimized for Mac M2/M3 (MPS), CUDA GPU, or CPU

## Requirements

- Python 3.9 or higher
- Node.js 18+ and npm
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

3. Install Python dependencies:
```bash
pip install -r backend/requirements.txt
```

For Mac with Apple Silicon:
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r backend/requirements.txt
```

4. Install Playwright browsers (for manga downloading):
```bash
python -m playwright install chromium
```

5. Install Electron app dependencies:
```bash
cd electron-app
npm install
cd ..
```

## Usage

### Electron App (Recommended)

Run the application:
```bash
./start.sh
```

Or manually:
```bash
# Terminal 1: Start Python backend
source venv/bin/activate
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Start Electron app
cd electron-app
npm run dev
```

The app has 4 tabs:

#### 1. Single Image Tab
- Click "Choose Image" to select a manga page
- Adjust ink threshold and resolution settings
- Click "Colorize" to start (30-60 seconds)
- View side-by-side comparison
- Download the result

#### 2. Batch Processing Tab
- Drag-and-drop files or folders
- Configure global settings
- Monitor real-time progress
- View statistics and download results

#### 3. Manga Browser Tab
- Search manga from MangaFire
- View details and chapters
- Select chapters to download
- Track download progress

#### 4. Manga Reader Tab
- View your library grid
- Open and read manga
- Switch between original and colored versions
- Bookmark pages and track progress
- Keyboard shortcuts (Arrow keys, ESC, T, B)

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
├── backend/                      # Python backend
│   ├── api/                     # FastAPI application
│   │   ├── main.py              # Main API server
│   │   ├── dependencies.py      # Shared dependencies
│   │   └── routes/              # API endpoints
│   ├── core/                    # Core Python modules
│   │   ├── mcv2_engine.py       # Manga Colorization v2
│   │   ├── image_utils.py       # Image processing
│   │   ├── batch_processor.py   # Batch processing
│   │   ├── manga_library.py     # Library management
│   │   └── ...
│   ├── third_party/             # Manga-colorization-v2 code
│   ├── sources/                 # MangaFire scraper
│   └── requirements.txt         # Python dependencies
├── electron-app/                # Electron frontend
│   ├── src/                     # TypeScript/React code
│   │   ├── main/                # Electron main process
│   │   ├── preload/             # Preload scripts
│   │   └── renderer/            # React application
│   ├── package.json             # Node dependencies
│   └── README.md                # Electron app docs
├── library/                     # All manga storage
│   └── [Manga Title]/
│       ├── original/            # Downloaded originals
│       │   └── Ch_XX/           # Chapter folders
│       └── colored/             # Colorized versions
│           └── Ch_XX/           # Chapter folders
├── output/                      # Batch processing temp output
├── batch_colorize.py            # CLI batch tool
├── start.sh                     # Quick launcher
├── manga_data.json              # Library data
└── README.md                    # This file
```

## Configuration

Edit `backend/core/config.py` to adjust parameters:

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

**App won't start:**
- Ensure Python virtual environment is activated
- Check backend dependencies: `pip install -r backend/requirements.txt`
- Check Electron dependencies: `cd electron-app && npm install`
- Verify port 8000 is not in use: `lsof -i :8000`

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
- Reduce `max_side` setting (try 768)
- Ensure no other heavy applications are running
- Close browser tabs to free memory

**Text is blurred:**
- The ink preservation feature should prevent this
- Adjust `ink_threshold` in settings (default: 80, lower = preserve more)

**Reader not showing colored version:**
- Ensure manga was colorized after the latest update
- Colored chapters are in `output/<manga_name>/<chapter>/`
- Re-colorize if needed to get the correct output structure

## Development

See [`electron-app/README.md`](electron-app/README.md) for detailed development documentation.

## License

See LICENSE file for details.

## Credits

- Manga Colorization v2 by qweasdd
- Tachiyomi MangaFire extension (Java source for Python port)
- Playwright for browser automation
- Electron, React, FastAPI frameworks
