"""FAL AI provider implementation"""
import time
from typing import List, Optional, Dict, Any

from .base import (
    BaseProvider, GenerationRequest, GenerationResult, 
    ModelInfo, ModelCapability
)


class FALProvider(BaseProvider):
    """FAL AI provider implementation"""
    
    def __init__(self, api_key: Optional[str] = None, **config: Any) -> None:
        super().__init__("fal", api_key, **config)
        self._client = None
    
    def initialize(self) -> bool:
        """Initialize FAL client"""
        if not self.api_key:
            return False
        
        try:
            import fal_client as fal
            import os
            os.environ['FAL_KEY'] = self.api_key
            self._client = fal
            return True
        except ImportError:
            return False
    
    def get_available_models(self) -> List[ModelInfo]:
        """Get FAL models"""
        return [
            ModelInfo(
                name="flux-dev",
                display_name="Flux Dev",
                description="High-quality image generation with fine-tuning support",
                capabilities=[
                    ModelCapability.TEXT_TO_IMAGE,
                    ModelCapability.FINE_TUNING
                ],
                max_images=4,
                supports_fine_tuning=True,
                default_params={
                    "steps": 28,
                    "guidance_scale": 3.5,
                    "image_size": "landscape_16_9"
                }
            ),
            ModelInfo(
                name="flux-schnell", 
                display_name="Flux Schnell",
                description="Fast image generation (max 4 steps)",
                capabilities=[ModelCapability.TEXT_TO_IMAGE],
                max_images=4,
                supports_fine_tuning=False,
                default_params={
                    "steps": 4,
                    "guidance_scale": 3.5,
                    "image_size": "landscape_16_9"
                }
            ),
            ModelInfo(
                name="nano-banana",
                display_name="Nano Banana",
                description="Gemini Flash with image generation capabilities",
                capabilities=[
                    ModelCapability.TEXT_TO_IMAGE,
                    ModelCapability.IMAGE_TO_IMAGE,
                    ModelCapability.EDITING
                ],
                max_images=4,
                supports_fine_tuning=False,
                default_params={}
            )
        ]
    
    def generate_image(self, request: GenerationRequest) -> GenerationResult:
        """Generate images using FAL API"""
        if not self._client:
            return GenerationResult(
                success=False,
                images=[],
                metadata={},
                error_message="FAL client not initialized"
            )
        
        start_time = time.time()
        
        try:
            # Map model names to FAL endpoints
            model_mapping = {
                "flux-dev": "fal-ai/flux/dev",
                "flux-schnell": "fal-ai/flux/schnell", 
                "nano-banana": "fal-ai/gemini-25-flash-image"
            }
            
            fal_model = model_mapping.get(request.model_name)
            if not fal_model:
                raise ValueError(f"Unknown model: {request.model_name}")
            
            # Build arguments based on model
            if request.model_name == "nano-banana":
                # Handle nano-banana specific logic
                if request.reference_images:
                    fal_model = "fal-ai/gemini-25-flash-image/edit"
                    # Upload reference images
                    image_urls = []
                    for img_path in request.reference_images:
                        url = self._client.upload_file(img_path)
                        image_urls.append(url)
                    
                    arguments = {
                        "prompt": request.prompt,
                        "image_urls": image_urls,
                        "num_images": min(request.num_images, 4)
                    }
                else:
                    arguments = {
                        "prompt": request.prompt,
                        "num_images": min(request.num_images, 4)
                    }
            else:
                # Flux models
                arguments = {
                    "prompt": request.prompt,
                    "num_images": request.num_images,
                    "image_size": f"{request.width}x{request.height}" if request.width and request.height else "landscape_16_9",
                }
                
                if request.steps:
                    max_steps = 4 if request.model_name == "flux-schnell" else 50
                    arguments["num_inference_steps"] = min(request.steps, max_steps)
                
                if request.guidance_scale:
                    arguments["guidance_scale"] = request.guidance_scale
                
                if request.seed:
                    arguments["seed"] = request.seed
                
                if request.fine_tuned_model:
                    arguments["loras"] = [{"path": request.fine_tuned_model, "scale": 1.0}]
            
            # Call FAL API
            result = self._client.subscribe(
                fal_model,
                arguments=arguments,
                with_logs=True
            )
            
            generation_time = time.time() - start_time
            
            # Process results
            images = []
            if 'images' in result:
                for i, img_data in enumerate(result['images']):
                    images.append({
                        "url": img_data.get('url', ''),
                        "path": ""  # Will be filled by storage manager
                    })
            
            metadata = {
                "provider": "fal",
                "model": request.model_name,
                "fal_model": fal_model,
                "arguments": arguments,
                "raw_result": result
            }
            
            if 'seed' in result:
                metadata['seed'] = result['seed']
            
            return GenerationResult(
                success=True,
                images=images,
                metadata=metadata,
                generation_time=generation_time,
                seed=result.get('seed')
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            
            return GenerationResult(
                success=False,
                images=[],
                metadata={
                    "provider": "fal",
                    "model": request.model_name,
                    "error_details": str(e)
                },
                error_message=str(e),
                generation_time=generation_time
            )
    
    def fine_tune_model(self, 
                       image_paths: List[str],
                       trigger_word: str = "NANO",
                       **kwargs: Any) -> Dict[str, Any]:
        """Fine-tune a LoRA model using FAL"""
        if not self._client:
            raise RuntimeError("FAL client not initialized")
        
        # Upload training images
        uploaded_urls = []
        for img_path in image_paths:
            url = self._client.upload_file(img_path)
            uploaded_urls.append(url)
        
        # Submit training job
        arguments = {
            "images_data_url": uploaded_urls,
            "trigger_word": trigger_word,
            "steps": kwargs.get("steps", 1000),
            "learning_rate": kwargs.get("learning_rate", 4e-4),
        }
        
        result = self._client.subscribe(
            "fal-ai/flux-lora-fast-training",
            arguments=arguments,
            with_logs=True
        )
        
        return result
    
    def edit_image(self, 
                  prompt: str,
                  image_urls: List[str],
                  **kwargs: Any) -> GenerationResult:
        """Edit images using nano-banana edit endpoint"""
        if not self._client:
            return GenerationResult(
                success=False,
                images=[],
                metadata={},
                error_message="FAL client not initialized"
            )
        
        start_time = time.time()
        
        try:
            arguments = {
                "prompt": prompt,
                "image_urls": image_urls
            }
            
            result = self._client.subscribe(
                "fal-ai/gemini-25-flash-image/edit",
                arguments=arguments,
                with_logs=True
            )
            
            generation_time = time.time() - start_time
            
            # Process results
            images = []
            if 'images' in result:
                for img_data in result['images']:
                    images.append({
                        "url": img_data.get('url', ''),
                        "path": ""
                    })
            
            return GenerationResult(
                success=True,
                images=images,
                metadata={
                    "provider": "fal",
                    "operation": "edit",
                    "arguments": arguments
                },
                generation_time=generation_time
            )
            
        except Exception as e:
            generation_time = time.time() - start_time
            
            return GenerationResult(
                success=False,
                images=[],
                metadata={"provider": "fal", "operation": "edit"},
                error_message=str(e),
                generation_time=generation_time
            )