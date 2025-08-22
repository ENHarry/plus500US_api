"""
Pytest configuration and fixtures for Plus500US client tests
"""
import os
import pytest
import tempfile
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
from typing import Dict, Any, Optional, Generator

from plus500us_client.config import Config
from plus500us_client.session import SessionManager
from plus500us_client.webdriver import BrowserManager, WebDriverAuthHandler, WebDriverTradingClient
from plus500us_client.hybrid import MethodSelector, FallbackHandler


@pytest.fixture(scope="session")
def test_config() -> Config:
    """Test configuration with safe defaults"""
    return Config(
        base_url="https://futures.plus500.com",
        host_url="https://api-futures.plus500.com",
        account_type="demo",
        preferred_method="webdriver",
        webdriver_config={
            "browser": "chrome",
            "headless": True,  # Run headless for tests
            "stealth_mode": True,
            "window_size": (1920, 1080),
            "implicit_wait": 5,
            "page_load_timeout": 15,
        }
    )


@pytest.fixture
def mock_driver():
    """Mock WebDriver instance with common methods"""
    driver = Mock()
    driver.get = Mock()
    driver.quit = Mock()
    driver.close = Mock()
    driver.find_element = Mock()
    driver.find_elements = Mock(return_value=[])
    driver.execute_script = Mock()
    driver.get_cookies = Mock(return_value=[])
    driver.add_cookie = Mock()
    driver.delete_all_cookies = Mock()
    driver.current_url = "https://futures.plus500.com"
    driver.title = "Plus500 Trading Platform"
    driver.page_source = "<html><body>Mock page</body></html>"
    
    # Mock WebElement
    mock_element = Mock()
    mock_element.is_displayed = Mock(return_value=True)
    mock_element.is_enabled = Mock(return_value=True)
    mock_element.click = Mock()
    mock_element.send_keys = Mock()
    mock_element.clear = Mock()
    mock_element.get_attribute = Mock(return_value="mock_value")
    mock_element.text = "Mock text"
    
    driver.find_element.return_value = mock_element
    
    return driver


@pytest.fixture  
def mock_browser_manager(mock_driver):
    """Mock BrowserManager with driver instance"""
    manager = Mock(spec=BrowserManager)
    manager.get_driver = Mock(return_value=mock_driver)
    manager.cleanup = Mock()
    manager.is_driver_alive = Mock(return_value=True)
    manager.restart_driver = Mock(return_value=mock_driver)
    return manager


@pytest.fixture
def mock_element_detector():
    """Mock ElementDetector with common methods"""
    detector = Mock()
    detector.find_element_robust = Mock()
    detector.wait_for_element = Mock()
    detector.extract_text_safe = Mock(return_value="Mock text")
    detector.is_element_present = Mock(return_value=True)
    detector.wait_for_clickable = Mock()
    return detector


@pytest.fixture
def mock_session_manager():
    """Mock SessionManager"""
    session_manager = Mock(spec=SessionManager)
    session_manager.session = Mock()
    session_manager.session.get = Mock()
    session_manager.session.post = Mock()
    session_manager.session.cookies = Mock()
    return session_manager


