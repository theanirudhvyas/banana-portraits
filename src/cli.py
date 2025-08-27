"""Main CLI interface for nano-banana portrait generator"""
import click
import os
import json
from pathlib import Path
from typing import List, Optional
from .fal_wrapper import FALWrapper
from .storage import StorageManager
from .config import Config
from .database import DatabaseManager


def require_fal_client(ctx):
    """Check if FAL client is available, exit if not"""
    if ctx.obj['fal'] is None:
        click.echo("Error: FAL_KEY is required for this command.")
        click.echo("Set your API key with: nano-banana config set-key <your-key>")
        ctx.exit(1)
    return ctx.obj['fal']


@click.group()
@click.version_option(version="0.1.0")
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging (shows FAL API responses)')
@click.pass_context
def main(ctx, verbose):
    """AI Face Identity Image Composer CLI
    
    Generate custom portraits using AI fine-tuning with your own face images.
    
    WARNING: All output is AI-generated and watermarked. 
    Not suitable for deception or impersonation.
    """
    ctx.ensure_object(dict)
    
    # Store verbose flag for all commands
    ctx.obj['verbose'] = verbose
    
    # Initialize config and services
    config = Config()
    storage = StorageManager()
    db_manager = DatabaseManager()
    
    ctx.obj['config'] = config
    ctx.obj['storage'] = storage
    ctx.obj['db'] = db_manager
    
    # Only initialize FAL client if API key is available and not running config commands
    if config.fal_key:
        ctx.obj['fal'] = FALWrapper(config.fal_key, verbose=verbose, db_manager=db_manager)
    else:
        ctx.obj['fal'] = None


@main.command()
@click.option('--images-dir', '-i', required=True, type=click.Path(exists=True, file_okay=False, dir_okay=True),
              help='Directory containing 15-20 face images for training')
@click.option('--name', '-n', default='default', show_default=True, help='Name for this model')
@click.option('--trigger-word', '-t', default='NANO', show_default=True, help='Trigger word for the model')
@click.pass_context
def fine_tune(ctx, images_dir: str, name: str, trigger_word: str):
    """Fine-tune a LoRA model with your face images
    
    Provide a directory with 15-20 clear face photos of the same person.
    The model will learn to generate that person's face in new scenarios.
    """
    fal = require_fal_client(ctx)
    storage = ctx.obj['storage']
    
    # Find all image files in directory
    images_dir = Path(images_dir)
    image_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
    image_paths = [
        str(path) for path in images_dir.iterdir() 
        if path.suffix.lower() in image_extensions
    ]
    
    if not image_paths:
        click.echo(f"Error: No image files found in {images_dir}")
        return
    
    click.echo(f"Found {len(image_paths)} images in {images_dir}")
    
    if len(image_paths) < 10:
        if not click.confirm(f"Warning: Only {len(image_paths)} images found. 15-20 recommended. Continue?"):
            return
    
    try:
        # Start fine-tuning
        click.echo("Starting fine-tuning process...")
        result = fal.fine_tune_flux_lora(image_paths, trigger_word)
        
        if 'lora_url' in result:
            # Save model info
            model_info = {
                'name': name,
                'lora_url': result['lora_url'],
                'trigger_word': trigger_word,
                'created_at': storage.get_timestamp(),
                'training_images': len(image_paths)
            }
            
            storage.save_model(name, model_info)
            
            click.echo(f"✅ Fine-tuning completed successfully!")
            click.echo(f"Model saved as: {name}")
            click.echo(f"Trigger word: {trigger_word}")
            click.echo(f"Use this model with: nano-banana generate --model {name} --prompt \"<your prompt>\"")
        else:
            click.echo("❌ Fine-tuning failed. Check the output above for errors.")
            
    except Exception as e:
        click.echo(f"❌ Error during fine-tuning: {e}")


@main.command()
@click.option('--prompt', '-p', required=True, help='Description of the image to generate')
@click.option('--base-model', '-b', default='flux-dev', show_default=True,
              type=click.Choice(['flux-dev', 'flux-schnell', 'nano-banana']),
              help='Base model to use')
@click.option('--model', '-m', help='Name of fine-tuned model to use (optional - uses base model if not specified)')
@click.option('--reference-images', '-r', multiple=True, type=click.Path(exists=True),
              help='Reference image paths for character consistency (nano-banana only, can specify multiple)')
