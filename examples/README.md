# Plus500US WebDriver Automation Examples

This directory contains comprehensive examples demonstrating the WebDriver-powered automation capabilities of the Plus500US client.

## 🚀 Quick Start

The examples are designed to be run in order, building from basic authentication to complete trading workflows:

1. **`webdriver_login.py`** - Basic WebDriver authentication
2. **`webdriver_trading.py`** - Trading operations and risk management  
3. **`hybrid_fallback.py`** - Intelligent fallback system
4. **`complete_workflow.py`** - End-to-end automation workflow

## 📋 Example Descriptions

### 🔐 webdriver_login.py
**WebDriver Authentication Example**

Demonstrates the primary authentication method using WebDriver automation:
- Browser-based manual login with session capture
- Cookie extraction and session management
- Session validation and backup
- Profile persistence for faster future logins

```bash
python examples/webdriver_login.py
```

**Features:**
- ✅ Handles anti-bot protection automatically
- ✅ Supports both demo and live accounts
- ✅ Session persistence and backup
- ✅ Stealth mode for undetected automation

---

### 📈 webdriver_trading.py
**Trading Automation Example**

Comprehensive trading operations using WebDriver:
- Market, limit, and stop order placement
- Position monitoring and management
- Risk management (stop loss/take profit)
- **Critical**: Partial take profit validation safeguards

```bash
python examples/webdriver_trading.py
```

**Key Safety Features:**
- 🛡️ **Partial TP requires position > 1 contract**
- 🛡️ **Remaining position must be ≥ 1 contract**
- 🛡️ Order validation and error handling
- 🛡️ Real-time P&L monitoring

---

### 🧠 hybrid_fallback.py
**Intelligent Fallback System**

Demonstrates the hybrid automation system that automatically switches between methods:
- Intelligent method selection based on context
- Automatic fallback when primary method fails
- Circuit breaker protection
- Context-aware adaptation

```bash
python examples/hybrid_fallback.py
```

**Adaptive Features:**
- 🤖 Detects captcha and switches to WebDriver
- 🚫 Handles rate limiting and access blocks
- ⚡ Circuit breaker prevents repeated failures
- 📊 Health monitoring and diagnostics

---

### 🎯 complete_workflow.py
**Complete End-to-End Workflow**

Full automation workflow from authentication to trading:
- Complete authentication process
- Session management and validation
- Trading operations with risk management
- Position monitoring and management
- Error handling and recovery
- Cleanup and session backup

```bash
python examples/complete_workflow.py
```

**Production Features:**
- 🚀 Complete automation pipeline
- 🛡️ Comprehensive safety validations
- 📊 System health monitoring
- 💾 Session backup and recovery
- 🧹 Proper resource cleanup

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
PLUS500US_EMAIL=your_email@example.com
PLUS500US_PASSWORD=your_password
PLUS500US_ACCOUNT_TYPE=demo
PLUS500US_TOTP_SECRET=your_totp_secret  # Optional
```

### WebDriver Configuration

The examples use Firefox by default. Customize in each example:

```python
webdriver_config = {
    "browser": "firefox",         # "firefox", "chrome", or "edge"
    "headless": False,            # True for background operation
    "stealth_mode": True,         # Anti-detection features
    "window_size": (1920, 1080), # Browser window size
    "implicit_wait": 10,          # Element wait timeout
    "page_load_timeout": 30,      # Page load timeout
    "profile_path": "~/.plus500_profile"  # Persistent profile
}
```

## 🛡️ Critical Safety Features

### Partial Take Profit Validation

**Why This Matters:** Partial take profit operations can corrupt positions if not properly validated.

**Safety Safeguards Implemented:**
1. **Position Size Check**: Position must have > 1 contract
2. **Remaining Quantity Check**: Remaining position must be ≥ 1 contract after partial close
3. **Quantity Validation**: Partial quantity cannot equal or exceed position size

**Example:**
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