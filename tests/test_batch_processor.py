"""
Unit tests for Batch Processor
"""
import unittest
from pathlib import Path
import sys
import tempfile
import zipfile

from PIL import Image

sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.batch_processor import BatchProcessor


class TestBatchProcessor(unittest.TestCase):
    """Test cases for BatchProcessor class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.processor = BatchProcessor(output_dir=Path(self.temp_dir) / 'output')
        
        # Create test images
        self.test_images = []
        for i in range(3):
            img = Image.new('RGB', (100, 100), color='white')
            img_path = Path(self.temp_dir) / f'test_{i}.png'
            img.save(img_path)
            self.test_images.append(img_path)
    
    def test_is_image_file(self):
        """Test image file detection"""
        self.assertTrue(self.processor.is_image_file('test.png'))
        self.assertTrue(self.processor.is_image_file('test.jpg'))
        self.assertFalse(self.processor.is_image_file('test.txt'))
    
    def test_is_zip_file(self):
        """Test ZIP file detection"""
        self.assertTrue(self.processor.is_zip_file('test.zip'))
        self.assertFalse(self.processor.is_zip_file('test.png'))
    
    def test_find_images_in_directory(self):
        """Test image finding in directory"""
        images = self.processor.find_images_in_directory(self.temp_dir)
        self.assertEqual(len(images), 3)
    
    def test_create_output_zip(self):
        """Test ZIP creation"""
        zip_path = self.processor.create_output_zip(
            self.test_images,
            zip_name='test_output.zip'
        )
        
        self.assertTrue(zip_path.exists())
        self.assertTrue(zipfile.is_zipfile(zip_path))
    
    def test_get_input_files_single(self):
        """Test getting input files from single image"""
        files = self.processor.get_input_files(self.test_images[0])
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0], self.test_images[0])
    
    def test_get_input_files_directory(self):
        """Test getting input files from directory"""
        files = self.processor.get_input_files(self.temp_dir)
        self.assertEqual(len(files), 3)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)


if __name__ == '__main__':
    unittest.main()
