# Manga Colorizer

AI-powered manga colorization tool using Stable Diffusion and ControlNet. Automatically colorizes black-and-white manga pages while preserving line art and protecting text regions.

## Features

- **Automatic Colorization**: Uses Stable Diffusion with ControlNet for high-quality manga colorization
- **Text Protection**: Automatically detects and preserves speech bubbles and text regions
- **Batch Processing**: Process single images or entire ZIP archives
- **Multiple Interfaces**: 
  - Modern Electron desktop GUI
  - Powerful command-line interface
- **Apple Silicon Optimized**: Native MPS (Metal Performance Shaders) support for M1/M2/M3 Macs
- **Customizable**: Adjust prompts, models, and generation parameters
- **Local & Offline**: Runs completely locally with no API costs

## Requirements

### System Requirements
- macOS 12.0+ (Monterey or later)
- Apple Silicon (M1/M2/M3) or Intel Mac
- 16GB RAM recommended (8GB minimum)
- 10GB free disk space for models

### Software Requirements
- Python 3.10 or higher
- Node.js 18+ (for GUI)
- Git

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd AIMangaColorer
```

### 2. Create Python Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On macOS/Linux
```

### 3. Install PyTorch with MPS Support

For Apple Silicon Macs:
```bash
pip install torch torchvision torchaudio
```

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Install Node.js Dependencies (for GUI)

```bash
npm install
```

### 6. Verify Installation

```bash
python cli/cli.py --help
```

## Quick Start

### Using the CLI

**Colorize a single image:**
```bash
python cli/cli.py colorize input.png
```

**Colorize a ZIP of manga pages:**
```bash
python cli/cli.py colorize manga_chapter.zip --output ./colored
```

**Use a different model:**
```bash
python cli/cli.py colorize input.png --model meinamix
```

**Custom prompt:**
```bash
python cli/cli.py colorize input.png --prompt "vibrant colors, high contrast"
```

### Using the GUI

**Start the application:**
```bash
npm start
```

The Electron app will launch automatically and start the Python backend server.

## Usage Guide

### Command-Line Interface

```bash
python cli/cli.py colorize [OPTIONS] INPUT_PATH
```

**Options:**
- `--output, -o`: Output directory (default: ./output)
- `--model, -m`: Model to use (default: anythingv5)
- `--prompt, -p`: Custom prompt for colorization
- `--negative-prompt, -n`: Custom negative prompt
- `--denoise, -d`: Denoising strength 0.3-0.5 (default: 0.4)
- `--steps, -s`: Number of inference steps (default: 25)
- `--guidance, -g`: Guidance scale (default: 8.0)
- `--seed`: Random seed for reproducibility
- `--zip`: Create output ZIP file
- `--no-text-protection`: Disable text detection
- `--comparison`: Save before/after comparison
- `--verbose, -v`: Verbose output

**Examples:**

```bash
# Basic colorization
python cli/cli.py colorize page.png

# Batch with custom settings
python cli/cli.py colorize chapter.zip \
  --model meinamix \
  --steps 30 \
  --denoise 0.45 \
  --zip

# High quality with reproducibility
python cli/cli.py colorize input.png \
  --steps 35 \
  --guidance 9.0 \
  --seed 42 \
  --comparison

# Without text protection (faster)
python cli/cli.py colorize page.png --no-text-protection
```

**List available models:**
```bash
python cli/cli.py list-models
```

**Download a model:**
```bash
python cli/cli.py download-model meinamix
```

**Start server only:**
```bash
python cli/cli.py server
```

### Desktop GUI

1. **Launch the app:**
   ```bash
   npm start
   ```

2. **Upload files:**
   - Drag and drop an image or ZIP file
   - Or click "Browse Files" to select

3. **Configure settings:**
   - Select model from dropdown
   - Customize prompts
   - Adjust advanced settings (steps, guidance, etc.)
   - Toggle text protection

4. **Start colorization:**
   - Click "Start Colorization"
   - Monitor progress in real-time
   - View results in the preview gallery

5. **Access outputs:**
   - Files saved to `output/` directory
   - Click "Open Output Folder" for quick access

## Available Models

| Model | Description | Best For |
|-------|-------------|----------|
| **anythingv5** | Versatile anime model | General manga colorization |
| **meinamix** | High-quality anime style | Detailed character art |
| **abyssorangemix** | Vibrant colors | Action scenes, fantasy |

### Adding Custom Models

Place downloaded models in the `models/` directory:

```
models/
├── your-custom-model/
│   ├── model_index.json
│   ├── vae/
│   ├── text_encoder/
│   └── ...
```

Or use the download command:
```bash
python cli/cli.py download-model custom-model --model-id "huggingface/model-id"
```

## Configuration

### Default Prompt

The default colorization prompt is optimized for manga:

