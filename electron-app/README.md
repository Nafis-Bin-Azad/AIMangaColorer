# 🎨 Manga Colorizer - Electron Desktop App

A powerful desktop application for AI-powered manga colorization using the Manga Colorization V2 (MCV2) engine. Built with Electron, React, TypeScript, and FastAPI.

## ✨ Features

### 🖼️ Single Image Colorization
- Upload and colorize individual manga pages
- Adjustable ink threshold and resolution settings
- Real-time preview and side-by-side comparison
- Download colorized images

### 📦 Batch Processing
- Process multiple images or entire folders at once
- Drag-and-drop file upload
- Real-time progress tracking
- Batch configuration options
- Error reporting and statistics

### 📚 Manga Browser
- Search manga from MangaFire
- View manga details, cover, and chapters
- Select and download specific chapters
- Download queue with progress tracking
- Automatic chapter organization

### 📖 Manga Reader
- Beautiful library grid view
- Full-screen reading experience
- Keyboard navigation (Arrow keys, ESC)
- Bookmark pages
- Switch between original and colored versions
- Reading progress tracking
- Thumbnail sidebar
- Multiple fit modes (width, height, actual)

## 🏗️ Architecture

```
AIMangaColorer/
├── backend/                  # Python FastAPI backend
│   ├── api/
│   │   ├── main.py          # Main FastAPI app with WebSocket
│   │   ├── dependencies.py  # Shared dependencies
│   │   └── routes/          # Modular API routes
│   │       ├── colorize.py  # Single image endpoints
│   │       ├── batch.py     # Batch processing endpoints
│   │       ├── manga.py     # Manga browser endpoints
│   │       └── library.py   # Reader/library endpoints
│   ├── core/                # Core Python modules
│   │   ├── mcv2_engine.py   # MCV2 colorization engine
│   │   ├── image_utils.py   # Image processing utilities
│   │   ├── batch_processor.py
│   │   ├── manga_library.py
│   │   └── ...
│   ├── third_party/         # Third-party libraries
│   └── sources/             # Manga scrapers
├── electron-app/            # Electron + React frontend
│   ├── src/
│   │   ├── main/           # Electron main process
│   │   ├── preload/        # Preload scripts
│   │   └── renderer/       # React application
│   │       ├── components/ # UI components
│   │       ├── services/   # API client
│   │       └── styles/     # CSS styles
│   └── dist/               # Built files
├── downloads/              # Downloaded manga storage
├── output/                 # Colorized images output
└── models/                 # AI model weights

```

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Node.js 18+
- npm or yarn

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd AIMangaColorer
   ```

2. **Install Python dependencies**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r backend/requirements.txt
   ```

3. **Install Playwright (for MangaFire scraper)**
   ```bash
   playwright install chromium
   ```

4. **Install Node.js dependencies**
   ```bash
   cd electron-app
   npm install
   ```

### Running the Application

#### Option 1: Use the startup script (Recommended)
```bash
./start.sh
```

#### Option 2: Manual startup
```bash
# Terminal 1: Start Python backend
source venv/bin/activate
python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000

# Terminal 2: Start Electron app
cd electron-app
npm run dev
```

## 📖 Usage Guide

### Single Image Colorization
1. Click the "Single Image" tab
2. Click "📁 Choose Image" or drag-and-drop a manga page
3. Adjust settings:
   - **Ink Threshold**: Controls line art preservation (40-120)
   - **Max Resolution**: Processing resolution (512-1536px)
4. Click "🎨 Colorize" and wait ~30-60 seconds
5. Download the result with "💾 Download"

### Batch Processing
1. Click the "Batch Processing" tab
2. Drag-and-drop files/folders or use the file picker
3. Configure global settings
4. Click "🚀 Start Batch Processing"
5. Monitor progress in real-time
6. Download results when complete

