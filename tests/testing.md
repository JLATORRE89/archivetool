# Testing the Website Archiver

This document provides information about the test suite and how to run the tests for the Website Archiver project.

## Test Suite Overview

The project includes a comprehensive test suite with:

1. **Unit Tests** - Testing individual components of the archiver
2. **Selenium Tests** - Testing dynamic content capture
3. **Integration Tests** - Testing the complete archiving flow with a test server

## Requirements

### Required Packages

Install all test dependencies with:

```bash
pip install -r tests/requirements-test.txt
```

The test requirements include:

```
# Basic testing
pytest==7.4.3
pytest-cov==4.1.0
pytest-mock==3.12.0
requests-mock==1.11.0

# Selenium testing
selenium==4.15.2
webdriver-manager==4.0.1

# Required for image testing
Pillow==10.1.0
beautifulsoup4==4.12.2
```

### Selenium Requirements

For Selenium tests (dynamic content capture):

- Chrome browser must be installed
- The tests will use webdriver-manager to download the appropriate ChromeDriver version
- Tests will skip gracefully if Selenium or ChromeDriver is not available

## Running Tests

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest -v tests/

# Run with code coverage report
pytest --cov=archiver tests/
```

### Run Specific Tests

```bash
# Run unit tests only
pytest tests/test_archiver.py

# Run Selenium tests
pytest tests/test_selenium_capture.py

# Run integration tests with test server
pytest tests/test_integration.py
```

### Test Markers

You can use test markers to run specific test categories:

```bash
# Run only tests marked as 'selenium'
pytest -m selenium tests/

# Run only tests marked as 'integration'
pytest -m integration tests/
```

## Test Server

The test suite includes a test server that creates a mini website with dynamic content for testing. 

### Running the Test Server Independently

You can start the test server separately to manually test against it:

```bash
python -m tests.test_server
```

This will start a local server at http://localhost:8888 with test pages that include:
- Static HTML pages
- CSS styling
- JavaScript with dynamic content
- Images
- A directory structure with subdirectories

The test server creates a temporary directory that is automatically cleaned up when the server is stopped.

## Troubleshooting Tests

### Common Issues

1. **Selenium tests failing or skipped**
   - Ensure Chrome is installed
   - Check that selenium and webdriver-manager are installed
   - Try running with increased verbosity: `pytest -v tests/test_selenium_capture.py`

2. **Integration tests timing out**
   - The test server might be having issues binding to a port
   - Check for other processes using port 8888
   - Try running with a longer timeout: `pytest --timeout=30 tests/test_integration.py`

3. **Permission errors when writing test files**
   - Ensure the user running the tests has write permissions to the temp directory

### Debug Logging

To enable more verbose debug logging during tests:

```bash
pytest --log-cli-level=DEBUG tests/
```

## Adding New Tests

When adding new tests, follow these guidelines:

1. Unit tests for new functionality should be added to `test_archiver.py`
2. For testing dynamic content, add tests to `test_selenium_capture.py`
3. For testing the complete archiving flow, add tests to `test_integration.py`
4. Use appropriate fixtures and mocks to isolate tests
5. Ensure tests clean up after themselves (especially temporary files)

## Continuous Integration

The test suite is designed to run in CI environments. When running in CI:

1. Install all dependencies including Chrome
2. Run tests with coverage: `pytest --cov=archiver --cov-report=xml tests/`
3. The tests will skip Selenium tests automatically if the environment doesn't support them