# Usage Examples

This document provides practical examples for using Manga Colorizer.

## Basic Examples

### Example 1: Single Page Colorization

Colorize a single manga page with default settings:

```bash
python cli/cli.py colorize page.png
```

Output will be saved to `output/page_colored.png`

### Example 2: Batch Processing

Colorize all pages in a ZIP file:

```bash
python cli/cli.py colorize chapter1.zip --output ./colored_chapter1
```

### Example 3: Custom Prompts

Use custom prompts for specific coloring styles:

```bash
python cli/cli.py colorize page.png \
  --prompt "vibrant fantasy colors, magical atmosphere, detailed shading" \
  --negative-prompt "dull, washed out, monochrome"
```

## Advanced Examples

### Example 4: High Quality Settings

Maximum quality colorization:

```bash
python cli/cli.py colorize page.png \
  --steps 35 \
  --guidance 9.0 \
  --denoise 0.45 \
  --comparison
```

### Example 5: Fast Processing

Faster processing with reduced quality:

```bash
python cli/cli.py colorize page.png \
  --steps 15 \
  --no-text-protection
```

### Example 6: Reproducible Results

Use a seed for consistent results:

```bash
python cli/cli.py colorize page.png \
  --seed 42 \
  --steps 25
```

### Example 7: Different Models

Try different models for varied styles:

```bash
# Anime-focused
python cli/cli.py colorize page.png --model meinamix

# Fantasy/vibrant
python cli/cli.py colorize page.png --model abyssorangemix
```

### Example 8: Batch with ZIP Output

Process multiple pages and create a ZIP:

```bash
python cli/cli.py colorize chapter.zip \
  --zip \
  --output ./results
```

## Workflow Examples

### Example 9: Full Chapter Workflow

Complete workflow for a manga chapter:

```bash
# 1. Download the model (first time only)
python cli/cli.py download-model meinamix

# 2. Process the chapter
python cli/cli.py colorize chapter_05.zip \
  --model meinamix \
  --steps 28 \
  --guidance 8.5 \
  --zip \
  --output ./manga_vol1/chapter_05

# 3. View results
open ./manga_vol1/chapter_05
```

### Example 10: Comparison Mode

Generate before/after comparisons:

```bash
python cli/cli.py colorize test_page.png \
  --comparison \
  --steps 25
```

### Example 11: Experimenting with Styles

Test different prompts on the same page:

```bash
# Natural colors
python cli/cli.py colorize page.png \
  --prompt "natural colors, realistic lighting" \
  --output ./test/natural

# Vibrant/fantasy
python cli/cli.py colorize page.png \
  --prompt "vibrant fantasy colors, magical glow" \
  --output ./test/fantasy

# Pastel
python cli/cli.py colorize page.png \
  --prompt "soft pastel colors, dreamy atmosphere" \
  --output ./test/pastel
```

## GUI Examples

### Example 12: Using the Desktop App

1. Start the application:
   ```bash
   npm start
   ```

2. Drag and drop your ZIP file onto the upload area

3. Adjust settings:
   - Model: MeinaMix
   - Steps: 25
   - Guidance: 8.0
   - Enable "Protect text regions"
   - Enable "Create output ZIP"

4. Click "Start Colorization"

5. Monitor progress in real-time

6. View results in the preview gallery

7. Click "Open Output Folder" to access files

## Tips for Best Results

### For Character-Focused Pages

```bash
python cli/cli.py colorize character_page.png \
  --prompt "detailed character coloring, soft shading, clean highlights" \
  --steps 30 \
  --guidance 8.5
```

### For Action Scenes

```bash
python cli/cli.py colorize action_page.png \
  --prompt "dynamic colors, high contrast, intense action" \
  --steps 25 \
  --guidance 9.0
```

### For Backgrounds

```bash
python cli/cli.py colorize background.png \
  --prompt "detailed environment, atmospheric lighting" \
  --denoise 0.35 \
  --steps 28
```

### For Double-Page Spreads

Process each page separately for better control:

```bash
python cli/cli.py colorize left_page.png --output ./spread
python cli/cli.py colorize right_page.png --output ./spread
```

## Troubleshooting Examples

### If Colors Look Wrong

Try adjusting the guidance scale:

```bash
# Lower guidance (more creative)
python cli/cli.py colorize page.png --guidance 6.0

# Higher guidance (follows prompt more)
python cli/cli.py colorize page.png --guidance 10.0
```

### If Lines Get Blurred

Reduce denoising strength:

```bash
python cli/cli.py colorize page.png --denoise 0.3
```

### If Processing Too Slow

Reduce steps or disable text protection:

```bash
python cli/cli.py colorize page.png \
  --steps 20 \
  --no-text-protection
```

## Python API Examples

### Example: Using in Your Own Script

```python
from backend.colorizer import MangaColorizer

# Initialize
colorizer = MangaColorizer(
    model_name="anythingv5",
    enable_text_detection=True
)

# Initialize model
colorizer.initialize_model()

# Colorize single image
result = colorizer.colorize_single_image(
    image_path="page.png",
    save_comparison=True
)

print(f"Colorized: {result['output_file']}")

# Batch processing
result = colorizer.colorize_batch(
    input_path="chapter.zip",
    create_zip=True
)

print(f"Processed {result['output_count']} pages")
```

## Integration Examples

### Example: Server Mode

Run as a server for integration with other tools:

```bash
python cli/cli.py server
```

Then make API requests:

```bash
# Check status
curl http://localhost:5000/api/status

# List models
curl http://localhost:5000/api/models

# Upload and colorize
curl -X POST -F "file=@page.png" http://localhost:5000/api/colorize
```

---

For more information, see README.md and INSTALL.md
