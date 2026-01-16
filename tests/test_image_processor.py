"""
Unit tests for Image Processor
"""
import unittest
from pathlib import Path
import sys

import numpy as np
from PIL import Image

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.image_processor import ImageProcessor


class TestImageProcessor(unittest.TestCase):
    """Test cases for ImageProcessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = ImageProcessor()
        
        # Create a test image
        self.test_image = Image.new('RGB', (800, 600), color='white')
    
    def test_calculate_resize_dimensions(self):
        """Test resize dimension calculation"""
        # Test image smaller than max
        new_size = self.processor.calculate_resize_dimensions((512, 512), max_size=1024)
        self.assertEqual(new_size, (512, 512))
        
        # Test image larger than max
        new_size = self.processor.calculate_resize_dimensions((2000, 1500), max_size=1024)
        self.assertLessEqual(max(new_size), 1024)
        
        # Check dimensions are multiples of 8
        self.assertEqual(new_size[0] % 8, 0)
        self.assertEqual(new_size[1] % 8, 0)
    
    def test_preprocess_for_sd(self):
        """Test SD preprocessing"""
        processed, metadata = self.processor.preprocess_for_sd(self.test_image)
        
        # Check metadata
        self.assertIn('original_size', metadata)
        self.assertIn('processing_size', metadata)
        self.assertEqual(metadata['original_size'], (800, 600))
        
        # Check image is RGB
        self.assertEqual(processed.mode, 'RGB')
    
    def test_enhance_colors(self):
        """Test color enhancement"""
        enhanced = self.processor.enhance_colors(self.test_image)
        
        # Check output is valid image
        self.assertIsInstance(enhanced, Image.Image)
        self.assertEqual(enhanced.mode, 'RGB')
        self.assertEqual(enhanced.size, self.test_image.size)
    
    def test_composite_with_mask(self):
        """Test image compositing with mask"""
        # Create test images
        colored = Image.new('RGB', (100, 100), color='red')
        original = Image.new('RGB', (100, 100), color='blue')
        mask = Image.new('L', (100, 100), color=128)
        
        # Composite
        result = self.processor.composite_with_mask(colored, original, mask)
        
        # Check output
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, (100, 100))
    
    def test_is_valid_image(self):
        """Test image format validation"""
        self.assertTrue(self.processor.is_valid_image('test.png'))
        self.assertTrue(self.processor.is_valid_image('test.jpg'))
        self.assertTrue(self.processor.is_valid_image('test.jpeg'))
        self.assertFalse(self.processor.is_valid_image('test.txt'))
        self.assertFalse(self.processor.is_valid_image('test.pdf'))


if __name__ == '__main__':
    unittest.main()
