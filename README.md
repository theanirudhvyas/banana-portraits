# Nano Banana Portrait - AI Face Identity Image Composer

A Python CLI tool for creating custom portraits using AI fine-tuning with your own face images. Built with fal.ai's Flux models and LoRA fine-tuning.

⚠️ **WARNING**: All output is AI-generated and watermarked. Not suitable for deception or impersonation.

## 🚀 User Setup

To get started with nano-banana as a user, run this in Claude Code:
```
1. Clone the repository: git clone <repository-url> && cd nano_banana_portrait
2. Set up Python environment: python3 -m venv venv && source venv/bin/activate
3. Install the package: pip install -e .
4. Set FAL API key: nano-banana config set-key YOUR_FAL_API_KEY
5. Test with quick generation: nano-banana generate -p "a robot holding a banana" -b nano-banana

See "Quick Generation Examples" in Additional Context for usage patterns.
```

## 🔧 Developer Setup

To set up your development environment, run this in Claude Code:
```
1. Clone and enter directory: git clone <repository-url> && cd nano_banana_portrait
2. Create virtual environment: python3 -m venv venv && source venv/bin/activate
3. Install in development mode: pip install -e .
4. Install development dependencies: pip install -r requirements.txt
5. Set up environment: cp .env.example .env && nano-banana config set-key YOUR_FAL_API_KEY
6. Run tests: nano-banana generate -p "test prompt" -b nano-banana -v
7. Verify all commands work: nano-banana --help && nano-banana history --help

See "Development Commands" and "Testing" sections in Additional Context for full workflow.
```

## 📚 Additional Context

### Prerequisites
- Python 3.8+
- FAL API key ([get one here](https://fal.ai))
- Internet connection for API calls
- ~100MB storage per trained model

### Quick Generation Examples

**Base Models (No Fine-tuning Required):**
```bash
# Google's Gemini 2.5 Flash (nano-banana) - Fast, simple, great quality
nano-banana generate --prompt "a person in a sci-fi city" -b nano-banana

# Flux Dev - High quality, supports fine-tuning (default)
nano-banana generate --prompt "a person in a sci-fi city, photorealistic" -b flux-dev

# Flux Schnell - Very fast, lower quality  
nano-banana generate --prompt "a person in a sci-fi city" -b flux-schnell
```

**Custom Portrait Workflow:**
```bash
# 1. Fine-tune with your photos
nano-banana fine-tune --images-dir ./my_photos --name john_model --trigger-word JOHN

# 2. Generate custom portraits
nano-banana generate --model john_model --prompt "JOHN in a sci-fi city, photorealistic"

# 3. Edit faces with inpainting
nano-banana inpaint --image generated.jpg --mask face_mask.png --prompt "smiling happily" --model john_model
```

### Development Commands

**Installation & Setup:**
```bash
# Create virtual environment and install package
python3 -m venv venv && source venv/bin/activate && pip install -e .

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
```

**CLI Usage:**
```bash
# Main CLI entry point after installation
nano-banana --help

# For development without installation
python -m src.cli --help

# Test generation with verbose logging
nano-banana -v generate -p "test prompt" -b nano-banana
```

### Command Reference

**Core Commands:**
- `nano-banana generate -p "prompt" -b model` - Generate images
- `nano-banana fine-tune -i photos_dir -n model_name -t TRIGGER` - Train LoRA model  
- `nano-banana inpaint -i image -k mask -p "changes"` - Edit faces
- `nano-banana history browse` - Interactive Terminal UI browser
- `nano-banana config set-key API_KEY` - Set FAL API key

**Base Models:**
- `nano-banana`: Google Gemini 2.5 Flash - Fast, simple, no fine-tuning
- `flux-dev`: High quality, supports fine-tuning (default)
- `flux-schnell`: Very fast, lower quality, supports fine-tuning

### Project Architecture

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
│   ├── storage.py       # File management
│   └── tui.py           # Terminal UI browser
└── requirements.txt
```

**Core Components:**
- **FAL Wrapper**: Central API integration with model-specific parameter handling
- **CLI Interface**: Click-based commands (generate, fine-tune, inpaint, history, config)
- **Database Manager**: SQLite tracking for all generations with search/stats
- **Terminal UI**: Textual-based browser with ASCII thumbnails and fuzzy search
- **Storage Manager**: Organized file storage in `data/` directory

### Generation History Database

**Automatic Tracking:**
- All prompts, models, parameters, generation times
- Success/failure rates and performance metrics
- Local image paths and metadata

**Search & Browse:**
```bash
# Search by prompt content
nano-banana history list --search "robot sunset mountain"

# Filter by model
nano-banana history list --model nano-banana --limit 10

# Interactive Terminal UI with thumbnails
nano-banana history browse

# View statistics  
nano-banana history stats

# Clean up old entries
nano-banana history cleanup --days 30
```

### Testing

**Basic Generation Tests:**
```bash
# Test each base model
nano-banana generate -p "a panda dressed as Steve Jobs" -b nano-banana
nano-banana generate -p "a robot in a city" -b flux-dev  
nano-banana generate -p "a robot in a city" -b flux-schnell
```

**Debug Mode:**
```bash
# Use -v flag to see detailed API requests/responses
nano-banana -v generate --prompt "debug test" -b nano-banana
```

### Tips for Best Results

**Training Images (Flux models only):**
- Use 15-20 high-quality face photos
- Vary lighting, angles, and expressions
- Ensure clear, unobstructed faces

**Prompts:**
- **nano-banana**: Simple, natural descriptions work best
- **Flux models**: Include trigger word for fine-tuned models (e.g., "JOHN as an astronaut")

**Model Selection:**
- **Quick tests**: Use nano-banana or flux-schnell
- **Best quality**: Use flux-dev with 25-40 steps
- **Fine-tuning**: Only flux-dev and flux-schnell support LoRA models

### Troubleshooting

**Setup Issues:**
- "FAL_KEY is required" → Run `nano-banana config set-key YOUR_KEY`
- Python version → Ensure Python 3.8+
- Virtual environment → Always activate: `source venv/bin/activate`

**Generation Issues:**
- "No model found" → Check `nano-banana list-models`
- Failed generation → Use `-v` flag to see API errors
- Training fails → Verify 15-20 clear face photos of same person

**File Issues:**
- "No image files found" → Check directory contains .jpg/.png files
- Permissions → Ensure write access to `data/` directory

### Legal & Ethics

- **AI-Generated Content**: All outputs are synthetic and watermarked
- **Personal Use Only**: Not for commercial or deceptive purposes  
- **Identity Rights**: Only use your own face images or with explicit permission
- **Platform Terms**: Follow fal.ai terms of service