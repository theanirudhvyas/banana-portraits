# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python CLI tool called "nano-banana" for AI face portrait generation using the FAL API (fal.ai). The project supports both base model generation and fine-tuning LoRA models with personal face images for custom portraits.

## Development Commands

### Installation & Setup
```bash
# Create virtual environment and install package
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Install dependencies
pip install -r requirements.txt
```

### Running the CLI
```bash
# Main CLI entry point after installation
nano-banana --help

# For development without installation
python -m src.cli --help

# Test generation with verbose logging
nano-banana -v generate -p "test prompt" -b nano-banana
```

### Testing Generation
```bash
# Quick test with nano-banana model (fast)
nano-banana generate -p "a panda dressed as Steve Jobs" -b nano-banana

# Test with different models
nano-banana generate -p "a robot in a city" -b flux-dev
nano-banana generate -p "a robot in a city" -b flux-schnell
```

## Architecture

### Core Components

**FAL Wrapper (`src/fal_wrapper.py`)**
- Central API wrapper for fal.ai service calls
- Handles three model types with different parameters:
  - `flux-dev`: Full featured model with fine-tuning support
  - `flux-schnell`: Fast model (max 4 steps)
  - `nano-banana`: Maps to `fal-ai/gemini-25-flash-image` (no steps parameter)
- Includes verbose logging for debugging API calls
- Automatic generation tracking via DatabaseManager integration

**CLI Interface (`src/cli.py`)**
- Click-based command structure with 4 main command groups:
  - `generate`: Image generation with base/fine-tuned models
  - `fine-tune`: LoRA model training
  - `inpaint`: Face inpainting/editing
  - `history`: Database operations and TUI browser
  - `config`: API key and settings management
- Context object pattern for sharing services (FAL, storage, database, config)
- Verbose flag (`-v`) enables API response logging across all commands

**Database Manager (`src/database.py`)**
- SQLite database for generation history tracking
- Automatic logging of all generations with metadata
- Search, statistics, and cleanup capabilities
- Schema includes: prompt, model, success status, generation time, image paths

**Terminal UI Browser (`src/tui.py`)**
- Textual-based interface for browsing generation history
- Features: ASCII thumbnails, fuzzy search, click-to-open images
- Real-time search across prompts using fuzzywuzzy
- Keyboard controls: q=quit, r=refresh, esc=clear search

**Storage Manager (`src/storage.py`)**
- Organized file storage in `data/` directory
- Structure: `outputs/`, `models/`, `temp/`
- Automatic cleanup and path management

### Data Flow

1. **Generation**: CLI → FAL Wrapper → fal.ai API → Image Download → Storage → Database Log
2. **History**: Database → TUI Browser → Image Display
3. **Fine-tuning**: Images → FAL Wrapper → Model Training → Model Storage → Database Log

## Key Configuration

**Environment Variables:**
- `FAL_KEY`: Required API key for fal.ai service
- Stored in `.env` file or set via `nano-banana config set-key`

**Model Parameters:**
- Each model has specific defaults (steps, guidance_scale, etc.)
- nano-banana model doesn't accept `steps` parameter
- flux-schnell limited to max 4 steps

**File Storage:**
- `data/generations.db`: SQLite database
- `data/outputs/`: Generated images with timestamp naming
- `data/models/`: Fine-tuned LoRA model files
- `data/temp/`: Temporary processing files

## Development Notes

- Use `--verbose/-v` flag for debugging FAL API calls and responses
- The CLI validates FAL_KEY availability before attempting API calls
- All generations are automatically tracked in SQLite database
- TUI browser provides visual interface for generation history management
- Image files use descriptive naming: `base_{model}_{timestamp}_{index}.jpg`

## Important API Considerations

- FAL client uses `arguments` parameter (not `input`) and `with_logs=True` (not `logs=True`)
- Model mapping handles user-friendly names to actual FAL endpoints
- Error handling includes specific model parameter validation
- Verbose mode shows full JSON API requests/responses for debugging
- before running any python command, enable the venv using the command `source ./venv/bin/activate`