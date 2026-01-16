"""
Text Detector - Speech bubble protection (FIXED).
Detects enclosed white regions (speech bubbles) and avoids masking the whole page.
"""
import numpy as np
from PIL import Image, ImageFilter
import logging
from collections import deque

logger = logging.getLogger(__name__)


class TextDetector:
    """
    Speech bubble protection mask generator.

    Old version was broken because it masked ALL white background.
    New version:
    - Finds white pixels
    - Flood-fills from image borders to remove background-connected white regions
    - Keeps ONLY enclosed white regions (speech bubbles)
    - Adds sanity check to avoid huge masks
    """

    def detect_and_mask(
        self,
        image: Image.Image,
        white_thresh: int = 245,
        max_coverage: float = 0.30,
    ):
        """
        Returns:
            (mask_image, boxes)
            mask_image: L mode, 255 = protect original, 0 = allow color
        """
        gray = np.array(image.convert("L"))
        h, w = gray.shape

        # Step 1: find very white pixels
        white = gray >= white_thresh

        # Step 2: flood-fill from borders to remove background-connected whites
        bg = np.zeros((h, w), dtype=bool)
        q = deque()

        # enqueue border white pixels
        for x in range(w):
            if white[0, x] and not bg[0, x]:
                bg[0, x] = True
                q.append((0, x))
            if white[h - 1, x] and not bg[h - 1, x]:
                bg[h - 1, x] = True
                q.append((h - 1, x))

        for y in range(h):
            if white[y, 0] and not bg[y, 0]:
                bg[y, 0] = True
                q.append((y, 0))
            if white[y, w - 1] and not bg[y, w - 1]:
                bg[y, w - 1] = True
                q.append((y, w - 1))

        # BFS 4-connected
        while q:
            y, x = q.popleft()
            for ny, nx in ((y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1)):
                if 0 <= ny < h and 0 <= nx < w:
                    if white[ny, nx] and not bg[ny, nx]:
                        bg[ny, nx] = True
                        q.append((ny, nx))

        # Step 3: speech bubbles = white regions NOT connected to the border background
        bubble = white & (~bg)

        # Step 4: sanity check – if coverage too large, skip masking entirely
        coverage = bubble.mean()
        logger.info(f"Text mask coverage: {coverage:.3f}")

        if coverage > max_coverage:
            logger.warning(
                f"Text mask too large ({coverage:.2%}). Skipping text protection."
            )
            return None, []

        # Convert to mask image
        mask = (bubble.astype(np.uint8) * 255)
        mask_img = Image.fromarray(mask, mode="L")

        # Expand & smooth a bit to cover bubble borders
        mask_img = mask_img.filter(ImageFilter.MaxFilter(5))
        mask_img = mask_img.filter(ImageFilter.GaussianBlur(1))

        return mask_img, []
