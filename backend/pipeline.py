"""
Stable Diffusion + ControlNet Pipeline.
Uses img2img for proper colorization from grayscale input.
"""
import logging
import torch
from PIL import Image

from diffusers import (
    ControlNetModel,
    StableDiffusionControlNetImg2ImgPipeline,
    StableDiffusionXLControlNetImg2ImgPipeline,
    EulerAncestralDiscreteScheduler,
)

logger = logging.getLogger(__name__)


class ColorizationPipeline:
    """
    Diffusers-based Stable Diffusion + ControlNet pipeline.
    Supports SD1.5 + lineart anime, and optional SDXL + manga recolor.
    """

    SD15_BASE = "runwayml/stable-diffusion-v1-5"
    SD15_CONTROLNET = "lllyasviel/control_v11p_sd15s2_lineart_anime"

    SDXL_BASE = "stabilityai/stable-diffusion-xl-base-1.0"
    SDXL_CONTROLNET = "SubMaroon/ControlNet-manga-recolor"

    def __init__(self, model_manager):
        self.mm = model_manager
        self.pipeline = None
        self.mode = "sd15"  # "sd15" or "sdxl"

    def initialize_pipeline(self, model_name: str = "sd15"):
        """
        Initialize the SD+ControlNet pipeline.
        
        Args:
            model_name: "sd15" (default, fast) or "sdxl" (higher quality, slower)
        """
        self.mode = model_name.lower().strip()

        cached = self.mm.get_cached_pipeline(self.mode)
        if cached is not None:
            self.pipeline = cached
            logger.info(f"Loaded cached pipeline: {self.mode}")
            return

        device = self.mm.device
        dtype = self.mm.dtype

        if self.mode == "sdxl":
            logger.info("Initializing SDXL + Manga Recolor ControlNet...")
            controlnet = ControlNetModel.from_pretrained(
                self.SDXL_CONTROLNET, torch_dtype=dtype
            )

            pipe = StableDiffusionXLControlNetImg2ImgPipeline.from_pretrained(
                self.SDXL_BASE,
                controlnet=controlnet,
                torch_dtype=dtype,
                safety_checker=None,
                requires_safety_checker=False,
            )
        else:
            logger.info("Initializing SD1.5 + Lineart Anime ControlNet...")
            controlnet = ControlNetModel.from_pretrained(
                self.SD15_CONTROLNET, torch_dtype=dtype
            )

            pipe = StableDiffusionControlNetImg2ImgPipeline.from_pretrained(
                self.SD15_BASE,
                controlnet=controlnet,
                torch_dtype=dtype,
                safety_checker=None,
                requires_safety_checker=False,
            )

        pipe.scheduler = EulerAncestralDiscreteScheduler.from_config(pipe.scheduler.config)

        # Memory optimizations (critical for Mac)
        pipe.enable_attention_slicing()
        
        # VAE tiling causes contiguity issues on MPS - skip it
        # MPS handles memory well enough with just attention slicing
        if device != "mps":
            try:
                pipe.vae.enable_tiling()  # Use new API
            except Exception:
                pass

        pipe = pipe.to(device)

        self.pipeline = pipe
        self.mm.cache_pipeline(self.mode, pipe)

        logger.info(f"Pipeline ready ✅ mode={self.mode} device={device}")

    @torch.inference_mode()
    def colorize(
        self,
        image: Image.Image,
        control_image: Image.Image,
        mask: Image.Image | None,
        prompt: str,
        negative_prompt: str,
        progress_callback=None,
        steps: int = 25,
        guidance_scale: float = 7.0,
        strength: float = 0.45,
        controlnet_conditioning_scale: float = 1.0,
        seed: int | None = None,
        **kwargs
    ) -> Image.Image:
        """
        Colorize a manga page using SD+ControlNet img2img.
        
        Args:
            image: Input grayscale/bw image
            control_image: ControlNet conditioning (lineart)
            mask: Optional text protection mask
            prompt: Text prompt for colorization
            negative_prompt: Negative prompt
            progress_callback: Optional progress callback
            steps: Number of inference steps
            guidance_scale: CFG scale
            strength: How much to transform (0.0-1.0)
            controlnet_conditioning_scale: ControlNet influence
            seed: Random seed for reproducibility
            
        Returns:
            Colorized PIL Image
        """
        if self.pipeline is None:
            raise RuntimeError("Pipeline not initialized. Call initialize_pipeline().")

        generator = None
        if seed is not None:
            generator = torch.Generator(device=self.mm.device).manual_seed(seed)

        # Run img2img with ControlNet
        result = self.pipeline(
            prompt=prompt,
            negative_prompt=negative_prompt,
            image=image,
            control_image=control_image,
            num_inference_steps=steps,
            guidance_scale=guidance_scale,
            strength=strength,
            controlnet_conditioning_scale=controlnet_conditioning_scale,
            generator=generator,
        ).images[0]

        # Apply text protection mask if provided (and valid)
        if mask is not None:
            # extra safety: skip if mask somehow became huge
            import numpy as np
            cov = (np.array(mask) > 0).mean()
            if cov <= 0.30:
                result = Image.composite(image, result, mask)
                logger.info(f"Applied text protection mask (coverage={cov:.2%})")
            else:
                logger.warning(f"Skipping mask apply (coverage={cov:.2%})")

        return result

    def unload(self):
        """Unload the pipeline from memory."""
        self.pipeline = None
