# Plus500US SDK Examples# Plus500US SDK Examples



This directory contains practical examples demonstrating all features of the Plus500US Python SDK.This directory contains practical examples demonstrating all features of the Plus500US Python SDK.



## 🚀 Getting Started## 🚀 Quick Start



Run the examples in this order to learn the SDK:The examples are designed to be run in order, building from basic authentication to complete trading workflows:



1. **[webdriver_login.py](webdriver_login.py)** - Authentication basics1. **`webdriver_login.py`** - Basic WebDriver authentication

2. **[webdriver_trading.py](webdriver_trading.py)** - Trading operations  2. **`webdriver_trading.py`** - Trading operations and risk management  

3. **[hybrid_fallback.py](hybrid_fallback.py)** - Intelligent fallback system3. **`hybrid_fallback.py`** - Intelligent fallback system

4. **[complete_workflow.py](complete_workflow.py)** - End-to-end workflow4. **`complete_workflow.py`** - End-to-end automation workflow



## 📁 Example Categories## 📋 Example Descriptions



### 🔐 Authentication### 🔐 webdriver_login.py

- **`webdriver_login.py`** - WebDriver-based authentication**WebDriver Authentication Example**

- **`interactive_login.py`** - Manual browser login with session import

Demonstrates the primary authentication method using WebDriver automation:

### 📊 Trading Operations- Browser-based manual login with session capture

- **`webdriver_trading.py`** - Market/limit orders, positions, risk management- Cookie extraction and session management

- **`webdriver_account_management.py`** - Account info, balance, instruments- Session validation and backup

- Profile persistence for faster future logins

### 🤖 Advanced Features

- **`hybrid_fallback.py`** - Intelligent method switching```bash

- **`complete_workflow.py`** - Production-ready automation workflowpython examples/webdriver_login.py

```

### 🧪 Testing & Validation

- **`complete_live_test.py`** - Live market testing (use with caution)**Features:**

- ✅ Handles anti-bot protection automatically

## 🎯 Quick Examples- ✅ Supports both demo and live accounts

- ✅ Session persistence and backup

### Simple Market Order- ✅ Stealth mode for undetected automation

```python

from plus500us_client import Plus500ApiClient, load_config---

from decimal import Decimal

### 📈 webdriver_trading.py

config = load_config()**Trading Automation Example**

client = Plus500ApiClient(config)

client.authenticate()Comprehensive trading operations using WebDriver:

- Market, limit, and stop order placement

order = client.place_market_order(- Position monitoring and management

    instrument="GC", - Risk management (stop loss/take profit)

    side="BUY", - **Critical**: Partial take profit validation safeguards

    quantity=Decimal("1")

)```bash

print(f"Order placed: {order['id']}")python examples/webdriver_trading.py

``````



### Order with Risk Management**Key Safety Features:**

```python- 🛡️ **Partial TP requires position > 1 contract**

order = client.place_market_order(- 🛡️ **Remaining position must be ≥ 1 contract**

    instrument="GC",- 🛡️ Order validation and error handling

    side="BUY", - 🛡️ Real-time P&L monitoring

    quantity=Decimal("1"),

    stop_loss=Decimal("2650.00"),---

    take_profit=Decimal("2750.00")

)### 🧠 hybrid_fallback.py

```**Intelligent Fallback System**



### Position MonitoringDemonstrates the hybrid automation system that automatically switches between methods:

```python- Intelligent method selection based on context

positions = client.get_positions()- Automatic fallback when primary method fails

for pos in positions:- Circuit breaker protection

    print(f"{pos['instrument']}: {pos['side']} {pos['quantity']}")- Context-aware adaptation

    print(f"P&L: ${pos.get('unrealized_pnl', 'N/A')}")

``````bash

python examples/hybrid_fallback.py

## ⚙️ Configuration```



Create `.env` file in project root:**Adaptive Features:**

- 🤖 Detects captcha and switches to WebDriver

```bash- 🚫 Handles rate limiting and access blocks

PLUS500_EMAIL=your.email@example.com- ⚡ Circuit breaker prevents repeated failures

PLUS500_PASSWORD=your_secure_password- 📊 Health monitoring and diagnostics

PLUS500_ACCOUNT_TYPE=demo  # or 'live'

WEBDRIVER_HEADLESS=false   # true for background---

```

### 🎯 complete_workflow.py

## 🛡️ Safety Features**Complete End-to-End Workflow**



All examples demonstrate critical safety features:Full automation workflow from authentication to trading:

- Complete authentication process

- **Position Validation**: Prevents invalid partial take profits- Session management and validation

- **Risk Management**: Automatic stop loss and take profit- Trading operations with risk management

- **Error Handling**: Comprehensive exception handling  - Position monitoring and management

- **Resource Cleanup**: Proper WebDriver cleanup- Error handling and recovery

- Cleanup and session backup

## 📋 Requirements

```bash

- Python 3.8+python examples/complete_workflow.py

- Firefox browser (for WebDriver)```

- Plus500US account (demo recommended for testing)

- Environment variables configured**Production Features:**

- 🚀 Complete automation pipeline

## 🚀 Running Examples- 🛡️ Comprehensive safety validations

- 📊 System health monitoring

```bash- 💾 Session backup and recovery

# Basic authentication- 🧹 Proper resource cleanup

python examples/webdriver_login.py

---

# Trading operations

python examples/webdriver_trading.py  ## ⚙️ Configuration



# Complete workflow### Environment Variables

python examples/complete_workflow.py

Create a `.env` file in the project root:

# Interactive login (manual)

python examples/interactive_login.py```env