@click.option('--count', '-c', default=1, show_default=True, type=int, help='Number of images to generate')
@click.option('--size', '-s', default='landscape_16_9', show_default=True,
              type=click.Choice(['square', 'landscape_4_3', 'landscape_16_9', 'portrait_4_3', 'portrait_16_9']),
              help='Image size/aspect ratio (ignored for nano-banana)')
@click.option('--steps', type=int, help='Number of inference steps (model-specific defaults, ignored for nano-banana)')
@click.pass_context
def generate(ctx, prompt: str, base_model: str, model: str, reference_images: tuple, count: int, size: str, steps: int):
    """Generate images using specified base model or a fine-tuned model
    
    Supports multiple base models: flux-dev, flux-schnell, and nano-banana.
    Each model has appropriate defaults and capabilities.
    """
    fal = require_fal_client(ctx)
    storage = ctx.obj['storage']
    
    # Set model-specific defaults for steps if not provided
    if steps is None:
        model_defaults = {
            "flux-dev": 28,
            "flux-schnell": 4, 
            "nano-banana": None  # nano-banana doesn't use steps
        }
        steps = model_defaults.get(base_model, 28)
    
    lora_url = None
    trigger_word = None
    model_name = f"base_{base_model.replace('-', '_')}"
    
    # Load fine-tuned model info if specified
    if model:
        if base_model == "nano-banana":
            click.echo("⚠️  nano-banana doesn't support fine-tuned models, ignoring --model parameter")
            model = None
        else:
            try:
                model_info = storage.load_model(model)
                if not model_info:
                    click.echo(f"Error: Model '{model}' not found. Use 'nano-banana list-models' to see available models.")
                    click.echo(f"Falling back to base {base_model} model...")
                    model = None
                else:
                    lora_url = model_info['lora_url']
                    trigger_word = model_info['trigger_word']
                    model_name = model
                    
                    click.echo(f"Using fine-tuned model: {model} on {base_model}")
                    click.echo(f"Trigger word: {trigger_word}")
                    
                    if trigger_word.lower() not in prompt.lower():
                        click.echo(f"💡 Tip: Include '{trigger_word}' in your prompt for best results")
                    
            except Exception as e:
                click.echo(f"Error loading model: {e}")
                click.echo(f"Falling back to base {base_model} model...")
                model = None
                model_name = f"base_{base_model.replace('-', '_')}"
    
    if not model:
        click.echo(f"Using base {base_model} model")
    
    try:
        # Convert reference images tuple to list
        reference_image_list = list(reference_images) if reference_images else None
        
        # Generate images
        result = fal.generate_image(
            prompt=prompt,
            base_model=base_model,
            lora_url=lora_url,
            num_images=count,
            image_size=size,
            steps=steps or 0,  # Provide fallback for nano-banana
            reference_images=reference_image_list
        )
        
        if 'images' in result:
            click.echo(f"✅ Generated {len(result['images'])} image(s)!")
            
            # Save images locally
            saved_paths = []
            for i, image_data in enumerate(result['images']):
                image_url = image_data.get('url')
                if image_url:
                    filename = f"{model_name}_{storage.get_timestamp()}_{i+1}.jpg"
                    saved_path = storage.save_generated_image(image_url, filename)
                    saved_paths.append(saved_path)
                    click.echo(f"Saved: {saved_path}")
            
            # Update database with image paths
            if '_generation_id' in result and saved_paths:
                db = ctx.obj['db']
                try:
                    db.update_image_paths(result['_generation_id'], saved_paths)
                except Exception as e:
                    if ctx.obj.get('verbose'):
                        click.echo(f"Warning: Failed to update database with image paths: {e}")
            
            click.echo(f"\n🎨 Images saved to: {storage.outputs_dir}")
        else:
            click.echo("❌ Image generation failed. Check the output above for errors.")
            
    except Exception as e:
        click.echo(f"❌ Error during generation: {e}")


@main.command()
@click.option('--image', '-i', required=True, type=click.Path(exists=True),
              help='Path to image to inpaint')
@click.option('--mask', '-k', required=True, type=click.Path(exists=True),
              help='Path to mask image (white = areas to inpaint)')
