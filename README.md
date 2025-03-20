# Website Archiver

A Python application for creating self-contained offline archives of websites. Available in both GUI and CLI versions, with support for dynamic content and optimization features.

## Build Status: Broken

## Features

- Complete website downloading with asset preservation
- Multi-threaded architecture for faster downloads
- Dynamic content capture (AJAX/JavaScript)
- Image compression and optimization
- Resource inlining (CSS, JavaScript)
- Base64 encoding of assets
- Both GUI and CLI interfaces

## Choosing Your Interface

This tool offers two ways to run:

### GUI Version (Recommended for Desktop Users)
- Interactive graphical interface
- Easy to use
- Runs directly with Python
- Good for occasional use
- Visual progress and status updates

### CLI Version (Recommended for Automation/Servers)
- Command-line interface
- Runs in a container
- Good for scripts and automation
- No GUI dependencies needed
- Suitable for headless systems

## Quick Start - GUI Version

### Requirements
- Python 3.8 or higher
- pip (Python package installer)
- Tkinter (usually included with Python)

### Installation
```bash
# Clone repository
git clone https://github.com/JLATORRE89/website-archiver
cd website-archiver

# Install dependencies
pip install -r archiver/requirements.txt

# Run GUI
python -m archiver.gui
```

That's it! The GUI will open and you can start archiving websites.

## Quick Start - CLI Version (Container)

### Requirements
- Podman installed
- No Python installation needed

### Deploy Container
```bash
# Deploy container
python deployarchiver.py --clean

# Archive a website
podman exec website-archiver python -m archiver.cli https://example.com -o /data/archive
```

### CLI Options
```bash
python deployarchiver.py --help

Options:
  --port PORT     Port to run on (default: 8000)
  --data-dir DIR  Data directory (default: ./data)
  --rebuild       Force rebuild of container
  --clean         Remove existing container if it exists
```

## Directory Structure

```
.
├── Containerfile         # Container definition
├── deployarchiver.py     # CLI container deployment
├── manual.html           # User documentation
├── README.md             # This readme file
├── archiver/             # Core application package
│   ├── cli.py            # CLI application
│   ├── core.py           # Core archiver logic
│   ├── gui.py            # GUI application
│   ├── requirements.txt  # Dependencies
│   └── docker-entrypoint.sh # Container entrypoint
├── nginx/                # Archived site viewer
│   ├── Containerfile     # NGINX container definition
│   ├── deploy.py         # Deployment script
│   └── nginx.conf        # NGINX configuration
├── data/                 # Shared data directory
└── tests/                # Test suite
    ├── requirements-test.txt # Test dependencies
    └── test_archiver.py      # Test cases
```

## Viewing Archived Sites

After archiving, you can view the site using the included NGINX container:

```bash
cd nginx
python deploy.py
```

The archived site will be available at http://localhost:8080

## Development

### Local Development Setup

1. Install dependencies:
```bash
pip install -r archiver/requirements.txt
```

2. Install test dependencies:
```bash
pip install -r tests/requirements-test.txt
```

3. Run tests:
```bash
pytest tests/
```

### Testing

The project includes a comprehensive test suite with unit tests, Selenium tests for dynamic content capture, and integration tests using a local test server.

#### Test Requirements

- **Basic Testing**: pytest, pytest-cov, pytest-mock, requests-mock
- **Selenium Testing**: selenium, webdriver-manager
- **Other Dependencies**: Pillow, BeautifulSoup4

For Selenium tests to work properly:
- Chrome browser must be installed
- The tests will use webdriver-manager to automatically download the appropriate ChromeDriver
- Tests will skip gracefully if Selenium or ChromeDriver is not available

#### Running Specific Tests

```bash
# Run unit tests only
pytest tests/test_archiver.py

# Run Selenium tests
pytest tests/test_selenium_capture.py

# Run integration tests with test server
pytest tests/test_integration.py

# Run with coverage report
pytest --cov=archiver tests/
```

#### Test Server

The test suite includes a test server that creates a mini website with dynamic content for testing. You can use it independently:

```bash
python -m tests.test_server
# Test server will run at http://localhost:8888
```

### Container Management

```bash
# Stop container
podman stop website-archiver

# Start container
podman start website-archiver

# Remove container
podman rm -f website-archiver

# View logs
podman logs website-archiver
```

## Troubleshooting

### GUI Version
- "No module named 'tkinter'" - Install Python's Tkinter package
- Install system Tkinter package if needed:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install python3-tk
  
  # Fedora
  sudo dnf install python3-tkinter
  ```

### CLI Version
- Container already exists - Use `--clean` flag
- Permission issues - Check Podman installation and permissions
- Data directory issues - Verify directory permissions

## License

MIT License

## Support

For issues and feature requests, please use the GitHub issue tracker.
