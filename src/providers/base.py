"""Base classes for AI model providers"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum


class ModelCapability(Enum):
    """Capabilities that a model provider can support"""
    TEXT_TO_IMAGE = "text_to_image"
    IMAGE_TO_IMAGE = "image_to_image"
    INPAINTING = "inpainting"
    FINE_TUNING = "fine_tuning"
    EDITING = "editing"


@dataclass
class GenerationRequest:
    """Standard request format for image generation"""
    prompt: str
    model_name: str
    num_images: int = 1
    width: int = 1024
    height: int = 1024
    steps: Optional[int] = None
    guidance_scale: Optional[float] = None
    seed: Optional[int] = None
    reference_images: Optional[List[str]] = None
    fine_tuned_model: Optional[str] = None
    extra_params: Optional[Dict[str, Any]] = None


@dataclass
class GenerationResult:
    """Standard result format for image generation"""
    success: bool
    images: List[Dict[str, str]]  # List of {"url": "...", "path": "..."}
    metadata: Dict[str, Any]
    error_message: Optional[str] = None
    generation_time: Optional[float] = None
    seed: Optional[int] = None


@dataclass
class ModelInfo:
    """Information about an available model"""
    name: str
    display_name: str
    description: str
    capabilities: List[ModelCapability]
    max_images: int = 1
    supports_fine_tuning: bool = False
    default_params: Optional[Dict[str, Any]] = None


class BaseProvider(ABC):
    """Abstract base class for AI model providers"""
    
    def __init__(self, name: str, api_key: Optional[str] = None, **config: Any) -> None:
        self.name = name
        self.api_key = api_key
        self.config = config
        self._models: Dict[str, ModelInfo] = {}
    
    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the provider and return success status"""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[ModelInfo]:
        """Get list of available models from this provider"""
        pass
    
    @abstractmethod
    def generate_image(self, request: GenerationRequest) -> GenerationResult:
        """Generate images based on the request"""
        pass
    
    def supports_capability(self, capability: ModelCapability) -> bool:
        """Check if provider supports a specific capability"""
        return any(capability in model.capabilities for model in self.get_available_models())
    
    def get_model_info(self, model_name: str) -> Optional[ModelInfo]:
        """Get information about a specific model"""
        models = self.get_available_models()
        return next((m for m in models if m.name == model_name), None)
    
    def validate_request(self, request: GenerationRequest) -> List[str]:
        """Validate a generation request and return any errors"""
        errors = []
        
        if not request.prompt.strip():
            errors.append("Prompt cannot be empty")
        
        if request.num_images < 1:
            errors.append("Number of images must be at least 1")
        
        model_info = self.get_model_info(request.model_name)
        if not model_info:
            errors.append(f"Model '{request.model_name}' not found")
        elif request.num_images > model_info.max_images:
            errors.append(f"Model '{request.model_name}' supports max {model_info.max_images} images")
        
        return errors
    
    def fine_tune_model(self, **kwargs: Any) -> Dict[str, Any]:
        """Fine-tune a model - override if supported"""
        raise NotImplementedError(f"Provider '{self.name}' does not support fine-tuning")
    
    def edit_image(self, **kwargs: Any) -> GenerationResult:
        """Edit an image - override if supported"""
        raise NotImplementedError(f"Provider '{self.name}' does not support image editing")
    
    def inpaint_image(self, **kwargs: Any) -> GenerationResult:
        """Inpaint an image - override if supported"""
        raise NotImplementedError(f"Provider '{self.name}' does not support inpainting")


class ProviderRegistry:
    """Registry for managing multiple AI model providers"""
    
    def __init__(self) -> None:
        self._providers: Dict[str, BaseProvider] = {}
        self._model_to_provider: Dict[str, str] = {}
    
    def register_provider(self, provider: BaseProvider) -> bool:
        """Register a new provider"""
        if not provider.initialize():
            return False
        
        self._providers[provider.name] = provider
        
        # Map all provider models to the provider
        for model in provider.get_available_models():
            self._model_to_provider[model.name] = provider.name
        
        return True
    
    def get_provider(self, name: str) -> Optional[BaseProvider]:
        """Get a provider by name"""
        return self._providers.get(name)
    
    def get_provider_for_model(self, model_name: str) -> Optional[BaseProvider]:
        """Get the provider that supports a specific model"""
        provider_name = self._model_to_provider.get(model_name)
        return self._providers.get(provider_name) if provider_name else None
    
    def get_all_models(self) -> List[ModelInfo]:
        """Get all available models from all providers"""
        models = []
        for provider in self._providers.values():
            models.extend(provider.get_available_models())
        return models
    
    def get_models_with_capability(self, capability: ModelCapability) -> List[ModelInfo]:
        """Get all models that support a specific capability"""
        return [m for m in self.get_all_models() if capability in m.capabilities]
    
    def generate_image(self, request: GenerationRequest) -> GenerationResult:
        """Generate image using the appropriate provider"""
        provider = self.get_provider_for_model(request.model_name)
        
        if not provider:
            return GenerationResult(
                success=False,
                images=[],
                metadata={},
                error_message=f"No provider found for model '{request.model_name}'"
            )
        
        # Validate request
        errors = provider.validate_request(request)
        if errors:
            return GenerationResult(
                success=False,
                images=[],
                metadata={},
                error_message=f"Validation errors: {'; '.join(errors)}"
            )
        
        return provider.generate_image(request)
    
    def list_providers(self) -> List[str]:
        """Get list of registered provider names"""
        return list(self._providers.keys())


# Global registry instance
registry = ProviderRegistry()


def get_registry() -> ProviderRegistry:
    """Get the global provider registry"""
    return registry