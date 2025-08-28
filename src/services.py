"""Simple service locator for nano-banana application"""
from typing import Optional, Dict, Any, TypeVar, Type, TYPE_CHECKING
import os

if TYPE_CHECKING:
    from .fal_wrapper import FALWrapper

# Global service registry
_services: Dict[str, Any] = {}
_initialized: bool = False

T = TypeVar('T')


def register_service(service_type: Type[T], instance: T) -> None:
    """Register a service instance"""
    # Handle both actual classes and mocked classes
    try:
        service_name = service_type.__name__
    except AttributeError:
        # For mocked classes, use the string representation
        service_name = str(service_type).split("'")[1].split(".")[-1]
    _services[service_name] = instance


def get_service(service_type: Type[T]) -> T:
    """Get a service instance"""
    # Handle both actual classes and mocked classes
    try:
        service_name = service_type.__name__
    except AttributeError:
        # For mocked classes, use the string representation
        service_name = str(service_type).split("'")[1].split(".")[-1]
    
    if service_name not in _services:
        raise ValueError(f"Service {service_name} not registered. Call initialize_services() first.")
    return _services[service_name]


def clear_services() -> None:
    """Clear all services (useful for testing)"""
    global _initialized
    _services.clear()
    _initialized = False


def initialize_services(verbose: bool = False) -> None:
    """Initialize all core services"""
    global _initialized
    
    if _initialized:
        return
    
    from .config import Config
    from .storage import StorageManager
    from .database import DatabaseManager
    from .fal_wrapper import FALWrapper
    from .image_preview import ImagePreview
    from .providers.base import get_registry
    from .providers.fal_provider import FALProvider
    
    # Initialize in dependency order
    config = Config()
    register_service(Config, config)  # Register config first so other services can use it
    
    storage = StorageManager()
    database = DatabaseManager()
    image_preview = ImagePreview()
    
    # FAL wrapper with optional API key
    fal_client = None
    try:
        fal_client = FALWrapper(verbose=verbose, db_manager=database)
    except ValueError:
        # No FAL key available - will be handled by commands that need it
        pass
    
    # Initialize provider registry
    registry = get_registry()
    fal_api_key = getattr(config, 'fal_key', None)
    if fal_api_key and isinstance(fal_api_key, str):
        try:
            fal_provider = FALProvider(api_key=fal_api_key)
            registry.register_provider(fal_provider)
        except Exception:
            # Provider initialization failed - skip registration
            pass
    
    # Register remaining services (Config already registered)
    register_service(StorageManager, storage)
    register_service(DatabaseManager, database)
    register_service(ImagePreview, image_preview)
    
    if fal_client:
        register_service(FALWrapper, fal_client)
    
    _initialized = True


def is_initialized() -> bool:
    """Check if services are initialized"""
    return _initialized


def get_fal_client() -> Optional['FALWrapper']:
    """Get FAL client if available"""
    try:
        from .fal_wrapper import FALWrapper
        return get_service(FALWrapper)
    except ValueError:
        return None


def require_fal_client() -> 'FALWrapper':
    """Get FAL client or raise error if not available"""
    client = get_fal_client()
    if client is None:
        raise ValueError("FAL_KEY is required for this operation. Set with: nano-banana config set-key <key>")
    return client