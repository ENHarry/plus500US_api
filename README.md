# plus500us-client (Unofficial) — Hybrid Login

**⚠️ Disclaimer**: This is an *unofficial*, demo-oriented client. It must respect Plus500US Terms of Use.
Do **not** bypass captchas or bot checks. This client offers a *user-interactive* browser handoff to satisfy human verification.

## What's new
- **WebDriver Automation**: Full browser automation with anti-detection features
- **Hybrid Fallback System**: Intelligent switching between requests and WebDriver
- **Advanced Trading**: Market, limit, stop orders with comprehensive risk management
- **Critical Safety Features**: Partial take profit validation prevents position corruption
- `--interactive` login: open the official site in your browser, complete reCAPTCHA, then paste a **Copy as cURL** command or **Cookie** header. The client imports the cookies into its `requests.Session`.

## Quick start

### Traditional Interactive Login
```bash
pip install -e .[dev]
python -m plus500us_client.cli login --interactive
# or
python examples/interactive_login.py
```

### WebDriver Automation (Recommended)
```bash
# Install with WebDriver dependencies
pip install -e .[dev]

# WebDriver authentication
python examples/webdriver_login.py

# Complete trading automation
python examples/webdriver_trading.py

# Full end-to-end workflow
python examples/complete_workflow.py
```

## Why a browser handoff?
- Many platforms require human verification via JS and/or reCAPTCHA. Respecting ToS means we **let you complete it in your browser** and **import** the authenticated session cookies—no automation evasion.

## WebDriver Automation Features

### 🤖 Primary Automation Method
WebDriver is now the **primary automation method** due to Plus500's advanced anti-bot protection. The system automatically handles:

- **Anti-Detection**: Stealth mode with undetected browser automation
- **Element Detection**: Robust XPath/CSS selectors with multiple fallbacks
- **Human-like Behavior**: Natural timing patterns and mouse movements
- **Session Management**: Automatic cookie transfer between WebDriver and requests

### 🛡️ Critical Safety Features

**Partial Take Profit Validation** - Prevents position corruption:
```python
# ✅ SAFE: Position has 5 contracts, closing 2, leaving 3
execute_partial_take_profit("POS_001", Decimal("2"))

# ❌ BLOCKED: Position has only 1 contract
execute_partial_take_profit("POS_002", Decimal("0.5"))  # ValidationError

# ❌ BLOCKED: Would leave 0.5 contracts remaining  
execute_partial_take_profit("POS_001", Decimal("4.5"))  # ValidationError
```

### 🔄 Intelligent Fallback System

The hybrid system automatically switches methods based on conditions:
- **Captcha Detection** → Switch to WebDriver
- **Rate Limiting** → Circuit breaker protection
- **Anti-Bot Blocks** → Automatic method selection
- **Context Awareness** → Adapts to different scenarios

### 📊 Complete Trading Operations

```python
from plus500us_client.webdriver import WebDriverTradingClient
from decimal import Decimal

# Market order with risk management
client.place_market_order(
    "EURUSD", "BUY", Decimal("1"),
    stop_loss=Decimal("1.0950"),
    take_profit=Decimal("1.1050")
)

# Limit order
client.place_limit_order(
    "GBPUSD", "SELL", Decimal("2"), 
    limit_price=Decimal("1.2600")
)

# Position monitoring
positions = client.get_positions()
for pos in positions:
    pnl = client.monitor_position_pnl(pos['id'])
    print(f"Position P&L: ${pnl}")
```

## 📚 Examples

Comprehensive examples are available in the `examples/` directory:

- **`webdriver_login.py`** - WebDriver authentication basics
- **`webdriver_trading.py`** - Trading operations and risk management
- **`hybrid_fallback.py`** - Intelligent fallback system demo
- **`complete_workflow.py`** - End-to-end automation workflow

See [`examples/README.md`](examples/README.md) for detailed documentation.
