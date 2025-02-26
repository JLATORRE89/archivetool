# tests/test_archiver.py
import pytest
import os
import shutil
import tempfile
from unittest.mock import Mock, patch, MagicMock
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO
import base64
import json
from pathlib import Path
from archiver.core import WebsiteArchiver
import requests
import gzip

@pytest.fixture
def temp_dir():
    """Create and clean up a temporary directory"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)

@pytest.fixture
def archiver(temp_dir):
    """Create a test archiver instance"""
    return WebsiteArchiver(
        base_url="https://example.com",
        output_dir=temp_dir,
        max_threads=2,
        compress_images=True,
        wait_for_ajax=True
    )

@pytest.fixture
def sample_image():
    """Create a sample test image"""
    img = Image.new('RGB', (100, 100), color='red')
    img_io = BytesIO()
    img.save(img_io, 'JPEG')
    img_io.seek(0)
    return img_io.getvalue()

@pytest.fixture
def sample_large_image():
    """Create a sample large test image"""
    img = Image.new('RGB', (2000, 2000), color='blue')
    img_io = BytesIO()
    img.save(img_io, 'JPEG', quality=100)
    img_io.seek(0)
    return img_io.getvalue()

@pytest.fixture
def sample_html():
    """Create a sample HTML content"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <link rel="stylesheet" href="/styles.css">
        <script src="/script.js"></script>
    </head>
    <body>
        <img src="/image.jpg">
        <div class="loading"></div>
        <a href="/page2.html">Link</a>
    </body>
    </html>
    """

@pytest.fixture
def mock_responses():
    """Create mock responses for different content types"""
    return {
        'html': Mock(
            content=b'<html><body>Test</body></html>',
            text='<html><body>Test</body></html>',
            headers={'content-type': 'text/html'},
            status_code=200,
            ok=True
        ),
        'image': Mock(
            content=b'fake-image-data',
            headers={'content-type': 'image/jpeg'},
            status_code=200,
            ok=True
        ),
        'css': Mock(
            content=b'body { color: red; }',
            text='body { color: red; }',
            headers={'content-type': 'text/css'},
            status_code=200,
            ok=True
        ),
        'js': Mock(
            content=b'console.log("test");',
            text='console.log("test");',
            headers={'content-type': 'application/javascript'},
            status_code=200,
            ok=True
        )
    }

class TestWebsiteArchiver:
    """Test suite for WebsiteArchiver"""

    def test_initialization(self, archiver, temp_dir):
        """Test archiver initialization"""
        assert archiver.base_url == "https://example.com"
        assert archiver.domain == "example.com"
        assert archiver.compress_images is True
        assert archiver.wait_for_ajax is True
        assert archiver.output_dir == temp_dir
        assert os.path.exists(os.path.join(temp_dir, "logs"))
        assert os.path.exists(os.path.join(temp_dir, "logs", "archiver.log"))

    @pytest.mark.parametrize("url,expected", [
        ("https://example.com", True),
        ("https://example.com/page.html", True),
        ("https://other.com", False),
        ("https://example.com/test.pdf", False),
        ("https://example.com/test.exe", False),
    ])
    def test_should_download(self, archiver, url, expected):
        """Test URL filtering logic"""
        assert archiver._should_download(url) == expected

    def test_image_compression(self, archiver, sample_image, sample_large_image):
        """Test image compression functionality"""
        # Test with small image
        compressed_small = archiver.compress_image(sample_image)
        assert len(compressed_small) <= len(sample_image)
        
        # Test with large image
        compressed_large = archiver.compress_image(sample_large_image)
        assert len(compressed_large) < len(sample_large_image)
        assert len(compressed_large) <= archiver.max_image_size_kb * 1024

        # Test with invalid image
        invalid_image = b"not an image"
        result = archiver.compress_image(invalid_image)
        assert result == invalid_image

    @patch('requests.get')
    def test_process_image_tag(self, mock_get, archiver, sample_image):
        """Test processing of image tags"""
        mock_get.return_value = Mock(
            content=sample_image,
            headers={'content-type': 'image/jpeg'},
            status_code=200,
            ok=True
        )

        soup = BeautifulSoup('<img src="/test.jpg">', 'html.parser')
        img_tag = soup.find('img')
        
        archiver._process_image_tag("https://example.com", img_tag)
        
        assert img_tag['src'].startswith('data:image/jpeg;base64,')
        assert len(img_tag['src']) > 0

    @patch('selenium.webdriver.Chrome')
    def test_ajax_handling(self, mock_chrome, archiver, sample_html):
        """Test AJAX content capture"""
        # Mock Selenium driver
        mock_driver = MagicMock()
        mock_driver.page_source = sample_html
        mock_driver.get_log.return_value = []
        mock_chrome.return_value = mock_driver

        # Test AJAX capture
        result = archiver.capture_ajax_content("https://example.com")
        assert result == sample_html
        assert mock_driver.get.called_with("https://example.com")

    @patch('requests.get')
    def test_process_css(self, mock_get, archiver, mock_responses):
        """Test CSS processing"""
        mock_get.return_value = mock_responses['css']

        soup = BeautifulSoup(
            '<link rel="stylesheet" href="/styles.css">', 
            'html.parser'
        )
        link_tag = soup.find('link')
        
        archiver._process_css_tag("https://example.com", link_tag)
        
        # Check if link was converted to style
        assert soup.find('style') is not None
        assert soup.find('link') is None

    def test_save_html_page(self, archiver, sample_html):
        """Test HTML page saving"""
        url = "https://example.com/test.html"
        archiver._save_html_page(url, sample_html)
        
        output_path = os.path.join(archiver.output_dir, "test.html")
        assert os.path.exists(output_path)
        
        with open(output_path, 'r') as f:
            saved_content = f.read()
        assert saved_content == sample_html

    def test_save_compressed_html(self, archiver):
        """Test HTML compression for large pages"""
        large_html = "x" * 200 * 1024  # 200KB of content
        url = "https://example.com/large.html"
        
        archiver._save_html_page(url, large_html)
        
        output_path = os.path.join(archiver.output_dir, "large.html.gz")
        assert os.path.exists(output_path)
        
        with gzip.open(output_path, 'rt') as f:
            saved_content = f.read()
        assert saved_content == large_html

    @patch('requests.get')
    def test_full_page_processing(self, mock_get, archiver, mock_responses, sample_html):
        """Test complete page processing"""
        def mock_get_response(*args, **kwargs):
            url = args[0]
            if url.endswith('.html'):
                return mock_responses['html']
            elif url.endswith('.jpg'):
                return mock_responses['image']
            elif url.endswith('.css'):
                return mock_responses['css']
            elif url.endswith('.js'):
                return mock_responses['js']
            return mock_responses['html']

        mock_get.side_effect = mock_get_response

        # Process a complete page
        url = "https://example.com/page.html"
        archiver._process_url(url, None)

        # Verify files were saved
        assert os.path.exists(os.path.join(archiver.output_dir, "page.html"))
        assert len(os.listdir(os.path.join(archiver.output_dir, "logs"))) > 0

    def test_error_handling(self, archiver):
        """Test error handling and logging"""
        # Try to process a non-existent URL
        url = "https://example.com/nonexistent"
        archiver._process_url(url, None)
        
        # Check if error was logged
        log_path = os.path.join(archiver.output_dir, "logs", "archiver.log")
        with open(log_path, 'r') as f:
            log_content = f.read()
        assert "Error processing" in log_content

if __name__ == "__main__":
    pytest.main([__file__])