# Use Python 3.11 slim as base
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    tk \
    wget \
    gnupg \
    chromium \
    chromium-driver \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set display for Chrome
ENV DISPLAY=:99

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY archiver/requirements.txt .
RUN pip install -r requirements.txt

# Copy application code
COPY archiver/ ./archiver/

# Create directory for logs
RUN mkdir -p /data/logs

# Create volume for output
VOLUME ["/data"]

# Set entrypoint script
COPY ./archiver/docker-entrypoint.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Start Xvfb for headless Chrome
ENV CHROME_BIN=/usr/bin/chromium
ENV CHROME_PATH=/usr/lib/chromium/
ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver

ENTRYPOINT ["docker-entrypoint.sh"]

# Default command (can be overridden)
CMD ["cli"]