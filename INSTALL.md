# Installation Guide for Manga Colorizer

This guide provides step-by-step instructions for installing Manga Colorizer on macOS.

## Prerequisites

Before starting, ensure you have:
- macOS 12.0 (Monterey) or later
- Command Line Tools for Xcode
- At least 16GB RAM (8GB minimum)
- 10GB free disk space

## Step 1: Install Homebrew (if not already installed)

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## Step 2: Install Python 3.10+

```bash
brew install python@3.11
```

Verify installation:
```bash
python3 --version
```

## Step 3: Install Node.js

```bash
brew install node
```

Verify installation:
```bash
node --version
npm --version
```

## Step 4: Clone the Repository

```bash
git clone <repository-url>
cd AIMangaColorer
```

Or download and extract the ZIP file.

## Step 5: Set Up Python Environment

Create a virtual environment:
```bash
python3 -m venv venv
```

Activate the virtual environment:
```bash
source venv/bin/activate
```

Your prompt should now show `(venv)`.

## Step 6: Install PyTorch

For Apple Silicon (M1/M2/M3):
```bash
pip install --upgrade pip
pip install torch torchvision torchaudio
```

Verify MPS is available:
```bash
python3 -c "import torch; print('MPS available:', torch.backends.mps.is_available())"
```

Should output: `MPS available: True`

## Step 7: Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- diffusers (Stable Diffusion)
- transformers
- controlnet-aux
- opencv-python
- Pillow
- Flask
- Click
- And other dependencies

Installation may take 5-10 minutes.

## Step 8: Install Node.js Dependencies

```bash
npm install
```

This installs Electron and Socket.IO client.

## Step 9: Verify Installation

Test the CLI:
```bash
python cli/cli.py --help
```

You should see the help message with available commands.

Test imports:
```bash
python -c "import torch; import diffusers; import cv2; print('All imports successful!')"
```

## Step 10: First Run (Download Models)

On the first run, models will be automatically downloaded from HuggingFace. This can take 10-20 minutes depending on your connection.

Download models manually (optional):
```bash
python cli/cli.py download-model anythingv5
```

## Troubleshooting

### Issue: pip install fails with "No matching distribution"

**Solution**: Upgrade pip and try again
```bash
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt
```

### Issue: torch.backends.mps not available

**Solution**: Ensure you have the latest macOS and PyTorch
```bash
pip install --upgrade torch torchvision torchaudio
```

### Issue: Command not found errors

**Solution**: Make sure virtual environment is activated
```bash
source venv/bin/activate
```

### Issue: Permission denied when running scripts

**Solution**: Make scripts executable
```bash
chmod +x run_cli.sh run_gui.sh
```

### Issue: Node modules installation fails

**Solution**: Clear npm cache and retry
```bash
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### Issue: SSL certificate errors during model download

**Solution**: Update certificates
```bash
pip install --upgrade certifi
```

## Uninstallation

To remove the application:

1. Deactivate virtual environment:
   ```bash
   deactivate
   ```

2. Remove the directory:
   ```bash
   cd ..
   rm -rf AIMangaColorer
   ```

3. (Optional) Remove downloaded models from HuggingFace cache:
   ```bash
   rm -rf ~/.cache/huggingface
   ```

## Next Steps

Once installed, see README.md for usage instructions:
- Using the CLI: `python cli/cli.py colorize --help`
- Using the GUI: `npm start`

## Getting Help

If you encounter issues:
1. Check the Troubleshooting section above
2. Verify all prerequisites are met
3. Check existing GitHub issues
4. Create a new issue with:
   - Your macOS version
   - Python version (`python3 --version`)
   - Error messages
   - Installation logs
