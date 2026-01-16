"""
Model Manager for Stable Diffusion + ControlNet.
Handles device detection, dtype optimization, and pipeline caching.
"""
import torch
import logging

logger = logging.getLogger(__name__)


class ModelManager:
    """Manages ML models, devices, and pipeline caching."""
    
    def __init__(self):
        self.device = self._detect_device()
        self.dtype = torch.float16 if self.device == "mps" else torch.float32

        # Helps avoid some MPS ops failures
        if self.device == "mps":
            try:
                import os
                os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")
            except Exception:
                pass

        self._pipeline_cache = {}

        logger.info(f"ModelManager: device={self.device}, dtype={self.dtype}")

    def _detect_device(self) -> str:
        """Auto-detect best available device."""
        if torch.backends.mps.is_available():
            return "mps"
        return "cpu"

    def get_model_info(self) -> dict:
        """Get current model configuration info."""
        return {
            "device": self.device,
            "dtype": str(self.dtype),
            "cached_pipelines": list(self._pipeline_cache.keys())
        }

    def cache_pipeline(self, key: str, pipeline_obj):
        """Cache a pipeline for reuse."""
        self._pipeline_cache[key] = pipeline_obj

    def get_cached_pipeline(self, key: str):
        """Retrieve cached pipeline if available."""
        return self._pipeline_cache.get(key)

    def clear_cache(self):
        """Clear all cached pipelines."""
        self._pipeline_cache.clear()
