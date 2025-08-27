"""Configuration management for nano-banana"""
import os
from pathlib import Path
from dotenv import load_dotenv


class Config:
    """Configuration manager"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        self.env_file = self.project_root / '.env'
        
        # Load environment variables
        load_dotenv(self.env_file)
        
        # API configuration
        self.fal_key = os.getenv('FAL_KEY')
        
        # Storage configuration
        self.storage_dir = self.project_root / 'data'
        self.models_dir = self.storage_dir / 'models'
        self.temp_dir = self.storage_dir / 'temp'
        self.outputs_dir = self.storage_dir / 'outputs'
        
        # Create directories if they don't exist
        for directory in [self.storage_dir, self.models_dir, self.temp_dir, self.outputs_dir]:
            directory.mkdir(parents=True, exist_ok=True)
    
    def set_fal_key(self, api_key: str):
        """Save FAL API key to .env file"""
        env_content = ""
        
        # Read existing .env content
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                env_content = f.read()
        
        # Update or add FAL_KEY
        lines = env_content.strip().split('\n') if env_content.strip() else []
        fal_key_set = False
        
        for i, line in enumerate(lines):
            if line.startswith('FAL_KEY='):
                lines[i] = f'FAL_KEY={api_key}'
                fal_key_set = True
                break
        
        if not fal_key_set:
            lines.append(f'FAL_KEY={api_key}')
        
        # Write back to .env
        with open(self.env_file, 'w') as f:
            f.write('\n'.join(lines) + '\n')
        
        # Update current environment
        os.environ['FAL_KEY'] = api_key
        self.fal_key = api_key
    
    def validate(self):
        """Validate configuration"""
        if not self.fal_key:
            raise ValueError("FAL_KEY is required. Set it using 'nano-banana config set-key <key>' or as an environment variable.")