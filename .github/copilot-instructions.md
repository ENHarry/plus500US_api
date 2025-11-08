# Plus500US Trading Client - AI Coding Instructions

## Architecture Overview

This is a **hybrid trading automation client** with dual APIs for Plus500US futures platform. The architecture centers on intelligent fallback between WebDriver and requests-based automation.

### Core Components Structure
- `plus500us_client/requests/` - HTTP API client (legacy compatibility)
- `plus500us_client/webdriver/` - Browser automation (primary method)  
- `plus500us_client/hybrid/` - Intelligent method selection & fallback
- `examples/` - Complete workflow demonstrations
- `tests/` - Pytest-based testing with WebDriver markers

### Critical Safety Architecture
**Partial Take Profit Validation** - Position corruption prevention:
```python
# MANDATORY: Position must have >1 contract for partial TP
PartialClosureValidator.validate_partial_tp(position, partial_qty)
```

## Development Workflows

### Primary Test Command
```bash
pytest tests/ -m "unit or integration" --tb=short
```

### WebDriver Test Isolation
```bash 
pytest tests/ -m webdriver  # Browser automation tests only
pytest tests/ -m "not webdriver"  # Skip browser tests
```

### Example Execution Pattern
Always run examples in order (they build on each other):
1. `python examples/webdriver_login.py` 
2. `python examples/webdriver_trading.py`
3. `python examples/complete_workflow.py`

## Project-Specific Patterns

### Hybrid Method Selection
The `MethodSelector` automatically switches automation methods based on context:
```python
# Pattern: Always use method selector for new operations
from plus500us_client.hybrid import MethodSelector
method = selector.select_method("login", {"captcha_detected": True})
# Automatically returns AutomationMethod.WEBDRIVER for captcha scenarios
```

### Import Strategy
Main client aggregates all modules through `Plus500ApiClient`:
```python
# DO: Use unified client import
from plus500us_client import Plus500ApiClient

# AVOID: Direct module imports unless extending functionality
# from plus500us_client.requests.trading import TradingClient
```

### Error Handling Convention
Specific exception hierarchy for trading context:
- `AutomationBlockedError` → Triggers WebDriver fallback
- `CaptchaRequiredError` → Forces interactive handling
- `PartialTakeProfitError` → Critical position safety violation
- `ValidationError` → Input validation (extends to `PositionSizeError`)

### Configuration Management
Environment-based config with fallback defaults:
```python
# Pattern: Always load config first
from plus500us_client import load_config
config = load_config()  # Reads .env, applies defaults
```

## WebDriver Integration Patterns

### Browser Manager Lifecycle
```python
# CRITICAL: Always cleanup WebDriver resources
try:
    browser_manager = BrowserManager(config)
    # ... automation code
finally:
    browser_manager.cleanup()  # Prevents zombie processes
```

### Anti-Detection Standards
- Use `stealth_mode=True` for undetected automation
- Implement human-like timing patterns (`time.sleep(random.uniform(1, 3))`)
- Persist browser profiles for consistent fingerprinting

### Element Detection Strategy
Multiple selector fallbacks in `Plus500Selectors`:
```python
# Pattern: XPath primary, CSS fallback, attribute-based final
LOGIN_BUTTON = [
    "//button[@data-automation-id='login-submit']",
    "button[type='submit']:contains('Login')", 
    "input[value*='Login']"
]
```

## Critical Business Logic

### Position Management Rules
1. **Never** allow partial TP on positions ≤ 1 contract
2. **Always** validate remaining quantity ≥ 1 contract after partial close
3. Use `tick_round()` for price precision handling

### Session Bridge Pattern
WebDriver sessions transfer to requests for API efficiency:
```python
# Pattern: Authenticate with WebDriver, switch to requests for API calls
session_bridge.transfer_webdriver_cookies(webdriver_session, requests_session)
```

### Risk Management Integration
`AdvancedRiskManager` wraps all trading operations:
- Pre-trade validation (margin, position size limits)
- Real-time P&L monitoring
- Automatic stop-loss enforcement

## Testing Conventions

### Pytest Markers Usage
```python
@pytest.mark.webdriver  # Requires browser automation
@pytest.mark.captcha    # May encounter captcha challenges  
@pytest.mark.live       # Uses live trading account (rare)
@pytest.mark.slow       # Operations >5 seconds
```

### Mock Strategy
Use `responses` library for requests mocking, Selenium for WebDriver page mocking.

## Integration Points

### SignalR Considerations
Plus500 uses SignalR for real-time data. Extract parameters via:
```python
# Pattern: Capture SignalR negotiation during WebDriver session
signalr_params = extract_signalr_params(webdriver_session)
```

### Session Persistence
Browser profiles persist authentication across runs:
- Profile path: `~/.plus500_profile` (configurable)
- Cookie backup: JSON format in project root
- Session validation: Test API call before proceeding

## File Naming Conventions
- `*_api.py` - Core API clients  
- `*_manager.py` - WebDriver component managers
- `*_automation.py` - Complete automation workflows
- `test_*.py` - Pytest test files (follows pytest discovery)
- `*_example.py` - Runnable demonstration scripts

When extending functionality, follow the hybrid pattern: implement in both `requests/` and `webdriver/` modules, then integrate via `hybrid/` layer with intelligent fallback logic.


# Terminal Instructions
Only open one terminal per session to avoid multiple connections to Plus500Us.

# Code Etiquette and Conventions
- Maintain consistent import style across all files
- Use environment variables for all credentials and connection parameters
- Follow existing logging and error handling patterns
- Adhere to established async programming practices for real-time data handling
- Ensure code is modular, efficient, optimized, vectorized (where possible), clean, concise, and well-documented for maintainability