@click.option('--prompt', '-p', required=True, help='Description of desired changes')
@click.option('--model', '-m', help='Name of fine-tuned model to use (optional - uses base model if not specified)')
@click.option('--strength', '-s', default=0.85, show_default=True, type=float, help='Inpainting strength (0.0-1.0)')
@click.pass_context
def inpaint(ctx, image: str, mask: str, prompt: str, model: str, strength: float):
    """Edit/restore faces in images using inpainting
    
    Provide an image, a mask (white areas will be inpainted), and a prompt
    describing the desired changes. Optionally use a fine-tuned model.
    """
    fal = require_fal_client(ctx)
    storage = ctx.obj['storage']
    
    lora_url = None
    model_name = "base_flux"
    
    # Load model info if model is specified
    if model:
        try:
            model_info = storage.load_model(model)
            if not model_info:
                click.echo(f"Error: Model '{model}' not found.")
                click.echo("Falling back to base Flux model...")
                model = None
            else:
                lora_url = model_info['lora_url']
                model_name = model
                click.echo(f"Using fine-tuned model: {model}")
                
        except Exception as e:
            click.echo(f"Error loading model: {e}")
            click.echo("Falling back to base Flux model...")
            model = None
            model_name = "base_flux"
    
    if not model:
        click.echo("Using base Flux model for inpainting")
    
    try:
        # Upload source image and mask
        click.echo("Uploading images...")
        image_url = fal.upload_file(image)
        mask_url = fal.upload_file(mask)
        
        # Perform inpainting
        result = fal.inpaint_face(
            image_url=image_url,
            mask_url=mask_url,
            prompt=prompt,
            lora_url=lora_url,
            strength=strength
        )
        
        if 'images' in result and result['images']:
            click.echo("✅ Inpainting completed!")
            
            # Save result
            image_data = result['images'][0]
            if 'url' in image_data:
                filename = f"inpaint_{model_name}_{storage.get_timestamp()}.jpg"
                saved_path = storage.save_generated_image(image_data['url'], filename)
                click.echo(f"Saved: {saved_path}")
            else:
                click.echo("❌ No image URL in result")
        else:
            click.echo("❌ Inpainting failed. Check the output above for errors.")
            
    except Exception as e:
        click.echo(f"❌ Error during inpainting: {e}")


@main.command('list-models')
@click.pass_context
def list_models(ctx):
    """List all available fine-tuned models"""
    storage = ctx.obj['storage']
    
    models = storage.list_models()
    if not models:
        click.echo("No fine-tuned models found. Use 'nano-banana fine-tune' to create one.")
        return
    
    click.echo("Available models:")
    for name, info in models.items():
        click.echo(f"  • {name}")
        click.echo(f"    Trigger word: {info['trigger_word']}")
        click.echo(f"    Created: {info['created_at']}")
        click.echo(f"    Training images: {info['training_images']}")
        click.echo()


@main.command('detect-watermark')
@click.option('--image', '-i', required=True, type=click.Path(exists=True),
              help='Path to image to check for watermarks')
@click.pass_context
def detect_watermark(ctx, image: str):
    """Detect SynthID watermarks in generated images
    
    [PLACEHOLDER] This feature will detect AI watermarks in images.
    Currently not implemented - this is a placeholder for future development.
    """
    click.echo("🔍 SynthID Watermark Detection")
    click.echo(f"Analyzing image: {Path(image).name}")
    click.echo()
    click.echo("❌ Feature not yet implemented")
    click.echo("This is a placeholder for future SynthID detection capability.")
    click.echo()
    click.echo("💡 All images generated by this tool are AI-created and watermarked.")


@main.command('stats')
@click.pass_context  
def stats(ctx):
    """Show storage usage statistics"""
    storage = ctx.obj['storage']
    
    stats = storage.get_storage_stats()
    
    click.echo("📊 Storage Statistics")
    click.echo(f"  Models: {stats['models_count']}")
    click.echo(f"  Outputs size: {stats['outputs_size_mb']:.1f} MB")
    click.echo(f"  Temp size: {stats['temp_size_mb']:.1f} MB")
    click.echo(f"  Total size: {stats['total_size_mb']:.1f} MB")
    
    if stats['temp_size_mb'] > 10:
        click.echo()
        click.echo("💡 Tip: Clean up temp files with manual cleanup if needed")


@main.group()
def config():
    """Configuration management"""
    pass