```PLUS500US_EMAIL=your_email@example.com

PLUS500US_PASSWORD=your_password

## 🔧 TroubleshootingPLUS500US_ACCOUNT_TYPE=demo

PLUS500US_TOTP_SECRET=your_totp_secret  # Optional

**Common Issues:**```



1. **Browser doesn't open**: Install Firefox, check PATH### WebDriver Configuration

2. **Authentication fails**: Verify credentials in `.env` 

3. **Element not found**: Plus500 UI may have changedThe examples use Firefox by default. Customize in each example:

4. **Permission denied**: Check file permissions

```python

**Debug Mode:**webdriver_config = {

```python    "browser": "firefox",         # "firefox", "chrome", or "edge"

import logging    "headless": False,            # True for background operation

logging.basicConfig(level=logging.DEBUG)    "stealth_mode": True,         # Anti-detection features

```    "window_size": (1920, 1080), # Browser window size

    "implicit_wait": 10,          # Element wait timeout

## 📚 Learn More    "page_load_timeout": 30,      # Page load timeout

    "profile_path": "~/.plus500_profile"  # Persistent profile

- **[Installation Guide](../docs/guides/installation.md)**}

- **[Quick Start Guide](../docs/guides/quickstart.md)**```

- **[API Reference](../docs/api/client.md)**

- **[WebDriver Guide](../docs/guides/webdriver.md)**## 🛡️ Critical Safety Features



## ⚠️ Important Notes### Partial Take Profit Validation



- **Always test with demo account first****Why This Matters:** Partial take profit operations can corrupt positions if not properly validated.

- **Respect Plus500US Terms of Service**

- **Use appropriate risk management****Safety Safeguards Implemented:**

- **Never commit credentials to version control**1. **Position Size Check**: Position must have > 1 contract

2. **Remaining Quantity Check**: Remaining position must be ≥ 1 contract after partial close

---3. **Quantity Validation**: Partial quantity cannot equal or exceed position size



**Ready to automate your trading? Start with `webdriver_login.py`! 🚀****Example:**
```python
# ✅ SAFE: Position has 5 contracts, closing 2, leaving 3
execute_partial_take_profit("POS_001", Decimal("2"))

# ❌ BLOCKED: Position has only 1 contract
execute_partial_take_profit("POS_002", Decimal("0.5"))  # ValidationError

# ❌ BLOCKED: Would leave 0.5 contracts remaining
execute_partial_take_profit("POS_001", Decimal("4.5"))  # ValidationError
```

## 📊 WebDriver Features

### Element Detection Strategy
- **Multiple Selectors**: XPath and CSS with fallback strategies
- **Robust Detection**: Handles dynamic page changes
- **Human-like Interactions**: Mimics natural user behavior
- **Error Recovery**: Automatic retry and fallback

### Anti-Detection Measures
- **Stealth Mode**: Undetected browser automation
- **Human Patterns**: Natural timing and movements
- **Profile Persistence**: Consistent browser fingerprint
- **Anti-Bot Evasion**: Advanced detection avoidance

## 🔧 Troubleshooting

### Common Issues

**Browser Not Opening:**
```bash
# Install Chrome/ChromeDriver
# Windows: Download from Google Chrome website
# macOS: brew install google-chrome chromedriver
# Linux: apt-get install google-chrome-stable chromium-chromedriver
```

**Authentication Fails:**
```bash
# Check credentials
echo $PLUS500US_EMAIL
echo $PLUS500US_PASSWORD

# Verify .env file location and format
cat .env
```

**Element Not Found:**
```bash
# Run with headless=False to see browser
# Check Plus500 website accessibility
# Update selectors if UI changed
```

**Session Transfer Issues:**
```bash
# Clear browser profile and try again
rm -rf ~/.plus500_profile

# Check network connectivity
ping futures.plus500.com
```

### Debug Mode

Enable verbose logging in any example:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🚀 Production Deployment

### Recommended Setup

1. **Environment Configuration**
   ```bash
   # Production environment variables
   export PLUS500US_ACCOUNT_TYPE=live  # Use live account
   export PLUS500US_HEADLESS=true     # Background operation
   ```

2. **Resource Management**
   ```python
   # Always use cleanup
   try:
       # Your automation code
       pass
   finally:
       browser_manager.cleanup()  # Essential!
   ```

3. **Error Handling**
   ```python
   # Comprehensive error handling
   from plus500us_client.errors import (
       CaptchaRequiredError, AutomationBlockedError,
       OrderRejectError, ValidationError
   )
   ```

4. **Health Monitoring**
   ```python
   # Regular health checks
   health = fallback_handler.health_check()
   if health['overall_status'] != 'healthy':
       # Alert and investigate
   ```

## 📚 Additional Resources

- **Testing**: See `tests/` directory for comprehensive test examples
- **Configuration**: See `plus500us_client/config.py` for all options
- **Error Handling**: See `plus500us_client/errors.py` for all exception types
- **WebDriver Components**: See `plus500us_client/webdriver/` for implementation details

## ⚠️ Important Notes

1. **Demo Account First**: Always test with demo account before live trading
2. **Resource Cleanup**: Always call `cleanup()` to prevent browser zombie processes
3. **Rate Limiting**: Respect Plus500's rate limits and terms of service
4. **Security**: Never commit credentials to version control
5. **Validation**: Always validate critical operations (especially partial TP)

## 🤝 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review the test suite for working examples
3. Ensure all dependencies are installed correctly
4. Verify Plus500 website accessibility

---

**Happy Trading! 🎯**

*Remember: These examples demonstrate WebDriver automation capabilities. Always use appropriate risk management and comply with Plus500's terms of service.*