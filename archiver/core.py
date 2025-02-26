# archiver/core.py
import os
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import threading
from queue import Queue
import time
from pathlib import Path
import mimetypes
import re
import base64
from io import BytesIO
import gzip
import zlib
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json
from PIL import Image

class WebsiteArchiver:
    def __init__(self, base_url, output_dir=None, max_threads=5, compress_images=True, 
                 wait_for_ajax=True, max_image_size_kb=500, compression_quality=95):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.output_dir = output_dir or os.path.join(os.path.expanduser("~"), "website_archives")
        self.visited_urls = set()
        self.queue = Queue()
        self.max_threads = max_threads
        self.active = True
        self.compress_images = compress_images
        self.wait_for_ajax = wait_for_ajax
        self.ajax_data = {}
        self.max_image_size_kb = max_image_size_kb
        self.compression_quality = compression_quality
        
        # Setup logging
        self.setup_logging()
        
        # Initialize webdriver for AJAX handling if needed
        if self.wait_for_ajax:
            self.setup_webdriver()

    def setup_webdriver(self):
        """Initialize Selenium WebDriver with appropriate options"""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--enable-javascript")
            chrome_options.add_argument("--window-size=1920,1080")
            
            self.driver = webdriver.Chrome(options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.logger.info("WebDriver initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize WebDriver: {str(e)}")
            self.wait_for_ajax = False
            self.driver = None

    def setup_logging(self):
        """Configure logging system"""
        try:
            log_dir = os.path.join(self.output_dir, "logs")
            os.makedirs(log_dir, exist_ok=True)
            
            self.logger = logging.getLogger("website_archiver")
            self.logger.setLevel(logging.INFO)
            
            # File handler for detailed logging
            fh = logging.FileHandler(os.path.join(log_dir, "archiver.log"))
            fh.setLevel(logging.INFO)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
            
            # Error log file
            eh = logging.FileHandler(os.path.join(log_dir, "error.log"))
            eh.setLevel(logging.ERROR)
            eh.setFormatter(formatter)
            self.logger.addHandler(eh)
            
        except Exception as e:
            print(f"Failed to setup logging: {str(e)}")
            raise

    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'driver') and self.driver:
            try:
                self.driver.quit()
            except:
                pass

    def start_archive(self, progress_callback=None):
        """Start the archiving process"""
        try:
            self.visited_urls.clear()
            self.queue.put(self.base_url)
            
            # Create worker threads
            threads = []
            for _ in range(self.max_threads):
                t = threading.Thread(target=self._worker, args=(progress_callback,))
                t.daemon = True
                t.start()
                threads.append(t)
            
            # Wait for queue to empty
            self.queue.join()
            
            # Stop threads
            self.active = False
            for t in threads:
                t.join()
                
            self.logger.info(f"Archive complete. Total pages: {len(self.visited_urls)}")
            return True
            
        except Exception as e:
            self.logger.error(f"Archive failed: {str(e)}")
            return False
            
        finally:
            if hasattr(self, 'driver') and self.driver:
                self.driver.quit()
    def _worker(self, progress_callback=None):
        """Worker thread for processing URLs"""
        while self.active:
            try:
                url = self.queue.get(timeout=1)
                if url not in self.visited_urls:
                    self._process_url(url, progress_callback)
                self.queue.task_done()
            except Queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {str(e)}")
                self.queue.task_done()

    def capture_ajax_content(self, url):
        """Capture dynamically loaded content using Selenium"""
        if not self.driver:
            return None
            
        try:
            self.driver.get(url)
            
            # Wait for initial page load
            time.sleep(2)
            
            # Wait for dynamic content
            try:
                WebDriverWait(self.driver, 10).until(
                    lambda driver: driver.execute_script("""
                        return (
                            // jQuery
                            (typeof jQuery === 'undefined' || jQuery.active === 0) &&
                            // Fetch API
                            !window._fetchActive &&
                            // XHR
                            !window._xhrActive
                        );
                    """)
                )
            except:
                self.logger.warning(f"Timeout waiting for dynamic content on {url}")
            
            # Inject tracking for future XHR/Fetch requests
            self.driver.execute_script("""
                // Track XHR requests
                window._xhrActive = false;
                (function(open) {
                    XMLHttpRequest.prototype.open = function() {
                        window._xhrActive = true;
                        this.addEventListener('loadend', function() {
                            window._xhrActive = false;
                        });
                        return open.apply(this, arguments);
                    };
                })(XMLHttpRequest.prototype.open);
                
                // Track Fetch requests
                window._fetchActive = false;
                (function(fetch) {
                    window.fetch = function() {
                        window._fetchActive = true;
                        return fetch.apply(this, arguments).finally(() => {
                            window._fetchActive = false;
                        });
                    };
                })(window.fetch);
            """)
            
            # Capture network requests
            ajax_urls = set()
            performance_logs = self.driver.get_log('performance')
            
            for log in performance_logs:
                if 'Network.responseReceived' in str(log):
                    try:
                        url_data = json.loads(log['message'])
                        if 'params' in url_data and 'response' in url_data['params']:
                            response_url = url_data['params']['response']['url']
                            if self._should_download(response_url) and '.js' not in response_url:
                                ajax_urls.add(response_url)
                    except:
                        continue
            
            # Get content for each AJAX URL
            for ajax_url in ajax_urls:
                try:
                    response = requests.get(ajax_url)
                    if response.ok:
                        self.ajax_data[ajax_url] = response.text
                except Exception as e:
                    self.logger.error(f"Error capturing AJAX content from {ajax_url}: {str(e)}")
            
            # Get final HTML after JavaScript execution
            final_html = self.driver.page_source
            
            # Look for any remaining dynamic placeholders
            soup = BeautifulSoup(final_html, 'html.parser')
            loading_elements = soup.find_all(class_=re.compile(r'loading|skeleton|placeholder'))
            if loading_elements:
                self.logger.warning(f"Found {len(loading_elements)} potentially unloaded elements on {url}")
            
            return final_html
            
        except Exception as e:
            self.logger.error(f"Error capturing AJAX content: {str(e)}")
            return None

    def compress_image(self, img_data):
        """Compress image data while maintaining quality"""
        try:
            # Convert binary data to PIL Image
            img = Image.open(BytesIO(img_data))
            
            # If image is already small enough, return original
            if len(img_data) < self.max_image_size_kb * 1024:
                return img_data
            
            # Calculate target size
            target_size = self.max_image_size_kb * 1024
            quality = self.compression_quality
            output = BytesIO()
            
            # Try different quality levels to get desired size
            while quality > 30:  # Don't go below quality 30
                output.seek(0)
                output.truncate()
                
                if img.mode in ('RGBA', 'LA'):
                    # Handle transparency
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[-1])
                    background.save(output, 'JPEG', 
                                 quality=quality, 
                                 optimize=True,
                                 progressive=True)
                else:
                    img.save(output, 'JPEG', 
                           quality=quality, 
                           optimize=True,
                           progressive=True)
                
                if output.tell() <= target_size:
                    break
                
                quality -= 5
            
            compressed_size = output.tell()
            original_size = len(img_data)
            self.logger.info(f"Compressed image from {original_size/1024:.1f}KB to {compressed_size/1024:.1f}KB (quality={quality})")
            
            return output.getvalue()
            
        except Exception as e:
            self.logger.error(f"Error compressing image: {str(e)}")
            return img_data
    def _process_url(self, url, progress_callback=None):
        """Process a single URL"""
        if url in self.visited_urls or not url.startswith(self.base_url):
            return

        try:
            self.visited_urls.add(url)
            
            if self.wait_for_ajax:
                # Get content with dynamic AJAX handling
                html_content = self.capture_ajax_content(url)
                if html_content:
                    modified_html = self._process_html(url, html_content)
                    self._save_html_page(url, modified_html)
                else:
                    # Fallback to regular request
                    response = requests.get(url, timeout=30)
                    response.raise_for_status()
                    self._handle_response(url, response)
            else:
                # Regular request without AJAX handling
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                self._handle_response(url, response)

            if progress_callback:
                progress_callback(len(self.visited_urls), url)
                
        except Exception as e:
            self.logger.error(f"Error processing {url}: {str(e)}")

    def _handle_response(self, url, response):
        """Handle different types of responses"""
        content_type = response.headers.get('content-type', '').split(';')[0]
        
        if 'text/html' in content_type:
            modified_html = self._process_html(url, response.text)
            self._save_html_page(url, modified_html)
        else:
            self._save_asset(url, response.content)

    def _process_html(self, base_url, html_content):
        """Process HTML content and embedded resources"""
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Process images
            for img in soup.find_all('img'):
                self._process_image_tag(base_url, img)
            
            # Process CSS
            for link in soup.find_all('link', rel='stylesheet'):
                self._process_css_tag(base_url, link)
            
            # Process JavaScript
            for script in soup.find_all('script', src=True):
                self._process_script_tag(base_url, script)
            
            # Process other resources
            for link in soup.find_all('link', rel=['icon', 'shortcut icon']):
                self._process_link_tag(base_url, link)
            
            return str(soup)
            
        except Exception as e:
            self.logger.error(f"Error processing HTML from {base_url}: {str(e)}")
            return html_content

    def _process_image_tag(self, base_url, img):
        """Process and embed an image tag"""
        try:
            src = img.get('src')
            if not src:
                return
                
            absolute_url = urljoin(base_url, src)
            
            if not absolute_url.startswith(self.base_url):
                return
                
            response = requests.get(absolute_url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if not content_type:
                content_type, _ = mimetypes.guess_type(absolute_url)
            
            if not content_type:
                content_type = 'image/jpeg'
            
            # Compress image if enabled
            if self.compress_images:
                img_data = self.compress_image(response.content)
            else:
                img_data = response.content
            
            # Encode as base64
            encoded = base64.b64encode(img_data).decode('utf-8')
            data_url = f"data:{content_type};base64,{encoded}"
            
            img['src'] = data_url
            self.logger.info(f"Processed image: {absolute_url}")
            
        except Exception as e:
            self.logger.error(f"Error processing image {src}: {str(e)}")

    def _process_css_tag(self, base_url, link):
        """Process and embed a CSS stylesheet"""
        try:
            href = link.get('href')
            if not href:
                return
                
            absolute_url = urljoin(base_url, href)
            
            if not absolute_url.startswith(self.base_url):
                return
                
            # Download CSS
            response = requests.get(absolute_url, timeout=30)
            response.raise_for_status()
            
            # Process CSS content to handle url() references
            css_content = response.text
            css_content = self._process_css_urls(base_url, css_content)
            
            # Create style tag
            style_tag = BeautifulSoup('', 'html.parser').new_tag('style')
            style_tag.string = css_content
            
            # Replace link with style
            link.replace_with(style_tag)
            
            self.logger.info(f"Processed CSS: {absolute_url}")
            
        except Exception as e:
            self.logger.error(f"Error processing CSS {href}: {str(e)}")

    def _process_css_urls(self, base_url, css_content):
        """Process URLs within CSS content"""
        try:
            url_pattern = re.compile(r'url\([\'"]?([^\'"()]+)[\'"]?\)')
            
            def replace_url(match):
                url = match.group(1)
                absolute_url = urljoin(base_url, url)
                
                if not absolute_url.startswith(self.base_url):
                    return f'url("{url}")'
                
                try:
                    response = requests.get(absolute_url, timeout=30)
                    response.raise_for_status()
                    
                    content_type = response.headers.get('content-type', '')
                    if not content_type:
                        content_type, _ = mimetypes.guess_type(absolute_url)
                    
                    if not content_type:
                        return f'url("{url}")'
                    
                    encoded = base64.b64encode(response.content).decode('utf-8')
                    data_url = f"data:{content_type};base64,{encoded}"
                    
                    return f'url("{data_url}")'
                    
                except Exception:
                    return f'url("{url}")'
            
            return url_pattern.sub(replace_url, css_content)
            
        except Exception as e:
            self.logger.error(f"Error processing CSS URLs: {str(e)}")
            return css_content

    def _process_script_tag(self, base_url, script):
        """Process and embed a JavaScript file"""
        try:
            src = script.get('src')
            if not src:
                return
                
            absolute_url = urljoin(base_url, src)
            
            if not absolute_url.startswith(self.base_url):
                return
                
            # Download JavaScript
            response = requests.get(absolute_url, timeout=30)
            response.raise_for_status()
            
            # Update script content
            script.string = response.text
            del script['src']
            
            self.logger.info(f"Processed JavaScript: {absolute_url}")
            
        except Exception as e:
            self.logger.error(f"Error processing script {src}: {str(e)}")

    def _process_link_tag(self, base_url, link):
        """Process and embed other linked resources"""
        try:
            href = link.get('href')
            if not href:
                return
                
            absolute_url = urljoin(base_url, href)
            
            if not absolute_url.startswith(self.base_url):
                return
                
            # Download resource
            response = requests.get(absolute_url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            if not content_type:
                content_type, _ = mimetypes.guess_type(absolute_url)
            
            if not content_type:
                return
            
            # Encode as base64
            encoded = base64.b64encode(response.content).decode('utf-8')
            data_url = f"data:{content_type};base64,{encoded}"
            
            link['href'] = data_url
            self.logger.info(f"Processed link resource: {absolute_url}")
            
        except Exception as e:
            self.logger.error(f"Error processing link {href}: {str(e)}")

    def _save_html_page(self, url, content):
        """Save processed HTML page"""
        try:
            # Insert AJAX data if available
            if self.ajax_data:
                ajax_script = f"""
                <script>
                    window.ajaxData = {json.dumps(self.ajax_data)};
                </script>
                """
                content = content.replace('</head>', f'{ajax_script}</head>')
            
            relative_path = self._url_to_filepath(url)
            full_path = os.path.join(self.output_dir, relative_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            # Compress HTML if it's large
            if len(content.encode('utf-8')) > 1024 * 100:  # Compress if > 100KB
                compressed = gzip.compress(content.encode('utf-8'))
                with open(f"{full_path}.gz", 'wb') as f:
                    f.write(compressed)
            else:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
            self.logger.info(f"Saved HTML page: {url}")
            
        except Exception as e:
            self.logger.error(f"Error saving HTML page {url}: {str(e)}")

    def _save_asset(self, url, content):
        """Save a non-HTML asset"""
        try:
            relative_path = self._url_to_filepath(url)
            full_path = os.path.join(self.output_dir, relative_path)
            
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            with open(full_path, 'wb') as f:
                f.write(content)
                
            self.logger.info(f"Saved asset: {url}")
            
        except Exception as e:
            self.logger.error(f"Error saving asset {url}: {str(e)}")

    def _url_to_filepath(self, url):
        """Convert URL to local file path"""
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            path = 'index.html'
        elif not os.path.splitext(path)[1]:
            path = os.path.join(path, 'index.html')
            
        return path

    def _should_download(self, url):
        """Check if URL should be downloaded"""
        parsed = urlparse(url)
        return (
            parsed.netloc == self.domain and
            url not in self.visited_urls and
            not any(ext in url for ext in ['.pdf', '.zip', '.exe'])
        )