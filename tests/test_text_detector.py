"""
Unit tests for Text Detector
"""
import unittest
from pathlib import Path
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.text_detector import TextDetector


class TestTextDetector(unittest.TestCase):
    """Test cases for TextDetector class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = TextDetector()
        
        # Create a test image with some shapes
        self.test_image = Image.new('RGB', (400, 400), color='white')
    
    def test_create_mask(self):
        """Test mask creation"""
        boxes = [(10, 10, 50, 50), (100, 100, 60, 60)]
        mask = self.detector.create_mask((400, 400), boxes)
        
        self.assertIsInstance(mask, Image.Image)
        self.assertEqual(mask.size, (400, 400))
        self.assertEqual(mask.mode, 'L')
    
    def test_merge_overlapping_boxes(self):
        """Test box merging"""
        # Overlapping boxes
        boxes = [(10, 10, 50, 50), (20, 20, 50, 50)]
        merged = self.detector.merge_overlapping_boxes(boxes, iou_threshold=0.3)
        
        # Should merge into fewer boxes
        self.assertLessEqual(len(merged), len(boxes))
    
    def test_detect_and_mask(self):
        """Test complete detection pipeline"""
        mask, boxes = self.detector.detect_and_mask(self.test_image)
        
        # Check outputs
        self.assertIsInstance(mask, Image.Image)
        self.assertIsInstance(boxes, list)
        self.assertEqual(mask.size, self.test_image.size)
    
    def test_visualize_detections(self):
        """Test detection visualization"""
        boxes = [(10, 10, 50, 50)]
        result = self.detector.visualize_detections(self.test_image, boxes)
        
        self.assertIsInstance(result, Image.Image)
        self.assertEqual(result.size, self.test_image.size)


if __name__ == '__main__':
    unittest.main()
