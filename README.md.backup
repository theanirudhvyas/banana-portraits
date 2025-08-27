# Nano Banana Portrait - AI Face Identity Image Composer

A Python CLI tool for creating custom portraits using AI fine-tuning with your own face images. Built with fal.ai's Flux models and LoRA fine-tuning.

⚠️ **WARNING**: All output is AI-generated and watermarked. Not suitable for deception or impersonation.

## Features

- **Fine-tune** Flux LoRA models with your face images (15-20 recommended)
- **Generate** custom portraits with text prompts using your trained model
- **Inpaint** faces to edit expressions, restore damaged areas, or make modifications  
- **Manage** multiple trained models locally
- **Auto-cleanup** temporary files and organized output storage

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd nano_banana_portrait
```

2. Create and activate a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install the package:
```bash
pip install -e .
```

4. Set your FAL API key:
```bash
nano-banana config set-key YOUR_FAL_API_KEY
```

## Quick Start

### 1. Generate images with base models (no fine-tuning needed)

Choose from multiple base models, each with different strengths:

```bash
# Google's Gemini 2.5 Flash (nano-banana) - Fast, simple, great quality
nano-banana generate --prompt "a person in a sci-fi city" -b nano-banana

# Flux Dev - High quality, supports fine-tuning (default)
nano-banana generate --prompt "a person in a sci-fi city, photorealistic" -b flux-dev

# Flux Schnell - Very fast, lower quality  
nano-banana generate --prompt "a person in a sci-fi city" -b flux-schnell

# For debugging, use verbose mode to see API requests/responses:
nano-banana -v generate --prompt "a robot holding a banana" -b nano-banana
```

### 2. Fine-tune a model with your face images (optional)

For personalized portraits, prepare 15-20 clear face photos:

```bash
nano-banana fine-tune --images-dir ./my_photos --name john_model --trigger-word JOHN
```

### 3. Generate custom portraits with your model

```bash
nano-banana generate --model john_model --prompt "JOHN in a sci-fi city, photorealistic"
```

### 4. Edit faces with inpainting

```bash
nano-banana inpaint --image generated.jpg --mask face_mask.png --prompt "smiling happily"
# Or with a fine-tuned model:
nano-banana inpaint --image generated.jpg --mask face_mask.png --prompt "smiling happily" --model john_model
```

## Commands

### `fine-tune`
Train a LoRA model with your face images.

```bash
nano-banana fine-tune --images-dir PHOTOS_DIR [options]

Options:
  -i, --images-dir PATH   Directory with 15-20 face images [required]
  -n, --name TEXT         Model name (default: "default")  
  -t, --trigger-word TEXT Trigger word for model (default: "NANO")
```

### `generate`
Generate images using base models or fine-tuned models.

```bash
nano-banana generate --prompt "DESCRIPTION" [options]

Options:
  -p, --prompt TEXT               Image description [required]
  -b, --base-model [flux-dev|flux-schnell|nano-banana]  
                                  Base model to use (default: flux-dev)
  -m, --model TEXT                Fine-tuned model name (optional, flux models only)
  -c, --count INTEGER             Number of images (default: 1)
  -s, --size [square|landscape_4_3|landscape_16_9|portrait_4_3|portrait_16_9]
                                  Image size (default: landscape_16_9, ignored for nano-banana)
  --steps INTEGER                 Inference steps (model-specific defaults, ignored for nano-banana)
```

**Examples:**
```bash
# Generate with nano-banana (fast, simple)
nano-banana generate --prompt "a robot in space" -b nano-banana

# Generate with flux-dev (high quality, default)
nano-banana generate --prompt "an astronaut in space, photorealistic" -b flux-dev

# Generate with flux-schnell (very fast)
nano-banana generate --prompt "a mountain landscape" -b flux-schnell --steps 4

