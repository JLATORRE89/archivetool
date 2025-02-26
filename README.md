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
pip install -r requirements.txt

# Run GUI
python gui.py
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
├── gui.py               # GUI application (run directly)
├── cli.py              # CLI application
├── core.py             # Core archiver logic
├── deployarchiver.py   # CLI container deployment
├── nginx/             # Archived site viewer
└── data/              # Shared data directory
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
pip install -r requirements.txt
```

2. Install test dependencies:
```bash
pip install -r tests/requirements-test.txt
```

3. Run tests:
```bash
pytest tests/
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
