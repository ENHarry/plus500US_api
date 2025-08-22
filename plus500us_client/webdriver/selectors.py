from __future__ import annotations

from pickle import INST
from sre_constants import IN
from typing import Dict, List

class Plus500Selectors:
    """Comprehensive XPath and CSS selectors for Plus500 trading platform"""
    
    # Authentication selectors
    LOGIN_EMAIL = {
        'xpath': [
            "//input[@id='email']",
            "//input[@type='email' and @placeholder='Email']",
            "//input[@type='email' or @name='email' or contains(@class, 'email')]",
            "//input[contains(@placeholder, 'Email') or contains(@id, 'email')]",
            "//input[contains(@data-test, 'email') or contains(@aria-label, 'email')]"
        ],
        'css': [
            "#email",
            "input[type='email'][placeholder='Email']",
            "input[type='email']",
            "input[name='email']", 
            ".email-input",
            "input[placeholder*='email' i]",
            "input[id*='email']"
        ]
    }
    
    LOGIN_PASSWORD = {
        'xpath': [
            "//input[@id='password']",
            "//input[@type='password' and @placeholder='Password']",
            "//input[@type='password' or @name='password']",
            "//input[contains(@placeholder, 'Password') or contains(@id, 'password')]",
            "//input[contains(@data-test, 'password') or contains(@aria-label, 'password')]"
        ],
        'css': [
            "#password",
            "input[type='password'][placeholder='Password']",
            "input[type='password']",
            "input[name='password']",
            ".password-input",
            "input[placeholder*='password' i]",
            "input[id*='password']"
        ]
    }
    
    LOGIN_BUTTON = {
        'xpath': [
            "//button[@id='submitLogin']",
            "//button[contains(text(), 'Log') or contains(text(), 'Sign') or @type='submit']",
            "//button[contains(@class, 'login') or contains(@class, 'submit')]",
            "//input[@type='submit' and (contains(@value, 'Log') or contains(@value, 'Sign'))]",
            "//a[contains(@class, 'login') or contains(text(), 'Login')]"
        ],
        'css': [
            "#submitLogin",
            "button[type='submit']",
            ".login-button",
            ".submit-button",
            "button[class*='login']",
            "input[type='submit']"
        ]
    }

    KEEP_ME_LOGGED_IN = {
        'xpath': [
            "//input[@id='keepMeLoggedIn']",
            "//input[@type='checkbox' and contains(@class, 'checkbox-custom-text')]",
            "//label[contains(text(), 'Keep me logged in')]"
        ],
        'css': [
            "#keepMeLoggedIn",
            "input[type='checkbox'][class*='checkbox-custom-text']",
            "label:contains('Keep me logged in')"
        ]
    }

    # Trading interface selectors
    INSTRUMENT_SEARCH = {
        'xpath': [
            "//input[contains(@placeholder, 'Search') or contains(@class, 'search')]",
            "//input[contains(@data-test, 'instrument') or contains(@aria-label, 'instrument')]",
            "//input[contains(@id, 'search') or contains(@name, 'search')]"
        ],
        'css': [
            "input[placeholder*='search' i]",
            ".instrument-search",
            "input[data-test*='instrument']",
            "#search",
            "input[name='search']"
        ]
    }

    INSTRUMENT_LIST = {
        'xpath': [
            "//div[contains(@class, 'instrument-list')]",
            "//h2[contains(@class, 'instrument-title')]",
            "//span[contains(@class, 'instrument-price')]"
        ],
        'css': [
            ".instrument-list",
            ".instrument-title",
            ".instrument-price"
        ]
    }

    INSTRUMENT_DETAILS = {
        'xpath': [
            "//div[contains(@class, 'instrument-details')]",
            "//h1[contains(@class, 'instrument-name')]",
            "//span[contains(@class, 'instrument-price')]"
        ],
        'css': [
            ".instrument-details",
            ".instrument-name",
            ".instrument-price"
        ]
    }

    BUY_BUTTON = {
        'xpath': [
            "//button[contains(text(), 'Buy') or contains(@class, 'buy')]",
            "//button[contains(@data-action, 'buy') or contains(@data-side, 'buy')]",
            "//div[contains(@class, 'buy')]/button",
            "//button[contains(@aria-label, 'buy')]"
        ],
        'css': [
            ".buy-button",
            "button[data-action='buy']",
            "button[data-side='buy']",
            "button[class*='buy']",
            ".trade-buy"
        ]
    }
    
    SELL_BUTTON = {
        'xpath': [
            "//button[contains(text(), 'Sell') or contains(@class, 'sell')]",
            "//button[contains(@data-action, 'sell') or contains(@data-side, 'sell')]",
            "//div[contains(@class, 'sell')]/button",
            "//button[contains(@aria-label, 'sell')]"
        ],
        'css': [
            ".sell-button",
            "button[data-action='sell']",
            "button[data-side='sell']",
            "button[class*='sell']",
            ".trade-sell"
        ]
    }
    
    QUANTITY_INPUT = {
        'xpath': [
            "//input[@type='number' and (contains(@class, 'quantity') or contains(@name, 'quantity'))]",
            "//input[contains(@placeholder, 'quantity') or contains(@placeholder, 'amount')]",
            "//input[contains(@data-test, 'quantity') or contains(@aria-label, 'quantity')]",
            "//input[contains(@id, 'qty') or contains(@name, 'qty')]"
        ],
        'css': [
            "input[type='number'][class*='quantity']",
            "input[name='quantity']",
            ".quantity-input",
            "input[placeholder*='quantity' i]",
            "input[name='qty']",
            "input[id*='qty']"
        ]
    }
    
    PRICE_INPUT = {
        'xpath': [
            "//input[contains(@class, 'price') or @name='price']",
            "//input[contains(@placeholder, 'price') or contains(@placeholder, 'limit')]",
            "//input[contains(@data-test, 'price') or contains(@aria-label, 'price')]",
            "//input[contains(@id, 'price') or contains(@name, 'limit')]"
        ],
        'css': [
            ".price-input",
            "input[name='price']",
            "input[placeholder*='price' i]",
            "input[name='limit']",
            "input[id*='price']"
        ]
    }
    
    # Order type selectors
    MARKET_ORDER = {
        'xpath': [
            "//button[contains(text(), 'Market') or contains(@value, 'market')]",
            "//input[@type='radio' and contains(@value, 'market')]",
            "//label[contains(text(), 'Market')]/input"
        ],
        'css': [
            "button[value='market']",
            "input[value='market']",
            ".market-order"
        ]
    }
    
    LIMIT_ORDER = {
        'xpath': [
            "//button[contains(text(), 'Limit') or contains(@value, 'limit')]",
            "//input[@type='radio' and contains(@value, 'limit')]",
            "//label[contains(text(), 'Limit')]/input"
        ],
        'css': [
            "button[value='limit']",
            "input[value='limit']",
            ".limit-order"
        ]
    }
    
    STOP_ORDER = {
        'xpath': [
            "//button[contains(text(), 'Stop') or contains(@value, 'stop')]",
            "//input[@type='radio' and contains(@value, 'stop')]",
            "//label[contains(text(), 'Stop')]/input"
        ],
        'css': [
            "button[value='stop']",
            "input[value='stop']",
            ".stop-order"
        ]
    }
    
    # Position management selectors
    POSITIONS_TABLE = {
        'xpath': [
            "//table[contains(@class, 'positions') or .//th[contains(text(), 'Position')]]",
            "//div[contains(@class, 'positions-grid') or contains(@data-test, 'positions')]",
            "//table[.//th[contains(text(), 'Instrument')] and .//th[contains(text(), 'P&L')]]"
        ],
        'css': [
            ".positions-table",
            "table[data-table='positions']",
            ".positions-grid",
            "[data-test='positions-table']"
        ]
    }
    
    POSITION_ROW = {
        'xpath': [
            "//tr[contains(@class, 'position-row') or contains(@data-position-id, '{position_id}')]",
            "//tr[.//td[contains(text(), '{instrument}')]]",
            "//div[contains(@class, 'position-item') and contains(., '{instrument}')]"
        ],
        'css': [
            "tr[data-position-id='{position_id}']",
            ".position-row",
            "tr.position"
        ]
    }
    
    CLOSE_POSITION = {
        'xpath': [
            "//button[contains(text(), 'Close') or contains(@class, 'close')]",
            "//button[contains(@data-action, 'close') or contains(@aria-label, 'close')]",
            "//a[contains(@class, 'close') or contains(text(), 'Close')]"
        ],
        'css': [
            ".close-position",
            "button[data-action='close']",
            ".close-btn",
            "button[class*='close']"
        ]
    }
    
    # Stop Loss / Take Profit selectors
    STOP_LOSS_INPUT = {
        'xpath': [
            "//input[contains(@class, 'stop-loss') or @name='stopLoss']",
            "//input[contains(@placeholder, 'Stop') or contains(@data-test, 'stop-loss')]",
            "//input[contains(@id, 'sl') or contains(@name, 'sl')]"
        ],
        'css': [
            ".stop-loss-input",
            "input[name='stopLoss']",
            "input[placeholder*='Stop' i]",
            "input[id*='sl']",
            "input[name='sl']"
        ]
    }
    
    TAKE_PROFIT_INPUT = {
        'xpath': [
            "//input[contains(@class, 'take-profit') or @name='takeProfit']",
            "//input[contains(@placeholder, 'Take') or contains(@data-test, 'take-profit')]",
            "//input[contains(@id, 'tp') or contains(@name, 'tp')]"
        ],
        'css': [
            ".take-profit-input",
            "input[name='takeProfit']",
            "input[placeholder*='Take' i]",
            "input[id*='tp']",
            "input[name='tp']"
        ]
    }
    
    # Order confirmation and submission
    CONFIRM_ORDER = {
        'xpath': [
            "//button[contains(text(), 'Confirm') or contains(text(), 'Submit')]",
            "//button[contains(@class, 'confirm') or contains(@class, 'submit')]",
            "//button[contains(@data-action, 'confirm') or @type='submit']"
        ],
        'css': [
            ".confirm-btn",
            ".submit-order",
            "button[data-action='confirm']",
            "button[type='submit']"
        ]
    }
    
    # Loading and status indicators
    LOADING_SPINNER = {
        'xpath': [
            "//div[contains(@class, 'loading') or contains(@class, 'spinner')]",
            "//div[contains(@class, 'progress') or contains(@aria-label, 'loading')]"
        ],
        'css': [
            ".loading",
            ".spinner",
            ".progress-indicator",
            "[aria-label*='loading']"
        ]
    }
    
    SUCCESS_MESSAGE = {
        'xpath': [
            "//div[contains(@class, 'success') or contains(@class, 'notification')]",
            "//div[contains(text(), 'successful') or contains(text(), 'confirmed')]"
        ],
        'css': [
            ".success-message",
            ".notification.success",
            ".alert-success"
        ]
    }
    
    ERROR_MESSAGE = {
        'xpath': [
            "//div[contains(@class, 'error') or contains(@class, 'alert')]",
            "//div[contains(text(), 'error') or contains(text(), 'failed')]"
        ],
        'css': [
            ".error-message",
            ".notification.error",
            ".alert-error"
        ]
    }
    
    # Dashboard and navigation
    DASHBOARD_INDICATOR = {
        'xpath': [
            # Account switch control indicates successful login (highest priority)
            "//a[@id='switchModeSubNav']",
            # Account balance elements
            "//div[contains(@class, 'account-balance') or contains(@class, 'equity-value')]",
            "//span[contains(@class, 'balance') or contains(text(), '$')]",
            # Trading interface elements
            "//div[contains(@class, 'section-table instruments') or contains(@class, 'categories-instruments')]",
            "//div[@id='instrumentsRepeater']",
            # Navigation elements
            "//nav[contains(@class, 'main-nav') or contains(@class, 'trading-nav')]",
            "//h3[contains(text(), 'My Watchlist') or contains(text(), 'Most Popular')]",
            # User menu/profile elements
            "//div[contains(@class, 'user-menu') or contains(@class, 'profile')]",
            # Plus500 specific post-login elements
            "//div[contains(@class, 'trading-workspace')]",
            "//div[contains(@class, 'instrument-list')]"
        ],
        'css': [
            # Account switching (primary indicator)
            "#switchModeSubNav",
            ".switch-mode",
            # Balance/account elements
            ".account-balance",
            ".equity-value", 
            ".balance-display",
            # Trading dashboard elements
            "#instrumentsRepeater",
            ".section-table-body",
            ".categories-instruments",
            # General dashboard selectors
            ".dashboard",
            ".trading-dashboard",
            ".main-navigation",
            "[data-page='dashboard']",
            ".trading-workspace",
            ".instrument-list"
        ]
    }
    
    BALANCE_DISPLAY = {
        'xpath': [
            "//span[contains(text(), 'Balance') or contains(@class, 'balance')]",
            "//div[contains(@class, 'account-balance') or contains(@data-test, 'balance')]",
            "//span[contains(@aria-label, 'balance')]"
        ],
        'css': [
            ".balance",
            ".account-balance",
            "[data-test='balance']",
            "[aria-label*='balance']"
        ]
    }

    @classmethod
    def get_dynamic_selector(cls, base_selector: str, **kwargs) -> str:
        """Generate dynamic selectors with variable substitution"""
        return base_selector.format(**kwargs)
    
    # Enhanced Plus500US specific selectors
    
    # Updated instrument table selectors for new HTML structure
    CATEGORIES_INSTRUMENTS_CONTAINER = {
        'xpath': [
            "//div[@id='categoriesInstruments']",
            "//div[contains(@class, 'categories-instruments')]"
        ],
        'css': [
            "#categoriesInstruments",
            ".categories-instruments"
        ]
    }
    
    INSTRUMENTS_REPEATER = {
        'xpath': [
            "//div[@id='instrumentsRepeater']",
            "//div[contains(@class, 'section-table-body')]"
        ],
        'css': [
            "#instrumentsRepeater",
            ".section-table-body"
        ]
    }
    
    # Account Management Selectors
    ACCOUNT_SWITCH_CONTROL = {
        'xpath': [
            "//a[@id='switchModeSubNav']",
            "//a[contains(@class, 'switch-mode')]"
        ],
        'css': [
            "#switchModeSubNav",
            ".switch-mode"
        ]
    }
    
    # Account type detection - Enhanced for Plus500 structure
    ACTIVE_ACCOUNT_TYPE = {
        'xpath': [
            # Primary selectors for active account detection
            "//a[@id='switchModeSubNav']//span[@class='active']",
            "//span[@class='active' and (contains(text(), 'Demo') or contains(text(), 'Real'))]",
            # Alternative selectors for account type detection
            "//div[contains(@class, 'account-type')]//span[@class='active']",
            "//span[contains(@class, 'account-mode') and contains(@class, 'active')]",
            # Text-based detection
            "//span[contains(@class, 'active') and normalize-space(text())]"
        ],
        'css': [
            "#switchModeSubNav span.active",
            "#switchModeSubNav > span.active",
            ".switch-mode span.active",
            ".account-type span.active",
            ".account-mode.active",
            "span.active"
        ]
    }
    
    DEMO_MODE_SPAN = {
        'xpath': [
            # Primary demo mode selectors
            "//a[@id='switchModeSubNav']//span[contains(text(), 'Demo Mode') or contains(text(), 'Demo')]",
            "//a[@id='switchModeSubNav']/span[contains(text(), 'Demo')]",
            "//span[contains(text(), 'Demo Mode') or contains(text(), 'Demo')]",
            # Alternative demo detection
            "//span[contains(@class, 'demo') or @data-mode='demo']",
            "//div[contains(@class, 'demo-account')]//span",
            # Class-based demo detection
            "//span[contains(@class, 'account-demo') or contains(@class, 'mode-demo')]"
        ],
        'css': [
            "#switchModeSubNav span[text*='Demo' i]",
            ".switch-mode span[text*='Demo' i]",
            "span[class*='demo']",
            "[data-mode='demo']",
            ".account-demo",
            ".mode-demo"
        ]
    }
    
    REAL_MODE_SPAN = {
        'xpath': [
            # Primary real/live mode selectors
            "//a[@id='switchModeSubNav']//span[contains(text(), 'Real Money') or contains(text(), 'Real') or contains(text(), 'Live')]",
            "//a[@id='switchModeSubNav']/span[contains(text(), 'Real') or contains(text(), 'Live')]",
            "//span[contains(text(), 'Real Money') or contains(text(), 'Real') or contains(text(), 'Live')]",
            # Alternative real/live detection
            "//span[contains(@class, 'real') or contains(@class, 'live') or @data-mode='real']",
            "//div[contains(@class, 'real-account') or contains(@class, 'live-account')]//span",
            # Class-based real detection
            "//span[contains(@class, 'account-real') or contains(@class, 'mode-real') or contains(@class, 'account-live')]"
        ],
        'css': [
            "#switchModeSubNav span[text*='Real' i], #switchModeSubNav span[text*='Live' i]",
            ".switch-mode span[text*='Real' i], .switch-mode span[text*='Live' i]",
            "span[class*='real'], span[class*='live']",
            "[data-mode='real'], [data-mode='live']",
            ".account-real",
            ".mode-real",
            ".account-live"
        ]
    }
    
    # Account Balance and Margin Selectors
    EQUITY_VALUE = {
        'xpath': [
            "//li[@automation='equity']/span[@data-currency]",
            "//li[@automation='equity']/span[contains(@title, 'Total Account Value')]"
        ],
        'css': [
            "li[automation='equity'] span[data-currency]",
            "li[automation='equity'] span"
        ]
    }
    
    TOTAL_PNL = {
        'xpath': [
            "//li[@automation='total-positions-pl']/span[@data-currency]",
            "//li[@automation='total-positions-pl']/span[contains(@title, 'Total Profit')]"
        ],
        'css': [
            "li[automation='total-positions-pl'] span[data-currency]",
            "li[automation='total-positions-pl'] span"
        ]
    }
    
    LIVE_MARGIN_AVAILABLE = {
        'xpath': [
            "//li[@automation='live-margin-available']/span[@data-currency]",
            "//li[@automation='live-margin-available']/span[contains(@title, 'margin amount')]"
        ],
        'css': [
            "li[automation='live-margin-available'] span[data-currency]",
            "li[automation='live-margin-available'] span"
        ]
    }
    
    FULL_MARGIN_AVAILABLE = {
        'xpath': [
            "//li[@automation='full-margin-available']/span[@data-currency]",
            "//li[@automation='full-margin-available']/span[contains(@title, 'margin amount')]"
        ],
        'css': [
            "li[automation='full-margin-available'] span[data-currency]",
            "li[automation='full-margin-available'] span"
        ]
    }
    
    # Instrument Discovery Selectors
    INSTRUMENT_CATEGORIES_CONTAINER = {
        'xpath': [
            "//div[@id='categories']",
            "//div[contains(@class, 'categories')]"
        ],
        'css': [
            "#categories",
            ".categories"
        ]
    }
    
    INSTRUMENT_CATEGORY_LINKS = {
        'xpath': [
            "//div[@id='categories']//a[not(contains(@class, 'selected'))]",
            "//div[@id='categories']//li/a"
        ],
        'css': [
            "#categories a",
            "#categories li a"
        ]
    }
    
    SELECTED_CATEGORY = {
        'xpath': [
            "//div[@id='categories']//a[@class='selected']",
            "//div[@id='categories']//a[contains(@class, 'selected')]"
        ],
        'css': [
            "#categories a.selected",
            "#categories .selected"
        ]
    }
    
    INSTRUMENTS_TABLE_CONTAINER = {
        'xpath': [
            "//div[@id='instrumentsTable']",
            "//div[contains(@class, 'instruments')]"
        ],
        'css': [
            "#instrumentsTable",
            ".instruments"
        ]
    }
    
    INSTRUMENT_ROWS = {
        'xpath': [
            "//div[@class='instrument-row instrument']",
            "//div[contains(@class, 'instrument-row')]"
        ],
        'css': [
            ".instrument-row.instrument",
            ".instrument-row"
        ]
    }
    
    INSTRUMENT_NAME = {
        'xpath': [
            ".//div[@class='name']//strong",
            ".//div[contains(@class, 'name')]//strong"
        ],
        'css': [
            ".name strong",
            ".name-medium strong",
            ".name-long strong"
        ]
    }
    
    INSTRUMENT_PRICES = {
        'xpath': [
            ".//div[@class='sell' and @data-no-trading]",
            ".//div[@class='buy' and @data-no-trading]"
        ],
        'css': [
            ".sell[data-no-trading]",
            ".buy[data-no-trading]"
        ]
    }
    
    INSTRUMENT_INFO_BUTTON = {
        'xpath': [
            ".//button[@class='open-info icon-info-circle']",
            ".//button[contains(@class, 'open-info')]"
        ],
        'css': [
            ".open-info.icon-info-circle",
            ".open-info"
        ]
    }
    
    # Closed Positions and PnL Analysis Selectors
    CLOSED_POSITIONS_NAV = {
        'xpath': [
            "//a[@id='closedPositionsNav']",
            "//a[contains(@class, 'icon-futures-history')]",
            "//a[contains(text(), 'Closed Positions')]"
        ],
        'css': [
            "#closedPositionsNav",
            ".icon-futures-history",
            "a[text='Closed Positions']"
        ]
    }
    
    TRADE_HISTORY_TABLE = {
        'xpath': [
            "//div[contains(@class, 'futures-closed-positions')]",
            "//div[contains(@class, 'section-table')]"
        ],
        'css': [
            ".futures-closed-positions",
            ".section-table"
        ]
    }
    
    TRADE_HISTORY_ROWS = {
        'xpath': [
            "//div[@class='history']",
            "//div[contains(@class, 'history')]"
        ],
        'css': [
            ".history",
            "div.history"
        ]
    }
    
    TRADE_DATE = {
        'xpath': [
            ".//div[@class='date']",
            ".//div[contains(@class, 'date')]"
        ],
        'css': [
            ".date",
            "div.date"
        ]
    }
    
    TRADE_ACTION = {
        'xpath': [
            ".//div[@class='action']",
            ".//div[contains(@class, 'action')]"
        ],
        'css': [
            ".action",
            "div.action"
        ]
    }
    
    TRADE_AMOUNT = {
        'xpath': [
            ".//div[@class='amount']",
            ".//div[contains(@class, 'amount')]"
        ],
        'css': [
            ".amount",
            "div.amount"
        ]
    }
    
    TRADE_INSTRUMENT = {
        'xpath': [
            ".//div[@class='name']//strong",
            ".//div[contains(@class, 'name')]//strong"
        ],
        'css': [
            ".name strong",
            "div.name strong"
        ]
    }
    
    TRADE_OPEN_PRICE = {
        'xpath': [
            ".//div[@class='open-price']",
            ".//div[contains(@class, 'open-price')]"
        ],
        'css': [
            ".open-price",
            "div.open-price"
        ]
    }
    
    TRADE_CLOSE_PRICE = {
        'xpath': [
            ".//div[@class='close-price']",
            ".//div[contains(@class, 'close-price')]"
        ],
        'css': [
            ".close-price",
            "div.close-price"
        ]
    }
    
    TRADE_PNL = {
        'xpath': [
            ".//div[@class='pl green']",
            ".//div[@class='pl red']",
            ".//div[contains(@class, 'pl')]"
        ],
        'css': [
            ".pl.green",
            ".pl.red",
            ".pl"
        ]
    }
    
    # Date Filter Selectors
    DATE_FILTER_FROM = {
        'xpath': [
            "//input[@id and contains(@id, 'dp') and @readonly]",
            "//label[@id='from']/following-sibling::input"
        ],
        'css': [
            "input[id*='dp'][readonly]",
            "label#from + input"
        ]
    }
    
    DATE_FILTER_TO = {
        'xpath': [
            "//label[@id='to']/following-sibling::input",
            "//input[@readonly and contains(@class, 'hasDatepicker')]"
        ],
        'css': [
            "label#to + input",
            "input.hasDatepicker[readonly]"
        ]
    }
    
    DATE_FILTER_SUBMIT = {
        'xpath': [
            "//button[@id='date-filter-submit']",
            "//button[contains(@class, 'date-filter-submit') and contains(text(), 'Display')]"
        ],
        'css': [
            "#date-filter-submit",
            ".date-filter-submit"
        ]
    }

    # Plus500US Specific Navigation Selectors
    POSITIONS_NAV = {
        'xpath': [
            "//a[@id='positionsFuturesNav']",
            "//a[contains(@class, 'icon-futures-positions')]",
            "//a[contains(text(), 'Positions')]"
        ],
        'css': [
            "#positionsFuturesNav",
            ".icon-futures-positions",
            "a[text='Positions']"
        ]
    }
    
    ORDERS_NAV = {
        'xpath': [
            "//a[@id='ordersFuturesNav']",
            "//a[contains(@class, 'icon-futures-orders')]",
            "//a[contains(text(), 'Orders')]"
        ],
        'css': [
            "#ordersFuturesNav",
            ".icon-futures-orders",
            "a[text='Orders']"
        ]
    }
    
    # Plus500US Positions Table Selectors
    POSITIONS_TABLE_CONTAINER = {
        'xpath': [
            "//div[contains(@class, 'futures-positions')]",
            "//div[contains(@class, 'section-table')]"
        ],
        'css': [
            ".futures-positions",
            ".section-table"
        ]
    }
    
    POSITION_ROWS = {
        'xpath': [
            "//div[contains(@class, 'position')]",
            "//div[@class='section-table-body']//div[contains(@class, 'icon-tag')]"
        ],
        'css': [
            ".position",
            ".section-table-body .icon-tag"
        ]
    }
    
    # Plus500US Orders Table Selectors
    ORDERS_TABLE_CONTAINER = {
        'xpath': [
            "//div[contains(@class, 'futures-orders')]",
            "//div[contains(@class, 'section-table')]"
        ],
        'css': [
            ".futures-orders",
            ".section-table"
        ]
    }
    
    ORDER_ROWS = {
        'xpath': [
            "//div[contains(@class, 'order')]",
            "//div[@class='section-table-body']//div[contains(@class, 'icon-tag')]"
        ],
        'css': [
            ".order",
            ".section-table-body .icon-tag"
        ]
    }
    
    # Plus500US Trading Interface Selectors
    TRADING_SIDEBAR = {
        'xpath': [
            "//div[contains(@class, 'sidebar-trade')]",
            "//div[contains(@class, 'instrument-header')]"
        ],
        'css': [
            ".sidebar-trade",
            ".instrument-header"
        ]
    }
    
    BUY_SELL_SELECTOR = {
        'xpath': [
            "//div[contains(@class, 'buysell-selection')]//select",
            "//select[contains(@class, 'opertion-switcher')]"
        ],
        'css': [
            ".buysell-selection select",
            "select.opertion-switcher"
        ]
    }
    
    CURRENT_PRICE_DISPLAY = {
        'xpath': [
            "//div[contains(@class, 'rate') and @title='Last Traded Rate']",
            "//div[contains(@class, 'data')]//div[contains(@class, 'rate')]"
        ],
        'css': [
            ".rate[title='Last Traded Rate']",
            ".data .rate"
        ]
    }
    
    # Risk Management Selectors (Plus500US specific)
    TRAILING_STOP_SWITCH = {
        'xpath': [
            "//plus500-switch[@data-testid='trailingStop']",
            "//plus500-switch[contains(., 'Trailing Stop')]"
        ],
        'css': [
            "plus500-switch[data-testid='trailingStop']",
            "plus500-switch:has(.inner-label:contains('Trailing Stop'))"
        ]
    }
    
    TRAILING_STOP_INPUT = {
        'xpath': [
            "//plus500-switch[@data-testid='trailingStop']/following-sibling::div//input[@type='tel']",
            "//div[contains(@class, 'spinbox') and .//plus500-switch[@data-testid='trailingStop']]//input[@type='tel']"
        ],
        'css': [
            "plus500-switch[data-testid='trailingStop'] + .spinbox-inner input[type='tel']",
            ".spinbox:has(plus500-switch[data-testid='trailingStop']) input[type='tel']"
        ]
    }
    
    STOP_LOSS_SWITCH = {
        'xpath': [
            "//plus500-switch[@data-testid='stopLoss']",
            "//plus500-switch[contains(., 'Stop Loss')]"
        ],
        'css': [
            "plus500-switch[data-testid='stopLoss']",
            "plus500-switch:has(.inner-label:contains('Stop Loss'))"
        ]
    }
    
    TAKE_PROFIT_SWITCH = {
        'xpath': [
            "//plus500-switch[@data-testid='takeProfit']",
            "//plus500-switch[contains(., 'Take Profit')]"
        ],
        'css': [
            "plus500-switch[data-testid='takeProfit']",
            "plus500-switch:has(.inner-label:contains('Take Profit'))"
        ]
    }
    
    PLACE_ORDER_BUTTON = {
        'xpath': [
            "//button[@id='trade-button']",
            "//button[contains(text(), 'Place') and (contains(text(), 'Buy') or contains(text(), 'Sell'))]"
        ],
        'css': [
            "#trade-button",
            "button[id='trade-button']"
        ]
    }
    
    # Position Management Selectors
    POSITION_CLOSE_BUTTON = {
        'xpath': [
            "//button[contains(@class, 'close-position')]",
            "//button[contains(text(), 'Close')]"
        ],
        'css': [
            ".close-position",
            "button[class*='close']"
        ]
    }
    
    POSITION_EDIT_BUTTON = {
        'xpath': [
            "//a[contains(@class, 'edit-order')]",
            "//a[contains(text(), 'Edit')]"
        ],
        'css': [
            ".edit-order",
            "a[class*='edit']"
        ]
    }
    
    # Order Management Selectors  
    ORDER_CANCEL_BUTTON = {
        'xpath': [
            "//button[contains(@class, 'cancel-order')]",
            "//button[contains(text(), 'Cancel')]"
        ],
        'css': [
            ".cancel-order",
            "button[class*='cancel']"
        ]
    }
    
    ORDER_EDIT_BUTTON = {
        'xpath': [
            "//a[contains(@class, 'edit-order')]",
            "//a[contains(text(), 'Edit')]"
        ],
        'css': [
            ".edit-order",
            "a[class*='edit']"
        ]
    }

    # Enhanced Info Extraction Selectors
    SIDEBAR_CONTAINER = {
        'xpath': [
            "//div[@id='side-bar-container']",
            "//div[contains(@class, 'sidebar-content')]"
        ],
        'css': [
            "#side-bar-container",
            ".sidebar-content"
        ]
    }
    
    TRADE_TAB = {
        'xpath': [
            "//li[@class='tab-trade']//button",
            "//button[contains(text(), 'Trade')]"
        ],
        'css': [
            ".tab-trade button",
            "li.tab-trade button"
        ]
    }
    
    INFO_TAB = {
        'xpath': [
            "//li[@class='tab-information']//button",
            "//li[contains(@class, 'tab-information')]//button",
            "//button[contains(text(), 'Info')]"
        ],
        'css': [
            ".tab-information button",
            "li.tab-information button"
        ]
    }
    
    INSTRUMENT_SYMBOL = {
        'xpath': [
            "//span[contains(@class, 'sym') and contains(text(), '(')]",
            "//span[@data-ltr and contains(text(), '(')]"
        ],
        'css': [
            ".sym",
            "span[data-ltr]"
        ]
    }
    
    INSTRUMENT_FULL_NAME = {
        'xpath': [
            "//h4[contains(@class, 'name-long')]//strong[@class='name']",
            "//strong[@class='name']"
        ],
        'css': [
            ".name-long .name",
            "strong.name"
        ]
    }
    
    CURRENT_RATE_DISPLAY = {
        'xpath': [
            "//div[@title='Last Traded Rate' and contains(@class, 'rate')]",
            "//div[contains(@class, 'rate') and not(contains(@class, 'change'))]"
        ],
        'css': [
            ".rate[title='Last Traded Rate']",
            ".data .rate"
        ]
    }
    
    SELL_PRICE_BUTTON = {
        'xpath': [
            "//button[@class='info-button-sell buySellButton']",
            "//button[contains(@class, 'info-button-sell')]"
        ],
        'css': [
            ".info-button-sell.buySellButton",
            ".info-button-sell"
        ]
    }
    
    BUY_PRICE_BUTTON = {
        'xpath': [
            "//button[@class='info-button-buy buySellButton']",
            "//button[contains(@class, 'info-button-buy')]"
        ],
        'css': [
            ".info-button-buy.buySellButton",
            ".info-button-buy"
        ]
    }
    
    LIVE_STATISTICS_SECTION = {
        'xpath': [
            "//div[@id='dailyChange']",
            "//div[@class='daily-change']"
        ],
        'css': [
            "#dailyChange",
            ".daily-change"
        ]
    }
    
    CHANGE_5MIN = {
        'xpath': [
            "//div[@id='dailyChange']//small[contains(text(), '5 minutes')]/following-sibling::span",
            "//small[contains(text(), '5 minutes')]/following-sibling::span"
        ],
        'css': [
            "#dailyChange small:contains('5 minutes') + span",
            "small:contains('5 minutes') + span"
        ]
    }
    
    CHANGE_1HOUR = {
        'xpath': [
            "//div[@id='dailyChange']//small[contains(text(), '60 minutes')]/following-sibling::span",
            "//small[contains(text(), '60 minutes')]/following-sibling::span"
        ],
        'css': [
            "#dailyChange small:contains('60 minutes') + span",
            "small:contains('60 minutes') + span"
        ]
    }
    
    CHANGE_1DAY = {
        'xpath': [
            "//div[@id='dailyChange']//small[contains(text(), '1 day')]/following-sibling::span",
            "//small[contains(text(), '1 day')]/following-sibling::span"
        ],
        'css': [
            "#dailyChange small:contains('1 day') + span",
            "small:contains('1 day') + span"
        ]
    }
    
    HIGH_LOW_METER_5MIN = {
        'xpath': [
            "//span[@class='bar-title' and contains(text(), '5 minutes')]/preceding-sibling::span[@class='bar-value']",
            "//span[@class='bar-title' and contains(text(), '5 minutes')]/following-sibling::span[@class='bar-value']"
        ],
        'css': [
            ".bar-title:contains('5 minutes') ~ .bar-value",
            ".daily-change-meter:has(.bar-title:contains('5 minutes')) .bar-value"
        ]
    }
    
    HIGH_LOW_METER_1HOUR = {
        'xpath': [
            "//span[@class='bar-title' and contains(text(), '60 minutes')]/preceding-sibling::span[@class='bar-value']",
            "//span[@class='bar-title' and contains(text(), '60 minutes')]/following-sibling::span[@class='bar-value']"
        ],
        'css': [
            ".bar-title:contains('60 minutes') ~ .bar-value",
            ".daily-change-meter:has(.bar-title:contains('60 minutes')) .bar-value"
        ]
    }
    
    HIGH_LOW_METER_1DAY = {
        'xpath': [
            "//span[@class='bar-title' and contains(text(), '1 day')]/preceding-sibling::span[@class='bar-value']",
            "//span[@class='bar-title' and contains(text(), '1 day')]/following-sibling::span[@class='bar-value']"
        ],
        'css': [
            ".bar-title:contains('1 day') ~ .bar-value",
            ".daily-change-meter:has(.bar-title:contains('1 day')) .bar-value"
        ]
    }
    
    COMMISSION_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Commissions')]/following-sibling::span[@data-currency]",
            "//span[contains(text(), 'Commissions')]/following-sibling::span[@data-currency]"
        ],
        'css': [
            ".data-label:contains('Commissions') + span[data-currency]",
            "span:contains('Commissions') ~ span[data-currency]"
        ]
    }
    
    DAY_MARGIN_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Day')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'Day Margin')]/following-sibling::span[@data-currency]"
        ],
        'css': [
            ".data-label:contains('Day') + span[data-percent='true']",
            "span:contains('Day Margin') ~ span[data-currency]"
        ]
    }
    
    PLACE_ORDER_MARGIN_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Place Order')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'Place Order')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Place Order') + span[data-percent='true']",
            "span:contains('Place Order') ~ span"
        ]
    }
    
    FULL_MARGIN_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Full')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'Full')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Full') + span[data-percent='true']",
            "span:contains('Full') ~ span"
        ]
    }
    
    AUTO_LIQUIDATION_COMMISSION = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Auto-Liquidation')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'Auto-Liquidation')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Auto-Liquidation') + span[data-percent='true']",
            "span:contains('Auto-Liquidation') ~ span"
        ]
    }
    
    EXPIRY_DATE_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'expiry')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'expiry')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('expiry') + span[data-percent='true']",
            "span:contains('expiry') ~ span"
        ]
    }
    
    CURRENT_TRADING_SESSION = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Current trading session')]/following-sibling::span[@class='value']",
            "//span[contains(text(), 'Current trading session')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Current trading session') + .value",
            "span:contains('Current trading session') ~ span"
        ]
    }
    
    NEXT_TRADING_SESSION = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Next trading session')]/following-sibling::span[@class='value']",
            "//span[contains(text(), 'Next trading session')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Next trading session') + .value",
            "span:contains('Next trading session') ~ span"
        ]
    }
    
    SINGLE_CONTRACT_VALUE = {
        'xpath': [
            "//span[@id='single-contract-value']",
            "//span[@class='data-label' and contains(., 'Single Contract Value')]/following-sibling::span[@class='value']"
        ],
        'css': [
            "#single-contract-value",
            ".data-label:contains('Single Contract Value') + .value"
        ]
    }
    
    UNITS_PER_CONTRACT = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Units per Contract')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'Units per Contract')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Units per Contract') + span[data-percent='true']",
            "span:contains('Units per Contract') ~ span"
        ]
    }
    
    EXCHANGE_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Exchange')]/following-sibling::span[@class='value']",
            "//span[contains(text(), 'Exchange')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Exchange') + .value",
            "span:contains('Exchange') ~ span"
        ]
    }
    
    TICK_SIZE_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Tick size')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'Tick size')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Tick size') + span[data-percent='true']",
            "span:contains('Tick size') ~ span"
        ]
    }
    
    TICK_VALUE_INFO = {
        'xpath': [
            "//span[@class='data-label' and contains(., 'Tick value')]/following-sibling::span[@data-percent='true']",
            "//span[contains(text(), 'Tick value')]/following-sibling::span"
        ],
        'css': [
            ".data-label:contains('Tick value') + span[data-percent='true']",
            "span:contains('Tick value') ~ span"
        ]
    }
    
    # Order Management Selectors
    EDIT_ORDER_BUTTON = {
        'xpath': [
            "//a[@class='edit-order icon-pencil']",
            "//a[contains(@class, 'edit-order')]"
        ],
        'css': [
            ".edit-order.icon-pencil",
            ".edit-order"
        ]
    }
    
    CANCEL_ORDER_BUTTON = {
        'xpath': [
            "//button[@class='cancel-order icon-times']",
            "//button[contains(@class, 'cancel-order')]"
        ],
        'css': [
            ".cancel-order.icon-times",
            ".cancel-order"
        ]
    }
    
    # Enhanced Instrument Row Selectors (updated for new HTML)
    INSTRUMENT_ROW_NEW = {
        'xpath': [
            "//div[@class='instrument-row instrument']",
            "//div[contains(@class, 'instrument-row') and @data-instrument-id]"
        ],
        'css': [
            ".instrument-row.instrument",
            "div[data-instrument-id].instrument-row"
        ]
    }
    
    INSTRUMENT_NAME_NEW = {
        'xpath': [
            ".//div[@class='name']//strong",
            ".//div[contains(@class, 'name')]//strong"
        ],
        'css': [
            ".name strong",
            "div.name strong"
        ]
    }
    
    INSTRUMENT_CHANGE_PCT = {
        'xpath': [
            ".//div[@class='change']//span",
            ".//div[contains(@class, 'change')]//span"
        ],
        'css': [
            ".change span",
            "div.change span"
        ]
    }
    
    INSTRUMENT_SELL_PRICE = {
        'xpath': [
            ".//div[@class='sell' and @data-no-trading]",
            ".//div[contains(@class, 'sell')]"
        ],
        'css': [
            ".sell[data-no-trading]",
            ".sell"
        ]
    }
    
    INSTRUMENT_BUY_PRICE = {
        'xpath': [
            ".//div[@class='buy' and @data-no-trading]",
            ".//div[contains(@class, 'buy')]"
        ],
        'css': [
            ".buy[data-no-trading]",
            ".buy"
        ]
    }
    
    INSTRUMENT_HIGH_LOW = {
        'xpath': [
            ".//div[@class='high-low']//span",
            ".//div[contains(@class, 'high-low')]//span"
        ],
        'css': [
            ".high-low span",
            "div.high-low span"
        ]
    }
    
    TRADING_BUTTONS = {
        'xpath': [
            ".//button[@class='buySellButton']",
            ".//button[contains(@class, 'buySellButton')]"
        ],
        'css': [
            ".buySellButton",
            "button.buySellButton"
        ]
    }
    
    # Category URL Mappings
    CATEGORY_URL_MAP = {
        "All Popular": "/all-popular",
        "Micro": "/micro", 
        "Agriculture": "/agriculture",
        "Crypto": "/crypto",
        "Equity Indices": "/equity-indices",
        "Forex": "/forex",
        "Interest Rates": "/interest-rates",
        "Metals": "/metals",
        "Energy": "/energy"
    }

    @classmethod
    def get_all_selectors_for_element(cls, element_name: str) -> Dict[str, List[str]]:
        """Get all selector strategies for a specific element"""
        return getattr(cls, element_name, {})
    
    # Order editing functionality
    EDIT_ORDER_PRICE_INPUT = {
        'xpath': [
            "//input[contains(@name, 'price') or contains(@placeholder, 'Price')]",
            "//input[contains(@class, 'price-input') or contains(@id, 'price')]",
            "//div[contains(@class, 'edit-order')]//input[@type='text' or @type='number']"
        ],
        'css': [
            "input[name*='price']",
            ".price-input",
            "#order-price",
            ".edit-order input[type='text']",
            ".edit-order input[type='number']"
        ]
    }
    
    SAVE_ORDER_CHANGES = {
        'xpath': [
            "//button[contains(text(), 'Save') or contains(text(), 'Update')]",
            "//button[contains(@class, 'save') or contains(@class, 'update')]",
            "//button[contains(@data-action, 'save') or contains(@data-action, 'update')]"
        ],
        'css': [
            ".save-btn",
            ".update-order",
            "button[data-action='save']",
            "button[data-action='update']",
            ".edit-dialog .confirm-btn"
        ]
    }
    
    ORDERS_TABLE = {
        'xpath': [
            "//table[contains(@class, 'orders') or contains(@class, 'pending')]",
            "//div[contains(@class, 'orders-list') or contains(@class, 'orders-table')]",
            "//table//tr[contains(., 'Take Profit') or contains(., 'Limit')]/ancestor::table"
        ],
        'css': [
            ".orders-table",
            ".pending-orders",
            "table.orders",
            ".orders-list table",
            "[data-test='orders-table']"
        ]
    }
    
    ORDERS_SECTION = {
        'xpath': [
            "//div[contains(@class, 'orders') or contains(text(), 'Orders')]",
            "//section[contains(@class, 'orders') or contains(@id, 'orders')]",
            "//nav//a[contains(text(), 'Orders') or contains(text(), 'Pending')]"
        ],
        'css': [
            ".orders-section",
            "#orders",
            "nav a[href*='order']",
            ".sidebar .orders"
        ]
    }
    
    POSITIONS_SECTION = {
        'xpath': [
            "//div[contains(@class, 'positions') or contains(text(), 'Positions')]",
            "//section[contains(@class, 'positions') or contains(@id, 'positions')]",
            "//nav//a[contains(text(), 'Positions') or contains(text(), 'Open Trades')]",
            "//a[contains(@href, 'position') or contains(@href, 'trade')]"
        ],
        'css': [
            ".positions-section",
            "#positions",
            "nav a[href*='position']",
            ".sidebar .positions",
            "a[href*='trade']"
        ]
    }

    # RECAPTCHA and anti-bot detection - Updated for actual Plus500 HTML structure
    RECAPTCHA = {
        'xpath': [
            # Primary Plus500 RECAPTCHA container (highest priority)
            "//div[@id='login-recaptcha']",
            "//div[contains(@class, 'login-captcha')]",
            # iframe-based detection for active RECAPTCHA
            "//div[@id='login-recaptcha']//iframe[@title='reCAPTCHA']",
            "//iframe[@title='reCAPTCHA' and contains(@src, 'recaptcha/api2/anchor')]",
            "//div[contains(@class, 'login-captcha')]//iframe[contains(@src, 'recaptcha')]",
            # Generic RECAPTCHA patterns (lower priority)
            "//div[contains(@class, 'recaptcha') or contains(@class, 'captcha')]",
            "//div[contains(@class, 'g-recaptcha')]",
            "//iframe[contains(@src, 'recaptcha')]",
            "//iframe[contains(@title, 'reCAPTCHA')]",
            "//div[contains(@class, 'hcaptcha')]",
            "//iframe[contains(@src, 'hcaptcha')]",
            "//div[contains(@id, 'captcha')]",
            "//div[contains(@data-sitekey, '')]",
            "//div[@class='captcha-container']",
            "//div[contains(text(), 'verify') or contains(text(), 'robot')]"
        ],
        'css': [
            # Primary Plus500 selectors (highest priority)
            "#login-recaptcha",
            ".login-captcha",
            "#login-recaptcha iframe[title='reCAPTCHA']",
            "iframe[title='reCAPTCHA'][src*='recaptcha/api2/anchor']",
            ".login-captcha iframe[src*='recaptcha']",
            # Generic RECAPTCHA selectors (lower priority)
            ".recaptcha",
            ".g-recaptcha",
            ".captcha",
            ".hcaptcha",
            "iframe[src*='recaptcha']",
            "iframe[title*='reCAPTCHA']",
            "iframe[src*='hcaptcha']",
            "#captcha",
            "[data-sitekey]",
            ".captcha-container",
            ".challenge-container"
        ]
    }
    
    RECAPTCHA_CHECKBOX = {
        'xpath': [
            "//div[contains(@class, 'recaptcha-checkbox')]",
            "//span[contains(@class, 'recaptcha-checkbox')]",
            "//div[@role='checkbox']",
            "//span[@role='checkbox']"
        ],
        'css': [
            ".recaptcha-checkbox",
            "[role='checkbox']",
            ".rc-anchor-checkbox"
        ]
    }
    
    RECAPTCHA_CHALLENGE = {
        'xpath': [
            "//div[contains(@class, 'recaptcha-challenge')]",
            "//div[contains(@class, 'rc-challenge')]",
            "//iframe[contains(@title, 'challenge')]"
        ],
        'css': [
            ".recaptcha-challenge",
            ".rc-challenge",
            "iframe[title*='challenge']"
        ]
    }

    @classmethod
    def get_category_url(cls, category_name: str) -> Optional[str]:
        """Get URL path for category navigation"""
        return cls.CATEGORY_URL_MAP.get(category_name)