@pytest.fixture
def temp_profile_dir():
    """Temporary directory for browser profile"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture(scope="function")
def isolated_config(temp_profile_dir):
    """Isolated config for each test"""
    return Config(
        base_url="https://futures.plus500.com",
        account_type="demo",
        preferred_method="webdriver",
        webdriver_config={
            "browser": "chrome",
            "headless": True,
            "profile_path": str(temp_profile_dir),
            "implicit_wait": 2,
            "page_load_timeout": 10,
        }
    )


@pytest.fixture
def mock_webdriver_trading_client(test_config, mock_browser_manager, mock_element_detector):
    """Mock WebDriver trading client"""
    client = WebDriverTradingClient(test_config, mock_browser_manager)
    client.element_detector = mock_element_detector
    client.driver = mock_browser_manager.get_driver()
    return client


@pytest.fixture
def method_selector(test_config):
    """Real MethodSelector instance for testing"""
    return MethodSelector(test_config)


@pytest.fixture  
def fallback_handler(test_config, method_selector):
    """Real FallbackHandler instance for testing"""
    return FallbackHandler(test_config, method_selector)


# Browser automation fixtures

@pytest.fixture(scope="session")
def browser_available():
    """Check if browser automation is available"""
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=options)
        driver.quit()
        return True
    except Exception:
        return False


@pytest.fixture
def real_browser_manager(test_config, browser_available):
    """Real browser manager for integration tests"""
    if not browser_available:
        pytest.skip("Browser automation not available")
    
    manager = BrowserManager(test_config)
    yield manager
    manager.cleanup()


# Test data fixtures

@pytest.fixture
def sample_instrument_data():
    """Sample instrument data for testing"""
    return {
        "id": "TEST_INSTRUMENT",
        "name": "Test Instrument",
        "market": "test",
        "symbol": "TEST",
        "price": 100.50,
        "change": 1.25,
        "change_percent": 1.26
    }


@pytest.fixture
def sample_position_data():
    """Sample position data for testing"""
    return {
        "id": "TEST_POSITION_123",
        "instrument_id": "TEST_INSTRUMENT", 
        "side": "BUY",
        "quantity": 10,
        "price": 100.50,
        "current_price": 102.75,
        "unrealized_pnl": 22.50,
        "timestamp": 1640995200
    }


@pytest.fixture
def sample_order_data():
    """Sample order data for testing"""
    return {
        "id": "TEST_ORDER_456",
        "instrument_id": "TEST_INSTRUMENT",
        "side": "BUY", 
        "order_type": "MARKET",
        "quantity": 5,
        "status": "FILLED",
        "create_time": "2024-01-01T12:00:00Z"
    }


# Authentication test fixtures

@pytest.fixture
def mock_auth_cookies():
    """Mock authentication cookies"""
    return [
        {"name": "session_id", "value": "mock_session_123", "domain": ".plus500.com"},
        {"name": "auth_token", "value": "mock_token_456", "domain": ".plus500.com"},
        {"name": "account_type", "value": "demo", "domain": ".plus500.com"}
    ]


@pytest.fixture
def mock_session_data(mock_auth_cookies):
    """Mock session data from WebDriver authentication"""
    return {
        "cookies": mock_auth_cookies,
        "account_type": "demo",
        "authenticated": True,
        "user_agent": "Mozilla/5.0 (Test Browser)",
        "csrf_token": "mock_csrf_token",
        "timestamp": 1640995200
    }


# Error simulation fixtures

@pytest.fixture
def captcha_error():
    """Mock captcha error"""
    from plus500us_client.errors import CaptchaRequiredError
    return CaptchaRequiredError("Captcha verification required")


@pytest.fixture
def automation_blocked_error():
    """Mock automation blocked error"""
    from plus500us_client.errors import AutomationBlockedError  
    return AutomationBlockedError("Automated access detected and blocked")


@pytest.fixture
def rate_limit_error():
    """Mock rate limit error"""
    from plus500us_client.errors import RateLimitedError
    return RateLimitedError("Rate limit exceeded, please wait")


# Test environment configuration

def pytest_configure(config):
    """Configure pytest environment"""
    # Set environment variables for testing
    os.environ["PLUS500US_TEST_MODE"] = "true"
    os.environ["PLUS500US_ACCOUNT_TYPE"] = "demo"


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers"""
    for item in items:
        # Add markers based on test file location
        if "webdriver" in str(item.fspath):
            item.add_marker(pytest.mark.webdriver)
            
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
            
        if "test_auth" in item.name:
            item.add_marker(pytest.mark.auth)
            
        if "test_trading" in item.name:
            item.add_marker(pytest.mark.trading)
            
        if "captcha" in item.name.lower():
            item.add_marker(pytest.mark.captcha)


# Skip conditions

def pytest_runtest_setup(item):
    """Setup for individual tests with skip conditions"""
    # Skip WebDriver tests if no browser available
    if item.get_closest_marker("webdriver"):
        try:
            from selenium import webdriver
        except ImportError:
            pytest.skip("Selenium not available for WebDriver tests")
    
    # Skip live tests in CI or if not explicitly enabled
    if item.get_closest_marker("live"):
        if not os.getenv("PLUS500US_ENABLE_LIVE_TESTS"):
            pytest.skip("Live tests disabled (set PLUS500US_ENABLE_LIVE_TESTS=1 to enable)")


# Custom assertions

def assert_webdriver_element_interaction(mock_element, expected_calls=1):
    """Assert WebDriver element was interacted with correctly"""
    assert mock_element.is_displayed.call_count >= expected_calls
    

def assert_authentication_flow(mock_driver, expected_navigations=1):
    """Assert authentication flow was executed correctly"""
    assert mock_driver.get.call_count >= expected_navigations


def assert_trading_operation(mock_element_detector, operation_type="market_order"):
    """Assert trading operation was executed correctly"""
    assert mock_element_detector.find_element_robust.call_count > 0