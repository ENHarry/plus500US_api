from sympy import im
from .requests.config import Config, load_config
from .requests.session import SessionManager
from .requests.auth import AuthClient
from .requests.trading import TradingClient
from .requests.marketdata import MarketDataClient
from .requests.instruments import InstrumentsClient
from .requests.account import AccountClient
from .requests.post_login import PostLoginDataService
from .requests.risk_management import RiskManagementService, PartialClosureValidator

from .requests.plus500_api import Plus500ApiClient  # Pulls from all modules

# Phase 1-3 Enhanced Components
from .requests.risk_manager import AdvancedRiskManager
from .requests.trading_utils import AdvancedTradingUtils
from .requests.hybrid_integration import HybridAPIClient, HybridConfig, FallbackStrategy
from .requests.security import SecureCredentialHandler, SecurityAuditor

from .requests.models import (
    Instrument, Quote, OrderDraft, Order, Position, Account,
    RiskManagementSettings, BracketOrder, PartialTakeProfitRule,
    # Phase 2 Enhanced Models
    Plus500AccountInfo, Plus500InstrumentData, Plus500OrderRequest, Plus500OrderResponse,
    Plus500Position, Plus500ClosedPosition, Plus500OrderInfo, Plus500ApiError,
    Plus500FundsInfo, Plus500InstrumentPrice, Plus500ChartData, Plus500MarginCalculation,
    Plus500OrderValidation, Plus500BuySellInfo
)
from .requests.errors import (
    AuthenticationError, AuthorizationError, AutomationBlockedError,
    RateLimitedError, OrderRejectError, InstrumentNotFound, ValidationError, 
    CaptchaRequiredError, PartialTakeProfitError, RiskManagementError, PositionSizeError,
    TradingError, APIError
)

# WebDriver modules (optional import)
try:
    from .webdriver import (
        BrowserManager, WebDriverAuthHandler, WebDriverTradingClient,
        Plus500Selectors, ElementDetector, WebDriverUtils
    )
    from .hybrid import SessionBridge, MethodSelector, FallbackHandler
    WEBDRIVER_AVAILABLE = True
except ImportError:
    WEBDRIVER_AVAILABLE = False

__all__ = [
    # Core services
    "Config", "load_config", "SessionManager", "AuthClient", "TradingClient",
    "MarketDataClient", "InstrumentsClient", "AccountClient", 
    "PostLoginDataService", "RiskManagementService", "PartialClosureValidator",
    
    # Models
    "Instrument", "Quote", "OrderDraft", "Order", "Position", "Account",
    "RiskManagementSettings", "BracketOrder", "PartialTakeProfitRule",
    
    # Errors
    "AuthenticationError", "AuthorizationError", "AutomationBlockedError",
    "RateLimitedError", "OrderRejectError", "InstrumentNotFound", "ValidationError", 
    "CaptchaRequiredError", "PartialTakeProfitError", "RiskManagementError", "PositionSizeError",
    
    # WebDriver availability
    "WEBDRIVER_AVAILABLE"
]

# Add WebDriver modules to __all__ if available
if WEBDRIVER_AVAILABLE:
    __all__.extend([
        "BrowserManager", "WebDriverAuthHandler", "WebDriverTradingClient",
        "Plus500Selectors", "ElementDetector", "WebDriverUtils",
        "SessionBridge", "MethodSelector", "FallbackHandler"
    ])