# Generate with fine-tuned model (flux only)
nano-banana generate --model john_model --prompt "JOHN as an astronaut in space" -b flux-dev
```

### `inpaint`
Edit faces in existing images.

```bash
nano-banana inpaint --image IMAGE --mask MASK --prompt "CHANGES" [options]

Options:
  -i, --image PATH        Source image [required]
  -k, --mask PATH         Mask image (white = edit areas) [required]  
  -p, --prompt TEXT       Description of changes [required]
  -m, --model TEXT        Fine-tuned model name (optional - uses base model if not specified)
  -s, --strength FLOAT    Edit strength 0.0-1.0 (default: 0.85)
```

**Examples:**
```bash
# Inpaint with base model
nano-banana inpaint --image photo.jpg --mask face_mask.png --prompt "smiling expression"

# Inpaint with fine-tuned model
nano-banana inpaint --image photo.jpg --mask face_mask.png --prompt "JOHN smiling" --model john_model
```

### `list-models`
Show all trained models.

```bash
nano-banana list-models
```

### `history`
Track and manage generation history with SQLite database.

```bash
# List recent generations
nano-banana history list

# Search generations by prompt
nano-banana history list --search "robot"

# Filter by model
nano-banana history list --model nano-banana

# Show detailed information
nano-banana history show 42

# Open generated image
nano-banana history open 42

# Interactive Terminal UI browser with thumbnails
nano-banana history browse

# Show statistics
nano-banana history stats

# Clean up old history
nano-banana history cleanup --days 30
```

### `config`
Manage configuration.

```bash
nano-banana config show              # Show current settings
nano-banana config set-key API_KEY   # Set FAL API key
```

## Base Models Comparison

### 🚀 nano-banana (Gemini 2.5 Flash Image)
- **Best for**: Quick, high-quality generations
- **Speed**: Very fast (~1-2 seconds)
- **Quality**: Excellent
- **Parameters**: Only prompt and count (max 4 images)
- **Fine-tuning**: Not supported
- **Cost**: ~$0.039 per image

### ⚡ flux-schnell
- **Best for**: Very fast iterations and testing
- **Speed**: Fast (~3-5 seconds) 
- **Quality**: Good
- **Parameters**: Full control (max 4 steps)
- **Fine-tuning**: Supported
- **Cost**: Lower cost per generation

### 🎨 flux-dev (default)
- **Best for**: High-quality results and fine-tuning
- **Speed**: Moderate (~10-30 seconds depending on steps)
- **Quality**: Excellent 
- **Parameters**: Full control (up to 50+ steps)
- **Fine-tuning**: Supported with LoRA
- **Cost**: Higher cost but best quality

## Tips for Best Results

### Training Images (Flux models only)
- Use 15-20 high-quality face photos
- Vary lighting, angles, and expressions
- Ensure clear, unobstructed faces
- Consistent person across all images

### Prompts
- **nano-banana**: Simple, natural descriptions work best
- **Flux models**: Include trigger word for fine-tuned models
- Be specific about style and setting
- Examples: "NANO in a Renaissance painting style", "JOHN at a beach party, golden hour"

### Model Selection
- **Quick tests**: Use nano-banana or flux-schnell
- **Best quality**: Use flux-dev with 25-40 steps
- **Fine-tuning**: Only flux-dev and flux-schnell support LoRA models

### Inference Steps (Flux models only)
- **flux-schnell**: Default 4 steps (max 4)
- **flux-dev**: Default 28 steps (1-50+ range)
- Higher steps = better quality but slower generation

### Inpainting
- Create masks with white areas for editing zones
- Use clear, specific prompts for changes
- Experiment with different strength values

## Generation History Database

The CLI automatically tracks all generations in a SQLite database (`data/generations.db`) with the following features:

### 📊 **Automatic Tracking**
- **Prompts & Parameters**: All prompts, models, steps, sizes recorded
- **Performance Metrics**: Generation time, success/failure rates
- **Image Management**: Local paths, original URLs, metadata
- **Model Usage**: Track which models you use most

### 🔍 **Powerful Search**
```bash
# Search by prompt content
nano-banana history list --search "robot sunset mountain"