@config.command('set-key')
@click.argument('api_key')
def set_key(api_key: str):
    """Set your FAL API key"""
    config = Config()
    config.set_fal_key(api_key)
    click.echo("✅ FAL API key saved to .env file")


@config.command('show')
@click.pass_context
def show_config(ctx):
    """Show current configuration"""
    config = ctx.obj['config']
    
    click.echo("Current configuration:")
    click.echo(f"  FAL API Key: {'Set' if config.fal_key else 'Not set'}")
    click.echo(f"  Storage directory: {config.storage_dir}")


@main.group()
def history():
    """Generation history management"""
    pass


@history.command('list')
@click.option('--search', '-s', help='Search in prompts')
@click.option('--model', '-m', help='Filter by base model')
@click.option('--limit', '-l', default=20, show_default=True, type=int, help='Number of results to show')
@click.option('--all', 'show_all', is_flag=True, help='Show failed generations too')
@click.pass_context
def list_history(ctx, search: str, model: str, limit: int, show_all: bool):
    """List generation history"""
    db = ctx.obj['db']
    
    try:
        results = db.search_generations(
            prompt_search=search,
            base_model=model,
            success_only=not show_all,
            limit=limit
        )
        
        if not results:
            click.echo("No generations found matching criteria.")
            return
        
        click.echo(f"Found {len(results)} generation(s):")
        click.echo()
        
        for gen in results:
            timestamp = gen['timestamp'][:19].replace('T', ' ')  # Format datetime
            status = "✅" if gen['success'] else "❌"
            model_info = gen['base_model']
            if gen['finetuned_model']:
                model_info += f" + {gen['finetuned_model']}"
            
            click.echo(f"{status} [{gen['id']:3d}] {timestamp} | {model_info}")
            click.echo(f"    \"{gen['prompt'][:80]}{'...' if len(gen['prompt']) > 80 else ''}\"")
            
            if gen['success'] and gen['image_paths']:
                paths = json.loads(gen['image_paths']) if isinstance(gen['image_paths'], str) else gen['image_paths']
                click.echo(f"    Images: {len(paths)} saved")
                if gen['generation_time']:
                    click.echo(f"    Time: {gen['generation_time']:.2f}s")
            elif not gen['success']:
                click.echo(f"    Error: {gen['error_message'][:60]}{'...' if len(gen['error_message'] or '') > 60 else ''}")
            
            click.echo()
            
    except Exception as e:
        click.echo(f"❌ Error querying history: {e}")


@history.command('show')
@click.argument('generation_id', type=int)
@click.pass_context
def show_generation(ctx, generation_id: int):
    """Show detailed information about a specific generation"""
    db = ctx.obj['db']
    
    try:
        gen = db.get_generation_by_id(generation_id)
        if not gen:
            click.echo(f"Generation {generation_id} not found.")
            return
        
        click.echo(f"Generation {gen['id']}")
        click.echo("=" * 50)
        click.echo(f"Timestamp: {gen['timestamp'].replace('T', ' ')}")
        click.echo(f"Status: {'Success' if gen['success'] else 'Failed'}")
        click.echo(f"Base Model: {gen['base_model']}")
        
        if gen['finetuned_model']:
            click.echo(f"Fine-tuned Model: {gen['finetuned_model']}")
        
        if gen['steps']:
            click.echo(f"Steps: {gen['steps']}")
        
        if gen['image_size']:
            click.echo(f"Image Size: {gen['image_size']}")
        
        click.echo(f"Number of Images: {gen['num_images']}")
        
        if gen['seed']:
            click.echo(f"Seed: {gen['seed']}")
        
        if gen['generation_time']:
            click.echo(f"Generation Time: {gen['generation_time']:.3f}s")
        
        click.echo(f"\nPrompt:")
        click.echo(f'"{gen["prompt"]}"')
        
        if gen['success'] and gen['image_paths']:
            paths = gen['image_paths']
            click.echo(f"\nSaved Images ({len(paths)}):")
            for i, path in enumerate(paths, 1):
                exists = "✓" if Path(path).exists() else "✗"
                click.echo(f"  {i}. {exists} {path}")
        
        if not gen['success'] and gen['error_message']:
            click.echo(f"\nError Message:")
            click.echo(gen['error_message'])
            
    except Exception as e:
        click.echo(f"❌ Error retrieving generation: {e}")


