"""FAL API wrapper for image generation and fine-tuning"""
import os
import time
import fal_client as fal
from typing import List, Dict, Optional, Callable, Any, Union
from pathlib import Path
import json


class FALWrapper:
    """Wrapper class for FAL API operations"""
    
    def __init__(self, api_key: Optional[str] = None, verbose: bool = False, db_manager: Optional[Any] = None) -> None:
        """Initialize FAL client with API key"""
        self.api_key = api_key or os.getenv('FAL_KEY')
        self.verbose = verbose
        self.db_manager = db_manager
        
        if not self.api_key:
            raise ValueError("FAL_KEY environment variable is required")
        
        os.environ['FAL_KEY'] = self.api_key
    
    def _log_verbose(self, title: str, data: Any) -> None:
        """Log verbose information if verbose mode is enabled"""
        if self.verbose:
            print(f"\n🔍 DEBUG: {title}")
            if isinstance(data, dict) or isinstance(data, list):
                print(json.dumps(data, indent=2, default=str))
            else:
                print(data)
            print("─" * 50)
    
    def _log_generation(
        self,
        prompt: str,
        base_model: str,
        result: Dict[str, Any],
        finetuned_model: Optional[str] = None,
        steps: Optional[int] = None,
        image_size: Optional[str] = None,
        num_images: int = 1,
        generation_time: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        image_paths: Optional[List[str]] = None
    ) -> Optional[int]:
        """Log generation to database if db_manager is available"""
        if self.db_manager:
            try:
                return self.db_manager.log_generation(
                    prompt=prompt,
                    base_model=base_model,
                    result=result,
                    finetuned_model=finetuned_model,
                    steps=steps,
                    image_size=image_size,
                    num_images=num_images,
                    generation_time=generation_time,
                    success=success,
                    error_message=error_message,
                    image_paths=image_paths
                )
            except Exception as e:
                if self.verbose:
                    print(f"Warning: Failed to log to database: {e}")
        return None
        
    def fine_tune_flux_lora(
        self, 
        image_paths: List[str], 
        trigger_word: str = "NANO",
        on_progress: Optional[Callable[[Any], None]] = None
    ) -> Dict[str, Any]:
        """Fine-tune Flux LoRA model with user images
        
        Args:
            image_paths: List of paths to training images (15-20 recommended)
            trigger_word: Trigger word for the LoRA model
            on_progress: Optional callback for progress updates
            
        Returns:
            Dict with training results including model URL
        """
        # Validate images
        self._validate_training_images(image_paths)
        
        # Upload images
        uploaded_urls = []
        print(f"Uploading {len(image_paths)} training images...")
        for i, path in enumerate(image_paths):
            print(f"Uploading image {i+1}/{len(image_paths)}: {Path(path).name}")
            url = fal.upload_file(path)
            uploaded_urls.append(url)
        
        print("Starting LoRA training...")
        
        # Submit training job
        arguments = {
            "images_data_url": uploaded_urls,
            "trigger_word": trigger_word,
            "steps": 1000,
            "learning_rate": 4e-4,
        }
        
        self._log_verbose("Fine-tuning Request", {
            "model": "fal-ai/flux-lora-fast-training",
            "arguments": arguments
        })
        
        result = fal.subscribe(
            "fal-ai/flux-lora-fast-training",
            arguments=arguments,
            with_logs=True
        )
        
        self._log_verbose("Fine-tuning Response", result)
        
        return result
    
    def edit_image(
        self,
        prompt: str,
        image_urls: List[str]
    ) -> Dict[str, Any]:
        """Edit images using nano-banana edit endpoint
        
        Args:
            prompt: Description of desired edits
            image_urls: List of image URLs to edit
            
        Returns:
            Dict with edited image URLs
        """
        model = "fal-ai/gemini-25-flash-image/edit"
        
        arguments = {
            "prompt": prompt,
            "image_urls": image_urls
        }
        
        self._log_verbose("Edit Request", {
            "model": model,
            "arguments": arguments
        })
        
        print(f"🎨 Editing {len(image_urls)} image(s): '{prompt}'")
        
        # Track generation time
        start_time = time.time()
        success = True
        error_message = None
        
        try:
            result = fal.subscribe(
                model,
                arguments=arguments,
                with_logs=True
            )
            
            generation_time = time.time() - start_time
            
            self._log_verbose("Edit Response", result)
            
            # Log to database if available
            if self.db_manager:
                try:
                    self.db_manager.log_generation(
                        prompt=f"[EDIT] {prompt}",
                        base_model="nano-banana", 
                        success=success,
                        generation_time=generation_time,
                        num_images=len(result.get('images', [])),
                        error_message=error_message
                    )
                except Exception as e:
                    if self.verbose:
                        print(f"Warning: Failed to log to database: {e}")
            
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            success = False
            error_message = str(e)
            
            # Log failed generation
            if self.db_manager:
                try:
                    self.db_manager.log_generation(
                        prompt=f"[EDIT] {prompt}",
                        base_model="nano-banana",
                        success=False,
                        generation_time=generation_time,
                        error_message=error_message
                    )
                except Exception as log_e:
                    if self.verbose:
                        print(f"Warning: Failed to log to database: {log_e}")
            
            raise e
        
    def generate_image(
        self, 
        prompt: str, 
        base_model: str = "flux-dev",
        lora_url: Optional[str] = None,
        num_images: int = 1,
        image_size: str = "landscape_16_9",
        steps: int = 28,
        reference_images: Optional[List[str]] = None,
        on_progress: Optional[Callable[[Any], None]] = None
    ) -> Dict[str, Any]:
        """Generate images using specified base model with optional LoRA
        
        Args:
            prompt: Text description of desired image
            base_model: Base model to use ("flux-dev", "flux-schnell", "nano-banana")
            lora_url: URL of trained LoRA model (optional)
            num_images: Number of images to generate
            image_size: Image dimensions (ignored for nano-banana)
            steps: Number of inference steps (ignored for nano-banana)
            reference_images: List of local image paths for reference (nano-banana only)
            on_progress: Optional callback for progress updates
            
        Returns:
            Dict with generated image URLs
        """
        # Build arguments based on model type
        if base_model == "nano-banana":
            # Choose endpoint based on whether we have reference images
            if reference_images:
                model = "fal-ai/gemini-25-flash-image/edit"
                
                # Upload reference images
                print(f"Uploading {len(reference_images)} reference image(s)...")
                uploaded_urls = []
                for i, img_path in enumerate(reference_images):
                    print(f"Uploading reference image {i+1}/{len(reference_images)}: {Path(img_path).name}")
                    url = fal.upload_file(img_path)
                    uploaded_urls.append(url)
                
                arguments = {
                    "prompt": prompt,
                    "image_urls": uploaded_urls,
                    "num_images": min(num_images, 4)  # Max 4 images for nano-banana
                }
                print(f"Using nano-banana edit mode with {len(uploaded_urls)} reference image(s)")
            else:
                model = "fal-ai/gemini-25-flash-image"
                arguments = {
                    "prompt": prompt,
                    "num_images": min(num_images, 4)  # Max 4 images for nano-banana
                }
                print("Using nano-banana text-to-image mode")
            
            if num_images > 4:
                print(f"Note: nano-banana max is 4 images, adjusted from {num_images} to 4")
            
            if lora_url:
                print("Note: nano-banana doesn't support LoRA fine-tuning, ignoring model parameter")
                
        else:
            # Map base model names to FAL model IDs for Flux models
            model_mapping = {
                "flux-dev": "fal-ai/flux/dev",
                "flux-schnell": "fal-ai/flux/schnell"
            }
            
            model = model_mapping.get(base_model, "fal-ai/flux/dev")
            
            if reference_images:
                print("Note: Reference images are only supported for nano-banana model, ignoring reference images")
            
            # Flux models support full parameter set
            # Flux Schnell has max 4 steps
            if base_model == "flux-schnell":
                actual_steps = min(steps, 4)
                if actual_steps != steps:
                    print(f"Note: flux-schnell max is 4 steps, adjusted from {steps} to {actual_steps}")
            else:
                actual_steps = steps
                
            arguments = {
                "prompt": prompt,
                "num_images": num_images,
                "image_size": image_size,
                "num_inference_steps": actual_steps,
            }
            
            if lora_url:
                arguments["loras"] = [{"path": lora_url, "scale": 1.0}]
            
        print(f"Generating {arguments['num_images']} image(s) with {base_model}: '{prompt}'")
        
        self._log_verbose("Generation Request", {
            "base_model": base_model,
            "fal_model": model,
            "arguments": arguments
        })
        
        # Track generation time
        start_time = time.time()
        success = True
        error_message = None
        
        try:
            result = fal.subscribe(
                model,
                arguments=arguments,
                with_logs=True
            )
            
            generation_time = time.time() - start_time
            
            self._log_verbose("Generation Response", result)
            
            # Log to database (image_paths will be added later by CLI)
            generation_id = self._log_generation(
                prompt=prompt,
                base_model=base_model,
                result=result,
                finetuned_model=lora_url,  # Store the LoRA URL for now
                steps=steps if base_model != "nano-banana" else None,
                image_size=image_size if base_model != "nano-banana" else None,
                num_images=arguments['num_images'],
                generation_time=generation_time,
                success=success
            )
            
            # Add generation_id to result for CLI use
            result['_generation_id'] = generation_id
            
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            success = False
            error_message = str(e)
            
            # Log failed generation
            self._log_generation(
                prompt=prompt,
                base_model=base_model,
                result={},
                finetuned_model=lora_url,
                steps=steps if base_model != "nano-banana" else None,
                image_size=image_size if base_model != "nano-banana" else None,
                num_images=arguments['num_images'],
                generation_time=generation_time,
                success=success,
                error_message=error_message
            )
            
            raise
        
    def inpaint_face(
        self, 
        image_url: str, 
        mask_url: str, 
        prompt: str,
        lora_url: Optional[str] = None,
        strength: float = 0.85,
        on_progress: Optional[Callable[[Any], None]] = None
    ) -> Dict[str, Any]:
        """Inpaint face region with given prompt
        
        Args:
            image_url: URL of source image
            mask_url: URL of mask image (white = inpaint area)
            prompt: Text description for inpainting
            lora_url: URL of trained LoRA model (optional)
            strength: Inpainting strength (0.0-1.0)
            on_progress: Optional callback for progress updates
            
        Returns:
            Dict with inpainted image URL
        """
        arguments = {
            "image_url": image_url,
            "mask_url": mask_url,
            "prompt": prompt,
            "strength": strength,
        }
        
        if lora_url:
            arguments["loras"] = [{"path": lora_url, "scale": 1.0}]
            
        print(f"Inpainting face with prompt: '{prompt}'")
        
        self._log_verbose("Inpainting Request", {
            "model": "fal-ai/flux/dev/image-to-image",
            "arguments": arguments
        })
        
        result = fal.subscribe(
            "fal-ai/flux/dev/image-to-image",
            arguments=arguments,
            with_logs=True
        )
        
        self._log_verbose("Inpainting Response", result)
        
        return result
        
    def upload_file(self, file_path: str) -> str:
        """Upload a local file and return its URL
        
        Args:
            file_path: Path to local file
            
        Returns:
            URL of uploaded file
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
            
        print(f"Uploading file: {Path(file_path).name}")
        
        result = fal.upload_file(file_path)
        
        self._log_verbose("File Upload", {
            "local_path": file_path,
            "uploaded_url": result
        })
        
        return result
        
    def _validate_training_images(self, image_paths: List[str]) -> None:
        """Validate training images for LoRA fine-tuning"""
        if len(image_paths) < 10:
            print(f"Warning: Only {len(image_paths)} images provided. 15-20 images recommended for best results.")
        elif len(image_paths) > 30:
            print(f"Warning: {len(image_paths)} images provided. Consider using 15-25 images for optimal training.")
            
        # Check if all files exist
        missing_files = [path for path in image_paths if not os.path.exists(path)]
        if missing_files:
            raise FileNotFoundError(f"Missing image files: {missing_files}")
            
        # Check file extensions
        valid_extensions = {'.jpg', '.jpeg', '.png', '.webp'}
        invalid_files = [
            path for path in image_paths 
            if Path(path).suffix.lower() not in valid_extensions
        ]
        if invalid_files:
            raise ValueError(f"Invalid image formats: {invalid_files}. Supported: {valid_extensions}")
            
    def _default_progress_callback(self, update: Any) -> None:
        """Default progress callback for queue updates"""
        # Handle different types of status updates
        if hasattr(update, 'status'):
            print(f"Status: {update.status}")
        elif isinstance(update, dict):
            if 'status' in update:
                print(f"Status: {update['status']}")
            if 'logs' in update:
                for log in update['logs']:
                    print(f"Log: {log['message']}")
        else:
            print(f"Update: {update}")