# Installation Guide

## Prerequisites

- **Python 3.8+** (3.11+ recommended)
- **Firefox Browser** (for WebDriver automation)
- **Plus500US Account** (demo or live)
- **Git** (for development installation)

## Installation Methods

### 1. Development Installation (Recommended)

Clone and install in development mode:

```bash
# Clone the repository
git clone https://github.com/ENHarry/plus500US_api.git
cd plus500US_api

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install in development mode with all dependencies
pip install -e .[dev]
```

### 2. Package Installation

```bash
# Install from PyPI (when available)
pip install plus500us-client

# Or install with WebDriver support
pip install plus500us-client[webdriver]
```

### 3. Docker Installation

```dockerfile
FROM python:3.11-slim

# Install Firefox and dependencies
RUN apt-get update && apt-get install -y \
    firefox-esr \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install geckodriver
RUN wget -O /tmp/geckodriver.tar.gz https://github.com/mozilla/geckodriver/releases/download/v0.33.0/geckodriver-v0.33.0-linux64.tar.gz \
    && tar -xzf /tmp/geckodriver.tar.gz -C /usr/local/bin \
    && chmod +x /usr/local/bin/geckodriver

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install SDK
COPY . /app
WORKDIR /app
RUN pip install -e .
```

## WebDriver Setup

### Firefox Installation

The SDK uses Firefox for WebDriver automation:

**Windows:**
```bash
# Download Firefox from https://www.mozilla.org/firefox/
# Or install via Chocolatey:
choco install firefox
```

**macOS:**
```bash
# Install via Homebrew:
brew install --cask firefox
```

**Linux:**
```bash
# Ubuntu/Debian:
sudo apt-get install firefox

# CentOS/RHEL:
sudo yum install firefox
```

### Geckodriver Installation

Geckodriver is automatically managed by the SDK, but you can install manually:

```bash
# Download from: https://github.com/mozilla/geckodriver/releases
# Place in PATH or specify in configuration
```

## Environment Configuration

Create a `.env` file in your project root:

```bash
# Copy the template
cp .env.example .env

# Edit with your credentials
```

### Required Environment Variables

```bash
# Plus500US Credentials
PLUS500_EMAIL=your.email@example.com
PLUS500_PASSWORD=your_secure_password

# Optional: Trading Configuration
PLUS500_ACCOUNT_TYPE=demo  # or 'live'
PLUS500_BASE_URL=https://futures.plus500.com

# Optional: WebDriver Configuration
WEBDRIVER_HEADLESS=false
WEBDRIVER_TIMEOUT=30
WEBDRIVER_PROFILE_PATH=~/.plus500_profile

# Optional: Risk Management
MAX_POSITION_SIZE=10
MAX_DAILY_LOSS=1000
```

## Verify Installation

Test your installation:

```bash
# Test basic import
python -c "from plus500us_client import Plus500ApiClient; print('✅ Installation successful')"

# Test WebDriver setup
python examples/test_browser_open.py

# Test configuration loading
python -c "from plus500us_client import load_config; config = load_config(); print('✅ Configuration loaded')"
```

## Dependencies

### Core Dependencies

```txt
requests>=2.31.0
pydantic>=2.0.0
python-dotenv>=1.0.0
selenium>=4.15.0
undetected-chromedriver>=3.5.0
```

### Development Dependencies

```txt
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0
```

### Optional Dependencies

```txt
# Enhanced WebDriver features
selenium-stealth>=1.0.6
fake-useragent>=1.4.0

# Performance monitoring
psutil>=5.9.0

# Advanced authentication
cryptography>=41.0.0
```

## Troubleshooting Installation

### Common Issues

**Firefox not found:**
```bash
# Specify Firefox path manually
export FIREFOX_BINARY_PATH=/path/to/firefox
```

**Geckodriver issues:**
```bash
# Download latest geckodriver
wget https://github.com/mozilla/geckodriver/releases/latest/download/geckodriver-linux64.tar.gz
tar -xzf geckodriver-linux64.tar.gz
sudo mv geckodriver /usr/local/bin/
```

**Permission errors:**
```bash
# Fix permissions for profile directory
chmod 755 ~/.plus500_profile
```

**SSL/Certificate errors:**
```bash
# Update certificates
pip install --upgrade certifi
```

### Platform-Specific Issues

**Windows:**
- Ensure Windows Defender doesn't block WebDriver
- Use PowerShell with execution policy set to RemoteSigned

**macOS:**
- Allow Firefox in Security & Privacy settings
- Install Xcode command line tools: `xcode-select --install`

**Linux:**
- Install additional dependencies: `sudo apt-get install libgtk-3-0 libdbus-glib-1-2`
- Ensure X11 forwarding for headless systems

## Next Steps

After installation:

1. **[Configure Environment](configuration.md)** - Set up credentials and options
2. **[Quick Start Guide](quickstart.md)** - Your first automated trade
3. **[Authentication Setup](authentication.md)** - Configure login methods
4. **[Run Examples](../examples/README.md)** - Test with provided examples

## Support

If you encounter issues:

1. Check the [Troubleshooting Guide](troubleshooting.md)
2. Review [Common Issues](https://github.com/ENHarry/plus500US_api/issues)
3. Open a new issue with detailed error logs

---

> **Note**: This SDK is designed for educational and demo purposes. Always ensure compliance with Plus500US Terms of Service.