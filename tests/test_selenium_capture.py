# tests/test_selenium_capture.py
import unittest
import os
import shutil
import tempfile
from unittest.mock import patch
from bs4 import BeautifulSoup

from archiver.core import WebsiteArchiver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


class MockResponse:
    def __init__(self, text, content=None, status_code=200, headers=None):
        self.text = text
        self.content = content if content else text.encode('utf-8')
        self.status_code = status_code
        self.ok = status_code < 400
        self.headers = headers or {'content-type': 'text/html'}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP Error: {self.status_code}")


class TestDynamicContentCapture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        """Set up test resources once for all tests"""
        # Create a simple test server directory
        cls.test_dir = tempfile.mkdtemp()
        
        # Create a temporary HTML file with dynamic content
        cls.html_path = os.path.join(cls.test_dir, "test_dynamic.html")
        with open(cls.html_path, "w") as f:
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Dynamic Content Test</title>
                <script>
                    // This will create content after the page loads
                    window.onload = function() {
                        setTimeout(function() {
                            const div = document.createElement('div');
                            div.id = 'dynamic-content';
                            div.innerHTML = '<h2>Dynamically Added Content</h2><p>This content was added by JavaScript.</p>';
                            document.body.appendChild(div);
                            
                            // Also update an existing element
                            document.getElementById('loading').innerText = 'Content Loaded!';
                        }, 500);
                    }
                </script>
            </head>
            <body>
                <h1>Dynamic Content Test</h1>
                <div id="loading">Loading...</div>
                <!-- Dynamic content will be added here -->
            </body>
            </html>
            """)
        
        # Setup webdriver for testing
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        try:
            cls.driver = webdriver.Chrome(options=options)
            cls.selenium_available = True
        except Exception as e:
            print(f"Selenium webdriver not available: {e}")
            cls.selenium_available = False

    @classmethod
    def tearDownClass(cls):
        """Clean up test resources"""
        # Remove the test directory
        shutil.rmtree(cls.test_dir)
        
        # Quit the webdriver if it was started
        if hasattr(cls, 'driver') and cls.driver:
            cls.driver.quit()

    def setUp(self):
        """Set up before each test"""
        # Create a temporary output directory for each test
        self.output_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up after each test"""
        # Remove the output directory
        shutil.rmtree(self.output_dir)

    @unittest.skipIf(not hasattr(TestDynamicContentCapture, 'selenium_available') or 
                    not TestDynamicContentCapture.selenium_available, 
                    "Selenium webdriver not available")
    def test_dynamic_content_captured(self):
        """Test that dynamically generated content is captured"""
        # Load the test HTML file
        file_url = f"file://{self.html_path}"
        self.driver.get(file_url)
        
        # Wait for the dynamic content to be added
        wait = WebDriverWait(self.driver, 10)
        wait.until(EC.presence_of_element_located((By.ID, "dynamic-content")))
        
        # Verify the dynamic content was added
        dynamic_content = self.driver.find_element(By.ID, "dynamic-content")
        self.assertIsNotNone(dynamic_content)
        self.assertIn("Dynamically Added Content", dynamic_content.text)
        
        # Verify the loading text was updated
        loading_element = self.driver.find_element(By.ID, "loading")
        self.assertEqual("Content Loaded!", loading_element.text)

    @patch('requests.get')
    @patch('archiver.core.WebsiteArchiver.capture_ajax_content')
    def test_archiver_processes_dynamic_content(self, mock_capture_ajax, mock_get):
        """Test that the archiver processes dynamic content correctly"""
        # Create a mock for the initial HTML
        initial_html = """
        <html><body>
            <h1>Initial Content</h1>
            <div id="loading">Loading...</div>
        </body></html>
        """
        
        # Create a mock for the dynamic HTML (after JavaScript execution)
        dynamic_html = """
        <html><body>
            <h1>Initial Content</h1>
            <div id="loading">Content Loaded!</div>
            <div id="dynamic-content">
                <h2>Dynamically Added Content</h2>
                <p>This content was added by JavaScript.</p>
            </div>
        </body></html>
        """
        
        # Setup our mocks
        mock_get.return_value = MockResponse(initial_html)
        mock_capture_ajax.return_value = dynamic_html
        
        # Create and run the archiver
        archiver = WebsiteArchiver("https://example.com", self.output_dir, wait_for_ajax=True)
        archiver.start_archive()
        
        # Check that the output file exists
        output_file = os.path.join(self.output_dir, "index.html")
        self.assertTrue(os.path.exists(output_file))
        
        # Check the content of the output file
        with open(output_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the content
        soup = BeautifulSoup(content, 'html.parser')
        
        # Check that the dynamic content is present
        dynamic_content = soup.find(id="dynamic-content")
        self.assertIsNotNone(dynamic_content)
        self.assertIn("Dynamically Added Content", dynamic_content.text)
        
        # Check that the loading text was updated
        loading_element = soup.find(id="loading")
        self.assertEqual("Content Loaded!", loading_element.text)

    def test_selenium_not_required_when_wait_for_ajax_false(self):
        """Test that selenium is not required when wait_for_ajax is False"""
        with patch('selenium.webdriver.Chrome', side_effect=Exception("No webdriver")):
            # This should not raise an exception because wait_for_ajax is False
            archiver = WebsiteArchiver("https://example.com", self.output_dir, wait_for_ajax=False)
            self.assertFalse(archiver.wait_for_ajax)
            self.assertIsNone(archiver.driver)

    @unittest.skipIf(not hasattr(TestDynamicContentCapture, 'selenium_available') or 
                    not TestDynamicContentCapture.selenium_available, 
                    "Selenium webdriver not available")
    def test_graceful_fallback_when_selenium_fails(self):
        """Test that archiver falls back gracefully when Selenium fails"""
        # Create a basic HTML file
        html_content = "<html><body><h1>Test Page</h1></body></html>"
        
        # Mock the Selenium driver to raise an exception
        with patch('selenium.webdriver.Chrome.get', side_effect=Exception("Selenium error")):
            # Setup a mock response for the requests fallback
            with patch('requests.get', return_value=MockResponse(html_content)):
                archiver = WebsiteArchiver("https://example.com", self.output_dir, wait_for_ajax=True)
                
                # This should not raise an exception despite Selenium failing
                archiver.start_archive()
                
                # Check that the output file exists
                output_file = os.path.join(self.output_dir, "index.html")
                self.assertTrue(os.path.exists(output_file))


if __name__ == '__main__':
    unittest.main()