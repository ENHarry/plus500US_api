from .config import Config, load_config
from .session import SessionManager
from .auth import AuthClient
from .trading import TradingClient
from .marketdata import MarketDataClient
from .instruments import InstrumentsClient
from .account import AccountClient
from .post_login import PostLoginDataService
from .risk_management import RiskManagementService, PartialClosureValidator

# Phase 1-3 Enhanced Components

from .risk_manager import AdvancedRiskManager
from .trading_utils import AdvancedTradingUtils

from .hybrid_integration import HybridAPIClient, HybridConfig, FallbackStrategy
from .security import SecureCredentialHandler, SecurityAuditor

from .models import (
    Instrument, Quote, OrderDraft, Order, Position, Account,
    RiskManagementSettings, BracketOrder, PartialTakeProfitRule,
    # Phase 2 Enhanced Models
    Plus500AccountInfo, Plus500InstrumentData, Plus500OrderRequest, Plus500OrderResponse,
    Plus500Position, Plus500ClosedPosition, Plus500OrderInfo, Plus500ApiError,
    Plus500FundsInfo, Plus500InstrumentPrice, Plus500ChartData, Plus500MarginCalculation,
    Plus500OrderValidation, Plus500BuySellInfo
)
from .errors import (
    AuthenticationError, AuthorizationError, AutomationBlockedError,
    RateLimitedError, OrderRejectError, InstrumentNotFound, ValidationError, 
    CaptchaRequiredError, PartialTakeProfitError, RiskManagementError, PositionSizeError,
    TradingError, APIError
)

# WebDriver modules (optional import)
try:
    from ..webdriver import (
        BrowserManager, WebDriverAuthHandler, WebDriverTradingClient,
        Plus500Selectors, ElementDetector, WebDriverUtils
    )
    from ..hybrid import SessionBridge, MethodSelector, FallbackHandler
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
