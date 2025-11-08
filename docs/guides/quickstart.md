# Quick Start Guide

Get started with Plus500US API automation in minutes.

## 1. Installation

```bash
# Install the SDK
pip install -e .[dev]

# Or clone from GitHub
git clone https://github.com/ENHarry/plus500US_api.git
cd plus500US_api
pip install -e .[dev]
```

## 2. Environment Setup

Create a `.env` file with your credentials:

```bash
# Plus500US Account
PLUS500_EMAIL=your.email@example.com
PLUS500_PASSWORD=your_secure_password
PLUS500_ACCOUNT_TYPE=demo

# Optional: WebDriver settings
WEBDRIVER_HEADLESS=false
```

## 3. Your First Trade

### Simple Market Order

```python
from plus500us_client import Plus500ApiClient, load_config
from decimal import Decimal

# Load configuration
config = load_config()

# Initialize client
client = Plus500ApiClient(config)

# Authenticate (hybrid method - will open browser if needed)
client.authenticate()

# Place a market order
order = client.place_market_order(
    instrument="GC",        # Gold futures
    side="BUY",            # Buy or "SELL"
    quantity=Decimal("1")   # 1 contract
)

print(f"✅ Order placed: {order['id']}")
print(f"   Status: {order['status']}")
```

### Market Order with Risk Management

```python
# Place order with stop loss and take profit
order = client.place_market_order(
    instrument="GC",
    side="BUY", 
    quantity=Decimal("1"),
    stop_loss=Decimal("2650.00"),    # Stop loss at $2650
    take_profit=Decimal("2750.00")   # Take profit at $2750
)

print(f"✅ Order with risk management: {order['id']}")
```

## 4. Check Your Positions

```python
# Get all open positions
positions = client.get_positions()

for position in positions:
    print(f"📊 {position['instrument']}: {position['side']} {position['quantity']}")
    print(f"   P&L: ${position.get('unrealized_pnl', 'N/A')}")
    print(f"   Entry: ${position.get('entry_price', 'N/A')}")
```

## 5. Account Information

```python
# Check account balance
balance = client.get_account_balance()
print(f"💰 Account Balance: ${balance.get('balance', 'N/A')}")
print(f"   Available: ${balance.get('available', 'N/A')}")
print(f"   Margin Used: ${balance.get('margin_used', 'N/A')}")

# Get account info
account = client.get_account_info()
print(f"🏦 Account Type: {account.get('account_type', 'Unknown')}")
print(f"   Account ID: {account.get('account_id', 'Unknown')}")
```

## 6. Available Instruments

```python
# Get tradable instruments
instruments = client.get_instruments()

print("📈 Available Instruments:")
for instrument in instruments[:10]:  # Show first 10
    symbol = instrument.get('symbol', 'Unknown')
    name = instrument.get('name', 'Unknown')
    print(f"   {symbol}: {name}")
```

## 7. Complete Workflow Example

Here's a complete trading workflow:

```python
from plus500us_client import Plus500ApiClient, load_config, OrderDraft
from decimal import Decimal
import time

def main():
    # Setup
    config = load_config()
    client = Plus500ApiClient(config)
    
    print("🔐 Authenticating...")
    client.authenticate()
    
    # Check account
    print("🏦 Checking account...")
    account = client.get_account_info()
    print(f"   Account: {account.get('account_type', 'Unknown')}")
    
    # Get balance
    balance = client.get_account_balance()
    print(f"💰 Balance: ${balance.get('balance', 'N/A')}")
    
    # Place order
    print("📊 Placing order...")
    order = client.place_market_order(
        instrument="GC",
        side="BUY",
        quantity=Decimal("1"),
        stop_loss=Decimal("2650.00"),
        take_profit=Decimal("2750.00")
    )
    
    print(f"✅ Order placed: {order['id']}")
    
    # Monitor position
    print("👀 Monitoring position...")
    time.sleep(5)  # Wait for fill
    
    positions = client.get_positions()
    for pos in positions:
        if pos.get('instrument') == 'GC':
            print(f"📊 GC Position: {pos['side']} {pos['quantity']}")
            print(f"   P&L: ${pos.get('unrealized_pnl', 'N/A')}")
    
    # Logout
    print("🚪 Logging out...")
    client.logout()
    print("✅ Session ended")

if __name__ == "__main__":
    main()
```

## 8. WebDriver Authentication

If you prefer explicit WebDriver authentication:

```python
from plus500us_client.webdriver import WebDriverAuthHandler, BrowserManager

# Setup WebDriver authentication
config = load_config()
browser_manager = BrowserManager(config)
auth_handler = WebDriverAuthHandler(config)

try:
    # Start browser
    driver = browser_manager.start_browser()
    
    # Navigate to login
    driver.get("https://futures.plus500.com/login")
    
    # Complete authentication in browser
    print("👤 Complete login in the browser window...")
    input("Press Enter when authentication is complete...")
    
    # Extract session
    session_data = auth_handler.extract_session_data(driver)
    print("✅ Session extracted successfully")
    
finally:
    browser_manager.stop_browser()
```

## 9. Error Handling

```python
from plus500us_client.requests.errors import (
    AuthenticationError, TradingError, ValidationError
)

try:
    client.authenticate()
    
except AuthenticationError as e:
    print(f"❌ Authentication failed: {e}")
    # Handle authentication issues
    
except TradingError as e:
    print(f"❌ Trading error: {e}")
    # Handle trading-specific errors
    
except ValidationError as e:
    print(f"❌ Validation error: {e}")
    # Handle input validation errors
    
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    # Handle other errors
```

## 10. Running Examples

The SDK includes comprehensive examples:

```bash
# Basic authentication
python examples/webdriver_login.py

# Trading operations  
python examples/webdriver_trading.py

# Complete workflow
python examples/complete_workflow.py

# Interactive login
python examples/interactive_login.py
```

## Next Steps

Now that you've completed the quick start:

1. **[Authentication Guide](authentication.md)** - Learn about different login methods
2. **[Trading Operations](trading.md)** - Explore advanced trading features
3. **[WebDriver Guide](webdriver.md)** - Master browser automation
4. **[Configuration](configuration.md)** - Customize your setup
5. **[Examples](../examples/README.md)** - Study detailed examples
6. **[API Reference](../api/client.md)** - Explore all available methods

## Support

- **Documentation**: [docs/README.md](../README.md)
- **Examples**: [examples/](../examples/)
- **Issues**: [GitHub Issues](https://github.com/ENHarry/plus500US_api/issues)
- **API Reference**: [docs/api/](../api/)

---

> **⚠️ Important**: Always test with a demo account first. This SDK is for educational purposes and must comply with Plus500US Terms of Service.