"""Base CLI command patterns and utilities"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
import click
from pathlib import Path

from .services import get_service, require_fal_client
from .fal_wrapper import FALWrapper
from .storage import StorageManager
from .database import DatabaseManager


class BaseCommand(ABC):
    """Base class for CLI commands using Template Method pattern"""
    
    def __init__(self) -> None:
        self.storage = get_service(StorageManager)
        self.db = get_service(DatabaseManager)
    
    def execute(self, **kwargs: Any) -> Any:
        """Template method for command execution"""
        # Step 1: Validate inputs
        validation_errors = self.validate_inputs(**kwargs)
        if validation_errors:
            for error in validation_errors:
                click.echo(f"❌ {error}", err=True)
            return False
        
        # Step 2: Execute main logic
        try:
            result = self.run(**kwargs)
            
            # Step 3: Handle success
            self.on_success(result, **kwargs)
            return result
            
        except Exception as e:
            # Step 4: Handle failure
            self.on_failure(e, **kwargs)
            return False
    
    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Main command logic - must be implemented by subclasses"""
        pass
    
    def validate_inputs(self, **kwargs: Any) -> List[str]:
        """Validate command inputs - override in subclasses if needed"""
        return []
    
    def on_success(self, result: Any, **kwargs: Any) -> None:
        """Handle successful command execution - override if needed"""
        if result:
            click.echo("✅ Command completed successfully")
    
    def on_failure(self, error: Exception, **kwargs: Any) -> None:
        """Handle command failure - override if needed"""
        click.echo(f"❌ Command failed: {error}", err=True)


class FALCommand(BaseCommand):
    """Base class for commands that require FAL API access"""
    
    def __init__(self) -> None:
        super().__init__()
        self.fal: Optional[FALWrapper] = None
    
    def validate_inputs(self, **kwargs: Any) -> List[str]:
        """Validate inputs including FAL API availability"""
        errors = super().validate_inputs(**kwargs)
        
        try:
            self.fal = require_fal_client()
        except ValueError as e:
            errors.append(str(e))
        
        return errors


class GenerationCommand(FALCommand):
    """Base class for image generation commands"""
    
    def validate_inputs(self, **kwargs: Any) -> List[str]:
        """Validate generation-specific inputs"""
        errors = super().validate_inputs(**kwargs)
        
        # Validate prompt
        prompt = kwargs.get('prompt', '').strip()
        if not prompt:
            errors.append("Prompt cannot be empty")
        elif len(prompt) < 3:
            errors.append("Prompt must be at least 3 characters long")
        
        # Validate number of images
        num_images = kwargs.get('num_images', 1)
        if not isinstance(num_images, int) or num_images < 1 or num_images > 10:
            errors.append("Number of images must be between 1 and 10")
        
        return errors
    
    def on_success(self, result: Any, **kwargs: Any) -> None:
        """Handle successful generation"""
        if result and 'images' in result:
            num_generated = len(result['images'])
            click.echo(f"✅ Generated {num_generated} image(s) successfully")
            
            # Show generation stats if available
            if 'generation_time' in result:
                click.echo(f"⏱️  Generation time: {result['generation_time']:.1f}s")
        else:
            click.echo("✅ Generation completed")


class FileCommand(BaseCommand):
    """Base class for commands that work with files"""
    
    def validate_file_exists(self, file_path: str, description: str = "File") -> List[str]:
        """Helper to validate file existence"""
        errors = []
        if not Path(file_path).exists():
            errors.append(f"{description} not found: {file_path}")
        return errors
    
    def validate_directory_exists(self, dir_path: str, description: str = "Directory") -> List[str]:
        """Helper to validate directory existence"""
        errors = []
        path = Path(dir_path)
        if not path.exists():
            errors.append(f"{description} not found: {dir_path}")
        elif not path.is_dir():
            errors.append(f"{description} is not a directory: {dir_path}")
        return errors


class ModelCommand(FALCommand):
    """Base class for model-related commands"""
    
    def validate_model_name(self, model_name: str) -> List[str]:
        """Validate model name format"""
        errors = []
        if not model_name:
            errors.append("Model name cannot be empty")
        elif len(model_name) < 2:
            errors.append("Model name must be at least 2 characters")
        elif not model_name.replace('-', '').replace('_', '').isalnum():
            errors.append("Model name can only contain letters, numbers, hyphens, and underscores")
        return errors


def command_with_template(command_class):
    """Decorator to create CLI commands using Template Method pattern"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            command = command_class()
            return command.execute(**kwargs)
        
        # Preserve original function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    return decorator


def safe_file_operation(operation_name: str):
    """Decorator for safe file operations with error handling"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except FileNotFoundError as e:
                click.echo(f"❌ {operation_name} failed: File not found - {e}")
                return False
            except PermissionError as e:
                click.echo(f"❌ {operation_name} failed: Permission denied - {e}")
                return False
            except OSError as e:
                click.echo(f"❌ {operation_name} failed: System error - {e}")
                return False
        
        return wrapper
    
    return decorator


def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024**2:
        return f"{size_bytes/1024:.1f} KB"
    elif size_bytes < 1024**3:
        return f"{size_bytes/(1024**2):.1f} MB"
    else:
        return f"{size_bytes/(1024**3):.1f} GB"


def validate_image_files(file_paths: List[str]) -> List[str]:
    """Validate that files are supported image formats"""
    valid_extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
    errors = []
    
    for file_path in file_paths:
        path = Path(file_path)
        
        if not path.exists():
            errors.append(f"File not found: {file_path}")
            continue
        
        if path.suffix.lower() not in valid_extensions:
            errors.append(f"Unsupported image format: {file_path} (must be {', '.join(valid_extensions)})")
    
    return errors