### Manga Browser
1. Click the "Manga Browser" tab
2. Search for manga by title
3. Click on a manga card to view details
4. Select chapters to download
5. Click "📥 Download Selected"
6. Monitor download progress

### Manga Reader
1. Click the "Manga Reader" tab to view your library
2. Click on a manga to open it
3. Use keyboard shortcuts:
   - **Arrow Left/Right**: Navigate pages
   - **ESC**: Close reader
   - **T**: Toggle thumbnails
   - **B**: Bookmark current page
4. Switch between original and colored versions
5. Change fit mode for comfortable reading

## 🔧 API Endpoints

### Colorization
- `POST /api/colorize` - Colorize single image

### Batch Processing
- `POST /api/batch/create` - Create batch job
- `POST /api/batch/{id}/start` - Start processing
- `GET /api/batch/{id}/status` - Get status
- `POST /api/batch/{id}/cancel` - Cancel job

### Manga Browser
- `GET /api/manga/search?q={query}` - Search manga
- `GET /api/manga/{id}/details` - Get details
- `GET /api/manga/{id}/chapters` - List chapters
- `POST /api/manga/download` - Download chapters

### Library/Reader
- `GET /api/library/manga` - List library
- `GET /api/library/manga/{title}/chapters` - List chapters
- `GET /api/library/manga/{title}/chapter/{id}/pages` - Get pages
- `POST /api/library/progress` - Save progress
- `POST /api/library/bookmark` - Toggle bookmark
- `GET /api/library/history` - Reading history

### WebSocket
- `WS /ws` - Real-time updates

## 🎨 Color Scheme

The app uses a modern dark theme:
- Primary: `#6366f1` (Indigo)
- Background: `#0f172a` (Dark Blue)
- Secondary Background: `#1e293b`
- Success: `#22c55e` (Green)
- Error: `#ef4444` (Red)

## 🛠️ Development

### Project Structure

**Backend (Python/FastAPI)**
- FastAPI for REST API
- MCV2 engine for colorization
- Playwright for web scraping
- WebSocket support for real-time updates

**Frontend (Electron/React/TypeScript)**
- Electron for desktop app framework
- React for UI components
- TypeScript for type safety
- Vite for fast development and building

### Building for Production

```bash
cd electron-app
npm run build
npm run package  # Creates distributable
```

## 📝 Configuration

### MCV2 Engine Parameters
Located in `backend/core/config.py`:
- `preserve_ink`: Keep original line art
- `ink_threshold`: Line detection sensitivity
- `size`: Processing resolution
- `denoise`: Enable denoising
- `denoise_sigma`: Denoising strength

### API Configuration
- Default port: 8000
- Host: 127.0.0.1 (localhost)
- Timeout: 300 seconds (5 minutes)

## 🐛 Troubleshooting

### Python API won't start
```bash
# Check if port is in use
lsof -i :8000
# Kill existing process
lsof -ti:8000 | xargs kill -9
```

### MangaFire downloads fail
```bash
# Reinstall Playwright browsers
playwright install chromium
```

### Electron app won't connect to API
- Ensure Python API is running on port 8000
- Check firewall settings
- Verify backend/api/main.py is using correct path

### Model weights missing
- The MCV2 model will auto-download on first run
- Weights are stored in `third_party/manga_colorization_v2/networks/`

## 📄 License

See LICENSE file for details.

## 🙏 Credits

- **Manga Colorization V2**: Advanced AI colorization engine
- **MangaFire**: Manga source (via scraper)
- **Tachiyomi**: Inspiration for manga management

## 🚀 Roadmap

- [ ] Multi-language support
- [ ] Custom color palette selection
- [ ] Cloud sync for reading progress
- [ ] Plugin system for additional scrapers
- [ ] Batch colorization presets
- [ ] Advanced image editing tools

## 💬 Support

For issues, questions, or contributions, please open an issue on GitHub.

---

**Made with ❤️ and AI** 🎨