```
full color manga page, anime style coloring, clean lineart preserved,
soft cel shading, consistent colors, detailed lighting, vibrant but natural tones
```

### Default Negative Prompt

```
blurry, repainting lines, messy colors, color bleeding, oversaturated,
artifacts, low quality, jpeg artifacts, text recoloring, speech bubble coloring,
monochrome
```

### Parameters

- **Denoise Strength** (0.3-0.5): Lower values preserve more of the original lineart
- **Guidance Scale** (7-9): Higher values follow the prompt more closely
- **Steps** (20-30): More steps = higher quality but slower
- **ControlNet Scale** (1.0): How strongly to condition on lineart

## Technical Details

### Architecture

The application uses a multi-layer architecture:

1. **Frontend Layer**: Electron GUI or CLI
2. **API Layer**: Flask REST API with WebSocket
3. **Processing Layer**: 
   - Model Manager (loading and caching)
   - Image Processor (preprocessing/postprocessing)
   - ControlNet Processor (lineart extraction)
   - Text Detector (speech bubble detection)
   - Batch Processor (ZIP handling)
4. **AI Layer**: Stable Diffusion + ControlNet pipeline

### Text Detection

The text detector uses:
- OpenCV contour detection for speech bubbles
- Morphological operations for text regions
- Binary masking to protect detected areas
- The colorization composites protected regions from the original image

### MPS Optimization

For Apple Silicon Macs, the app uses:
- Metal Performance Shaders (MPS) for GPU acceleration
- Attention slicing for memory efficiency
- Float16 precision for faster inference

## Project Structure

```
AIMangaColorer/
├── backend/              # Python backend
│   ├── colorizer.py      # Main orchestrator
│   ├── pipeline.py       # SD + ControlNet pipeline
│   ├── model_manager.py  # Model loading/management
│   ├── image_processor.py
│   ├── text_detector.py
│   ├── controlnet_processor.py
│   ├── batch_processor.py
│   ├── server.py         # Flask API
│   └── config.py
├── cli/                  # Command-line interface
│   └── cli.py
├── gui/                  # Electron desktop app
│   ├── main.js           # Main process
│   ├── preload.js        # IPC bridge
│   ├── renderer.js       # UI logic
│   ├── index.html
│   └── styles.css
├── models/               # Local model storage
├── output/               # Colorized outputs
├── tests/                # Unit tests
├── requirements.txt
├── package.json
└── README.md
```

## Troubleshooting

### Models not downloading

**Issue**: Models fail to download from HuggingFace

**Solution**:
- Check internet connection
- Manually download models and place in `models/` directory
- Set HuggingFace token if using private models

### Out of memory errors

**Issue**: Process killed due to insufficient memory

**Solution**:
- Reduce image resolution (automatically handled)
- Process fewer images at once
- Lower `num_inference_steps`
- Enable attention slicing (enabled by default)

### MPS errors on Apple Silicon

**Issue**: MPS-related errors on M1/M2/M3

**Solution**:
- Update to latest macOS version
- Update PyTorch: `pip install --upgrade torch`
- Fall back to CPU: Set `device="cpu"` in config.py

### Text regions being colorized

**Issue**: Text gets colorized despite protection

**Solution**:
- Text detection is probabilistic
- Increase padding in config
- Adjust detection sensitivity
- Use `--no-text-protection` and manually mask if needed

### Electron app won't start

**Issue**: GUI fails to launch

**Solution**:
- Ensure Node.js 18+ installed
- Run `npm install` again
- Check Python server starts: `python backend/server.py`
- Check logs in Console.app

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_image_processor.py

# With coverage
python -m pytest --cov=backend tests/
```

### Development Mode

Enable debug mode in Electron:
```bash
NODE_ENV=development npm start
```

Enable Flask debug mode:
```python
# In backend/config.py
FLASK_DEBUG = True
```

## Performance Tips

1. **First run is slow**: Models need to download (2-4GB)
2. **Batch processing**: Process multiple pages at once for efficiency
3. **Resolution**: Larger images take longer but produce better results
4. **Steps**: 20-25 steps is usually sufficient
5. **Model caching**: Models stay in memory between runs (faster)

## Limitations

- Requires significant disk space for models (5-10GB)
- GPU acceleration requires Apple Silicon or CUDA
- Text detection is not 100% accurate
- Processing speed depends on hardware (~30s per page on M2)
- Works best with clean, high-contrast manga line art

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Acknowledgments

- [Stable Diffusion](https://github.com/Stability-AI/stablediffusion) by Stability AI
- [ControlNet](https://github.com/lllyasviel/ControlNet) by Lvmin Zhang
- [Diffusers](https://github.com/huggingface/diffusers) by HuggingFace
- Anime models by the community

## Support

For issues and questions:
- Check existing GitHub issues
- Create a new issue with details
- Include system info and error logs

---

**Happy Colorizing!** 🎨
