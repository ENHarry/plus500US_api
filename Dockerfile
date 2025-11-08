# Dockerfile for Plus500US SDK
FROM python:3.10-slim

# Install system dependencies for WebDriver
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    xvfb \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99
ENV WEBDRIVER_HEADLESS=true

# Create app directory
WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml ./
RUN pip install --no-cache-dir -e ".[dev]"

# Copy source code
COPY plus500us_client/ ./plus500us_client/
COPY examples/ ./examples/
COPY tests/ ./tests/

# Create non-root user
RUN groupadd -r plus500 && useradd -r -g plus500 plus500
RUN chown -R plus500:plus500 /app
USER plus500

# Start Xvfb for headless browser testing
CMD ["sh", "-c", "Xvfb :99 -screen 0 1024x768x24 > /dev/null 2>&1 & python -m pytest tests/ -v"]