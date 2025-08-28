"""Local storage management for models and generated images"""
import json
import shutil
import tempfile
import requests
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Any
from .config import Config


class StorageManager:
    """Manages local storage for models, images, and temporary files"""
    
    def __init__(self) -> None:
        self.config = Config()
        self.models_file: Path = self.config.models_dir / 'models.json'
        self.outputs_dir: Path = self.config.outputs_dir
        self.temp_dir: Path = self.config.temp_dir
        
        # Load existing models registry
        self._models: Dict[str, Dict[str, Any]] = self._load_models_registry()
    
    def save_model(self, name: str, model_info: Dict[str, Any]) -> None:
        """Save model information to registry
        
        Args:
            name: Model name
            model_info: Model metadata including lora_url, trigger_word, etc.
        """
        self._models[name] = model_info
        self._save_models_registry()
    
    def load_model(self, name: str) -> Optional[Dict[str, Any]]:
        """Load model information from registry
        
        Args:
            name: Model name
            
        Returns:
            Model info dict or None if not found
        """
        return self._models.get(name)
    
    def list_models(self) -> Dict[str, Dict[str, Any]]:
        """List all saved models
        
        Returns:
            Dictionary of model name -> model info
        """
        return self._models.copy()
    
    def delete_model(self, name: str) -> bool:
        """Delete model from registry
        
        Args:
            name: Model name
            
        Returns:
            True if deleted, False if not found
        """
        if name in self._models:
            del self._models[name]
            self._save_models_registry()
            return True
        return False
    
    def save_generated_image(self, image_url: str, filename: str) -> str:
        """Download and save a generated image locally
        
        Args:
            image_url: URL of the image to download
            filename: Local filename to save as
            
        Returns:
            Path to saved file
        """
        output_path = self.outputs_dir / filename
        
        # Download image
        response = requests.get(image_url, stream=True)
        response.raise_for_status()
        
        # Save to outputs directory
        with open(output_path, 'wb') as f:
            shutil.copyfileobj(response.raw, f)
        
        return str(output_path)
    
    def create_temp_file(self, suffix: str = '') -> str:
        """Create a temporary file
        
        Args:
            suffix: File extension (e.g., '.jpg')
            
        Returns:
            Path to temporary file
        """
        temp_file = tempfile.NamedTemporaryFile(
            suffix=suffix,
            dir=self.temp_dir,
            delete=False
        )
        temp_file.close()
        return temp_file.name
    
    def cleanup_temp_files(self) -> None:
        """Clean up all temporary files"""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
    
    def get_timestamp(self) -> str:
        """Get current timestamp string for filenames
        
        Returns:
            Timestamp in format YYYYMMDD_HHMMSS
        """
        return datetime.now().strftime('%Y%m%d_%H%M%S')
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage usage statistics
        
        Returns:
            Dictionary with storage info
        """
        def get_dir_size(directory: Path) -> int:
            """Calculate directory size in bytes"""
            if not directory.exists():
                return 0
            return sum(f.stat().st_size for f in directory.rglob('*') if f.is_file())
        
        return {
            'models_count': len(self._models),
            'outputs_size_mb': get_dir_size(self.outputs_dir) / (1024 * 1024),
            'temp_size_mb': get_dir_size(self.temp_dir) / (1024 * 1024),
            'total_size_mb': get_dir_size(self.config.storage_dir) / (1024 * 1024),
        }
    
    def _load_models_registry(self) -> Dict[str, Dict[str, Any]]:
        """Load models registry from JSON file"""
        if self.models_file.exists():
            try:
                with open(self.models_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start with empty registry
                pass
        
        return {}
    
    def _save_models_registry(self) -> None:
        """Save models registry to JSON file"""
        with open(self.models_file, 'w') as f:
            json.dump(self._models, f, indent=2)