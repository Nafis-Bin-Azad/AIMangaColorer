"""
Stable Diffusion 1.5 + ControlNet Pipeline
Simplified pipeline for manga colorization using SD1.5 + anime lineart ControlNet
"""
import logging
import torch
from PIL import Image

from diffusers import (
    ControlNetModel,
    StableDiffusionControlNetImg2ImgPipeline,
    DPMSolverMultistepScheduler,
)

logger = logging.getLogger(__name__)


class SD15Pipeline:
    """
    SD1.5 + Anime Lineart ControlNet pipeline for manga colorization.
    Optimized for Mac MPS with memory-efficient settings.
    """
    
    SD15_BASE = "stablediffusionapi/anything-v5"
    SD15_CONTROLNET = "lllyasviel/control_v11p_sd15s2_lineart_anime"
    
    def __init__(self, progress_callback=None):
        """
        Initialize pipeline.
        
        Args:
            progress_callback: Optional callback(stage, current, total) for progress updates
        """
        self.progress_callback = progress_callback
        self.pipeline = None
        
        # Detect device
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"
        
        # Use float32 for MPS stability
        self.dtype = torch.float32
        
        logger.info(f"Pipeline device: {self.device}, dtype: {self.dtype}")
    
    def load_models(self):
        """Load SD1.5 + ControlNet models with MPS optimizations"""
        logger.info("Loading SD1.5 + Anime Lineart ControlNet...")
        
        # Load ControlNet
        controlnet = ControlNetModel.from_pretrained(
            self.SD15_CONTROLNET,
            torch_dtype=self.dtype
        )
        
        # Load SD1.5 pipeline
        self.pipeline = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
            self.SD15_BASE,
            controlnet=controlnet,
            torch_dtype=self.dtype,
            safety_checker=None,
            requires_safety_checker=False
        )
        
        # Move to device
        self.pipeline = self.pipeline.to(self.device)
        
        # Use DPM++ solver for better quality/speed
        self.pipeline.scheduler = DPMSolverMultistepScheduler.from_config(
            self.pipeline.scheduler.config,
            use_karras_sigmas=True
        )
        
        # MPS optimizations: upcast VAE to float32
        if self.device == "mps":
            try:
                self.pipeline.vae.to(dtype=torch.float32)
                logger.info("Upcasted VAE to float32 for MPS stability")
            except Exception as e:
                logger.warning(f"Could not upcast VAE: {e}")
        
        # Memory optimizations
        try:
            self.pipeline.enable_attention_slicing(slice_size="auto")
            logger.info("Enabled attention slicing")
        except Exception as e:
            logger.warning(f"Could not enable attention slicing: {e}")
        
        try:
            self.pipeline.enable_vae_slicing()
            logger.info("Enabled VAE slicing")
        except Exception as e:
            logger.warning(f"Could not enable VAE slicing: {e}")
        
        logger.info("Pipeline loaded successfully")
    
    @torch.inference_mode()
    def colorize(
        self,
        image: Image.Image,
        control_image: Image.Image,
        mask: Image.Image | None,
        prompt: str,
        negative_prompt: str,
        steps: int = 18,
        guidance_scale: float = 4.5,
        strength: float = 0.55,
        controlnet_conditioning_scale: float = 0.8,
        seed: int | None = None,
        **kwargs
    ) -> Image.Image:
        """
        Colorize a manga page using SD1.5 + ControlNet.
        
        Args:
            image: Preprocessed manga page (RGB)
            control_image: Lineart extracted from manga page (RGB)
            mask: Optional text protection mask
            prompt: Positive prompt
            negative_prompt: Negative prompt
            steps: Number of inference steps
            guidance_scale: Guidance scale
            strength: Denoise strength
            controlnet_conditioning_scale: ControlNet influence
            seed: Random seed for reproducibility
            
        Returns:
            Colored manga page
        """
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded. Call load_models() first.")
        
        # Ensure control_image matches image size exactly
        if control_image.size != image.size:
            logger.warning(f"Control image size {control_image.size} doesn't match image size {image.size}. Resizing...")
            control_image = control_image.resize(image.size, Image.LANCZOS)
        
        # Verify dimensions are multiples of 8
        w, h = image.size
        if w % 8 != 0 or h % 8 != 0:
            logger.warning(f"Image dimensions {w}x{h} not multiples of 8. Adjusting...")
            new_w = w - (w % 8)
            new_h = h - (h % 8)
            image = image.resize((new_w, new_h), Image.LANCZOS)
            control_image = control_image.resize((new_w, new_h), Image.LANCZOS)
            logger.info(f"Adjusted to {new_w}x{new_h}")
        
        # Set seed for reproducibility
        if seed is not None:
            generator = torch.Generator(device=self.device).manual_seed(seed)
        else:
            generator = None
        
        # Progress callback wrapper
        def step_callback(pipe, step_index, timestep, callback_kwargs):
            if self.progress_callback:
                self.progress_callback('colorizing', step_index + 1, steps)
            return callback_kwargs
        
        # Run img2img with ControlNet
        result = self.pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=image,
            control_image=control_image,
            num_inference_steps=steps,
            strength=strength,
            guidance_scale=guidance_scale,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
            generator=generator,
            callback_on_step_end=step_callback if self.progress_callback else None,
            callback_on_step_end_tensor_inputs=["latents"] if self.progress_callback else None,
        ).images[0]
        
        # Apply text protection mask if provided
        if mask is not None:
            import numpy as np
            coverage = (np.array(mask) > 0).mean()
            if coverage <= 0.30:  # Only apply if mask isn't too aggressive
                result = Image.composite(image, result, mask)
                logger.info(f"Applied text protection mask (coverage={coverage:.2%})")
            else:
                logger.warning(f"Skipping mask (coverage={coverage:.2%} too high)")
        
        # Clear MPS cache
        if self.device == "mps":
            try:
                torch.mps.empty_cache()
                logger.debug("Cleared MPS cache")
            except Exception as e:
                logger.warning(f"Could not clear MPS cache: {e}")
        
        return result
