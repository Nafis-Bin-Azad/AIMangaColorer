#!/usr/bin/env python3
"""
Command-line interface for Manga Colorizer.
"""
import logging
import sys
from pathlib import Path

import click
from tqdm import tqdm

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.colorizer import MangaColorizer
from backend.config import DEFAULT_PROMPT, DEFAULT_NEGATIVE_PROMPT


def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )


@click.group()
@click.version_option(version='1.0.0')
def cli():
    """Manga Colorizer - AI-powered manga colorization tool."""
    pass


@cli.command()
@click.argument('input_path', type=click.Path(exists=True))
@click.option('--output', '-o', type=click.Path(), help='Output directory')
@click.option('--model', '-m', default='anythingv5', help='Model to use')
@click.option('--prompt', '-p', help='Custom prompt')
@click.option('--negative-prompt', '-n', help='Custom negative prompt')
@click.option('--denoise', '-d', type=float, default=0.4, help='Denoising strength (0.3-0.5)')
@click.option('--steps', '-s', type=int, default=25, help='Number of inference steps')
@click.option('--guidance', '-g', type=float, default=8.0, help='Guidance scale')
@click.option('--seed', type=int, help='Random seed for reproducibility')
@click.option('--zip', 'create_zip', is_flag=True, help='Create output ZIP file')
@click.option('--no-text-protection', is_flag=True, help='Disable text detection')
@click.option('--comparison', is_flag=True, help='Save before/after comparison')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def colorize(
    input_path,
    output,
    model,
    prompt,
    negative_prompt,
    denoise,
    steps,
    guidance,
    seed,
    create_zip,
    no_text_protection,
    comparison,
    verbose
):
    """
    Colorize manga pages from an image or ZIP file.
    
    Examples:
    
        manga-colorize input.zip
        
        manga-colorize page.png --model meinamix --output ./colored
        
        manga-colorize input.zip --prompt "vibrant colors" --steps 30
    """
    setup_logging(verbose)
    
    input_path = Path(input_path)
    
    # Determine output directory
    if output:
        output_dir = Path(output)
        output_dir.mkdir(exist_ok=True, parents=True)
    else:
        output_dir = Path.cwd() / 'output'
        output_dir.mkdir(exist_ok=True, parents=True)
    
    click.echo(f"🎨 Manga Colorizer")
    click.echo(f"Input: {input_path}")
    click.echo(f"Output: {output_dir}")
    click.echo(f"Model: {model}")
    click.echo()
    
    try:
        # Initialize colorizer
        click.echo("Initializing colorizer...")
        colorizer = MangaColorizer(
            model_name=model,
            enable_text_detection=not no_text_protection,
            output_dir=output_dir
        )
        
        # Set custom prompts if provided
        if prompt or negative_prompt:
            colorizer.set_prompt(
                prompt or DEFAULT_PROMPT,
                negative_prompt or DEFAULT_NEGATIVE_PROMPT
            )
        
        # Set parameters
        colorizer.set_params(
            denoise_strength=denoise,
            num_inference_steps=steps,
            guidance_scale=guidance,
            seed=seed
        )
        
        # Initialize model
        click.echo(f"Loading model: {model}...")
        with click.progressbar(length=100, label='Loading model') as bar:
            colorizer.initialize_model()
            bar.update(100)
        
        click.echo("Model loaded successfully!")
        click.echo()
        
        # Check if single file or batch
        is_single = input_path.is_file() and input_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']
        
        if is_single:
            # Single image processing
            click.echo(f"Processing: {input_path.name}")
            
            progress_bar = tqdm(total=steps, desc="Colorizing", unit="step")
            
            def progress_callback(progress, current_step, total_steps):
                progress_bar.n = current_step
                progress_bar.refresh()
            
            result = colorizer.colorize_single_image(
                image_path=input_path,
                save_comparison=comparison,
                progress_callback=progress_callback
            )
            
            progress_bar.close()
            
            if result['success']:
                click.echo(f"✓ Success! Saved to: {result['output_file']}")
                if result.get('text_regions_protected', 0) > 0:
                    click.echo(f"  Protected {result['text_regions_protected']} text regions")
                if comparison and 'comparison_file' in result:
                    click.echo(f"  Comparison: {result['comparison_file']}")
            else:
                click.echo(f"✗ Failed: {result.get('error', 'Unknown error')}", err=True)
                sys.exit(1)
        
        else:
            # Batch processing
            click.echo("Starting batch processing...")
            
            progress_data = {'current': 0, 'total': 0}
            progress_bar = None
            
            def progress_callback(current, total, filename):
                nonlocal progress_bar
                
                if progress_bar is None or progress_data['total'] != total:
                    if progress_bar:
                        progress_bar.close()
                    progress_data['total'] = total
                    progress_bar = tqdm(total=total, desc="Processing pages", unit="page")
                
                progress_data['current'] = current
                progress_bar.n = current
                progress_bar.set_postfix_str(filename)
                progress_bar.refresh()
            
            result = colorizer.colorize_batch(
                input_path=input_path,
                create_zip=create_zip,
                progress_callback=progress_callback
            )
            
            if progress_bar:
                progress_bar.close()
            
            if result['success']:
                click.echo(f"\n✓ Batch complete!")
                click.echo(f"  Processed: {result['output_count']}/{result['input_count']} images")
                click.echo(f"  Output directory: {result['output_dir']}")
                if create_zip and 'zip_file' in result:
                    click.echo(f"  ZIP file: {result['zip_file']}")
            else:
                click.echo(f"\n✗ Batch failed: {result.get('error', 'Unknown error')}", err=True)
                sys.exit(1)
        
        click.echo("\n🎉 All done!")
    
    except KeyboardInterrupt:
        click.echo("\n\nCancelled by user", err=True)
        sys.exit(130)
    
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
def list_models():
    """List available models."""
    setup_logging()
    
    try:
        from backend.model_manager import ModelManager
        
        click.echo("Available models:")
        click.echo()
        
        manager = ModelManager()
        models = manager.list_available_models()
        
        for name, path in models.items():
            click.echo(f"  • {name}")
            if verbose:
                click.echo(f"    Path: {path}")
        
        click.echo(f"\nTotal: {len(models)} models")
    
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument('model_name')
@click.option('--model-id', help='HuggingFace model ID')
def download_model(model_name, model_id):
    """Download a model from HuggingFace."""
    setup_logging()
    
    try:
        from backend.model_manager import ModelManager
        
        click.echo(f"Downloading model: {model_name}")
        if model_id:
            click.echo(f"From: {model_id}")
        click.echo()
        
        manager = ModelManager()
        
        with click.progressbar(length=100, label='Downloading') as bar:
            path = manager.download_model(model_name, model_id)
            bar.update(100)
        
        click.echo(f"\n✓ Model downloaded to: {path}")
    
    except Exception as e:
        click.echo(f"\n✗ Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def server():
    """Start the Flask server for GUI."""
    setup_logging()
    
    try:
        click.echo("Starting Manga Colorizer server...")
        click.echo("Server will be available at: http://localhost:5000")
        click.echo("Press Ctrl+C to stop")
        click.echo()
        
        from backend.server import run_server
        run_server()
    
    except KeyboardInterrupt:
        click.echo("\n\nServer stopped", err=True)
        sys.exit(0)
    
    except Exception as e:
        click.echo(f"\nError: {e}", err=True)
        sys.exit(1)


if __name__ == '__main__':
    cli()