@history.command('open')
@click.argument('generation_id', type=int)
@click.option('--index', '-i', default=1, show_default=True, type=int, help='Image index to open (1-based)')
@click.pass_context
def open_generation(ctx, generation_id: int, index: int):
    """Open images from a specific generation"""
    db = ctx.obj['db']
    
    try:
        gen = db.get_generation_by_id(generation_id)
        if not gen:
            click.echo(f"Generation {generation_id} not found.")
            return
        
        if not gen['success']:
            click.echo(f"Generation {generation_id} failed, no images to open.")
            return
        
        if not gen['image_paths']:
            click.echo(f"No image paths found for generation {generation_id}.")
            return
        
        paths = gen['image_paths']
        if index < 1 or index > len(paths):
            click.echo(f"Invalid image index {index}. Available: 1-{len(paths)}")
            return
        
        image_path = Path(paths[index - 1])
        if not image_path.exists():
            click.echo(f"Image file not found: {image_path}")
            return
        
        # Open with system default application
        import subprocess
        import platform
        
        system = platform.system()
        try:
            if system == "Darwin":  # macOS
                subprocess.run(["open", str(image_path)])
            elif system == "Windows":
                subprocess.run(["start", str(image_path)], shell=True)
            else:  # Linux
                subprocess.run(["xdg-open", str(image_path)])
            
            click.echo(f"Opening: {image_path.name}")
            
        except Exception as e:
            click.echo(f"❌ Error opening image: {e}")
            click.echo(f"Image location: {image_path}")
            
    except Exception as e:
        click.echo(f"❌ Error retrieving generation: {e}")


@history.command('stats')
@click.pass_context
def history_stats(ctx):
    """Show generation history statistics"""
    db = ctx.obj['db']
    
    try:
        stats = db.get_stats()
        
        click.echo("📊 Generation History Statistics")
        click.echo("=" * 40)
        click.echo(f"Total Generations: {stats['total_generations']}")
        click.echo(f"Successful: {stats['successful_generations']}")
        click.echo(f"Failed: {stats['failed_generations']}")
        click.echo(f"Success Rate: {stats['success_rate']:.1f}%")
        
        if stats['model_counts']:
            click.echo(f"\nGenerations by Model:")
            for model, count in stats['model_counts'].items():
                click.echo(f"  {model}: {count}")
        
        if stats['avg_generation_times']:
            click.echo(f"\nAverage Generation Times:")
            for model, avg_time in stats['avg_generation_times'].items():
                click.echo(f"  {model}: {avg_time:.2f}s")
                
    except Exception as e:
        click.echo(f"❌ Error retrieving statistics: {e}")


@history.command('cleanup')
@click.option('--days', '-d', default=30, show_default=True, type=int, help='Keep generations newer than N days')
@click.option('--dry-run', is_flag=True, help='Show what would be deleted without actually deleting')
@click.pass_context
def cleanup_history(ctx, days: int, dry_run: bool):
    """Clean up old generation history"""
    db = ctx.obj['db']
    
    if dry_run:
        click.echo(f"DRY RUN: Would delete generations older than {days} days")
        # For now, just show current count
        stats = db.get_stats()
        click.echo(f"Current total: {stats['total_generations']} generations")
    else:
        if not click.confirm(f"Delete generations older than {days} days?"):
            return
        
        try:
            deleted = db.cleanup_old_generations(days)
            click.echo(f"✅ Deleted {deleted} old generations")
        except Exception as e:
            click.echo(f"❌ Error during cleanup: {e}")


@history.command('browse')
@click.pass_context
def browse_history(ctx):
    """Launch interactive TUI browser with image thumbnails and fuzzy search
    
    Features:
    - Image thumbnails displayed inline (Alacritty terminal)  
    - Fuzzy search across prompts
    - Click or Enter to open images
    - Keyboard navigation (q=quit, r=refresh, esc=clear search)
    """
    try:
        from .tui import run_history_browser
        run_history_browser()
    except ImportError as e:
        click.echo("❌ TUI dependencies not installed.")
        click.echo("Install with: pip install textual fuzzywuzzy python-levenshtein")
    except Exception as e:
        click.echo(f"❌ Error launching TUI: {e}")


if __name__ == '__main__':
    main()