# Filter by model
nano-banana history list --model nano-banana --limit 10

# Show failed generations too
nano-banana history list --all

# Get detailed info about specific generation
nano-banana history show 42
```

### 🖼️ **Image Management**
```bash
# Open generated image in default app
nano-banana history open 42

# Open specific image if multiple generated
nano-banana history open 42 --index 2
```

### 🎨 **Terminal UI Browser**
```bash
# Launch interactive Terminal UI with image thumbnails
nano-banana history browse
```

**Features:**
- **ASCII Thumbnails**: View image previews directly in terminal
- **Fuzzy Search**: Real-time search across all prompts using fuzzy matching
- **Click to Open**: Click on any generation to open the image in default app
- **Keyboard Navigation**: 
  - `q` - Quit
  - `r` - Refresh from database  
  - `Esc` - Clear search
- **Generation Details**: Shows ID, timestamp, model, generation time, and prompt
- **Visual Status**: ✅ for successful, ❌ for failed generations
- **Image Count**: Shows when multiple images were generated

### 📈 **Analytics**
```bash
# View generation statistics
nano-banana history stats
```

Sample output:
```
📊 Generation History Statistics
========================================
Total Generations: 25
Successful: 24
Failed: 1
Success Rate: 96.0%

Generations by Model:
  nano-banana: 15
  flux-dev: 8
  flux-schnell: 2

Average Generation Times:
  nano-banana: 2.1s
  flux-dev: 8.3s
  flux-schnell: 1.8s
```

### 🧹 **Database Management**
```bash
# Clean up old generations (keep last 30 days)
nano-banana history cleanup --days 30

# Preview what would be deleted
nano-banana history cleanup --days 30 --dry-run
```

## Project Structure

```
nano_banana_portrait/
├── data/
│   ├── models/           # Trained model registry
│   ├── outputs/          # Generated images  
│   ├── temp/             # Temporary files
│   └── generations.db    # SQLite history database
├── src/
│   ├── cli.py           # Main CLI commands
│   ├── fal_wrapper.py   # FAL API integration
│   ├── database.py      # SQLite history management
│   ├── config.py        # Configuration management
│   └── storage.py       # File management
└── requirements.txt
```

## Requirements

- Python 3.8+
- FAL API key ([get one here](https://fal.ai))
- Internet connection for API calls
- ~100MB storage per trained model

## Legal & Ethics

- **AI-Generated Content**: All outputs are synthetic and watermarked
- **Personal Use Only**: Not for commercial or deceptive purposes
- **Identity Rights**: Only use your own face images or with explicit permission
- **Platform Terms**: Follow fal.ai terms of service

## Debug Mode

Use the `-v` or `--verbose` flag to see detailed FAL API requests and responses:

```bash
# Debug image generation
nano-banana -v generate --prompt "a sunset over mountains"

# Debug fine-tuning
nano-banana -v fine-tune --images-dir ./photos --name debug_model

# Debug inpainting
nano-banana -v inpaint --image photo.jpg --mask mask.png --prompt "smile"
```

**Verbose output includes:**
- Complete API request parameters (indented JSON)
- Full API responses with metadata, timings, and URLs
- File upload URLs and paths
- Model selection and parameter adjustments

## Troubleshooting

**"FAL_KEY is required"**
- Set your API key: `nano-banana config set-key YOUR_KEY`

**"No image files found"**  
- Check image directory contains .jpg/.png files
- Ensure file extensions are lowercase

**Training fails**
- Verify images are clear face photos of same person
- Try with 15-20 images instead of fewer
- Check internet connection
- Use `-v` flag to see detailed error responses

**Generation fails**
- Ensure model exists: `nano-banana list-models`
- Include trigger word in prompt
- Try simpler prompts first
- Use `-v` flag to debug API calls