# Plus500US API Documentation

Welcome to the Plus500US Python SDK documentation. This SDK provides a hybrid approach to Plus500US futures trading automation, combining the reliability of direct API calls with the flexibility of WebDriver automation.

## 🏗️ Architecture Overview

The Plus500US SDK uses a **hybrid architecture** that intelligently switches between two automation methods:

- **Requests-First**: Direct API calls for efficiency and speed
- **WebDriver Fallback**: Browser automation for complex operations and authentication

### Key Components

- **[`plus500us_client/requests/`](api/requests.md)** - HTTP API client (primary method)
- **[`plus500us_client/webdriver/`](api/webdriver.md)** - Browser automation (authentication & fallback)
- **[`plus500us_client/hybrid/`](api/hybrid.md)** - Intelligent method selection & session bridge
- **[`examples/`](../examples/README.md)** - Complete workflow demonstrations
- **[`tests/`](api/testing.md)** - Comprehensive test suite

## 📚 Documentation Sections

### Getting Started
- **[Installation Guide](guides/installation.md)** - Setup and dependencies
- **[Quick Start](guides/quickstart.md)** - Your first automated trade
- **[Configuration](guides/configuration.md)** - Environment setup and options

### User Guides
- **[Authentication](guides/authentication.md)** - Hybrid login methods
- **[Trading Operations](guides/trading.md)** - Orders, positions, and risk management
- **[WebDriver Automation](guides/webdriver.md)** - Browser automation setup
- **[Error Handling](guides/error-handling.md)** - Exception handling and recovery

### API Reference
- **[Core Client](api/client.md)** - Main API client documentation
- **[Trading Models](api/models.md)** - Data structures and types
- **[WebDriver Components](api/webdriver.md)** - Browser automation reference
- **[Utilities](api/utilities.md)** - Helper functions and tools

### Advanced Topics
- **[Hybrid Architecture](guides/hybrid-architecture.md)** - Method selection and session bridging
- **[Risk Management](guides/risk-management.md)** - Safety features and validation
- **[Production Deployment](guides/production.md)** - Scaling and monitoring
- **[Troubleshooting](guides/troubleshooting.md)** - Common issues and solutions

## 🚀 Quick Example

```python
from plus500us_client import Plus500ApiClient, load_config
from decimal import Decimal

# Load configuration
config = load_config()

# Initialize client (hybrid mode)
client = Plus500ApiClient(config)

# Authenticate (automatically selects method)
client.authenticate()

# Place order with risk management
order = client.place_market_order(
    instrument="GC",  # Gold futures
    side="BUY",
    quantity=Decimal("1"),
    stop_loss=Decimal("2650.00"),
    take_profit=Decimal("2750.00")
)

print(f"Order placed: {order['id']}")
```

## 🛡️ Safety Features

This SDK includes critical safety features for production trading:

- **Partial Take Profit Validation**: Prevents position corruption
- **Position Size Limits**: Configurable risk controls
- **Circuit Breakers**: Automatic fallback on failures
- **Session Management**: Secure authentication handling
- **Anti-Detection**: Stealth browser automation

## 📋 Requirements

- Python 3.8+
- Firefox browser (for WebDriver automation)
- Valid Plus500US futures account
- Environment variables for credentials

## 🔗 Links

- **[GitHub Repository](https://github.com/ENHarry/plus500US_api)**
- **[Examples](../examples/)**
- **[Test Suite](../tests/)**
- **[License](../LICENSE)**

---

> **⚠️ Disclaimer**: This is an unofficial client. Always respect Plus500US Terms of Service and use responsibly.