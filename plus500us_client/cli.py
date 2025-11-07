\
from __future__ import annotations
import argparse, sys
from .requests.config import load_config
from .requests.session import SessionManager
from .requests.auth import AuthClient
from .requests.errors import CaptchaRequiredError, ValidationError
from .requests.instruments import InstrumentsClient
from .requests.marketdata import MarketDataClient
from .requests.account import AccountClient
from .requests.trading import TradingClient
from .requests.risk_management import RiskManagementService
from .requests.models import OrderDraft
from decimal import Decimal

def main():
    parser = argparse.ArgumentParser(prog="plus5", description="Unofficial Plus500US client (demo)")
    sub = parser.add_subparsers(dest="cmd")

    p_login = sub.add_parser("login")
    p_login.add_argument("--interactive", action="store_true", help="Use browser handoff to import cookies if captcha blocks programmatic login")
    p_login.add_argument("--email")
    p_login.add_argument("--password")
    p_login.add_argument("--totp")
    p_login.add_argument("--account-type", choices=["demo", "live"], help="Account type to use (demo or live)")
    p_login.add_argument("--method", choices=["webdriver", "requests", "auto"], default="auto", 
                        help="Authentication method (default: auto)")
    p_login.add_argument("--browser-auth", action="store_true", 
                        help="Use browser-based authentication (same as --method webdriver)")
    p_login.add_argument("--headless", action="store_true", 
                        help="Run browser in headless mode (for webdriver method)")

    sub.add_parser("whoami")

    p_ins = sub.add_parser("instruments")
    p_ins.add_argument("--market", default=None)

    p_q = sub.add_parser("quote")
    p_q.add_argument("--id", required=True)

    # Trading commands
    p_trade = sub.add_parser("trade", help="Place trading orders")
    trade_sub = p_trade.add_subparsers(dest="trade_cmd")
    
    # Market order
    p_market = trade_sub.add_parser("market", help="Place market order")
    p_market.add_argument("--instrument", required=True, help="Instrument ID")
    p_market.add_argument("--side", choices=["BUY", "SELL"], required=True, help="Order side")
    p_market.add_argument("--qty", type=float, required=True, help="Quantity")
    p_market.add_argument("--sl", type=float, help="Stop loss price")
    p_market.add_argument("--tp", type=float, help="Take profit price")
    
    # Limit order
    p_limit = trade_sub.add_parser("limit", help="Place limit order")
    p_limit.add_argument("--instrument", required=True, help="Instrument ID")
    p_limit.add_argument("--side", choices=["BUY", "SELL"], required=True, help="Order side")
    p_limit.add_argument("--qty", type=float, required=True, help="Quantity")
    p_limit.add_argument("--price", type=float, required=True, help="Limit price")
    p_limit.add_argument("--sl", type=float, help="Stop loss price")
    p_limit.add_argument("--tp", type=float, help="Take profit price")
    
    # Stop order
    p_stop = trade_sub.add_parser("stop", help="Place stop order")
    p_stop.add_argument("--instrument", required=True, help="Instrument ID")
    p_stop.add_argument("--side", choices=["BUY", "SELL"], required=True, help="Order side")
    p_stop.add_argument("--qty", type=float, required=True, help="Quantity")
    p_stop.add_argument("--stop-price", type=float, required=True, help="Stop trigger price")
    
    # Positions and orders
    sub.add_parser("positions", help="List all positions")
    sub.add_parser("orders", help="List all orders")
    
    # Risk management
    p_risk = sub.add_parser("risk", help="Risk management commands")
    risk_sub = p_risk.add_subparsers(dest="risk_cmd")
    
    p_partial_tp = risk_sub.add_parser("partial-tp", help="Execute partial take profit")
    p_partial_tp.add_argument("--position-id", required=True, help="Position ID")
    p_partial_tp.add_argument("--qty", type=float, required=True, help="Partial quantity to close")
    p_partial_tp.add_argument("--price", type=float, required=True, help="Take profit price")

    args = parser.parse_args()
    cfg = load_config()
    sm = SessionManager(cfg)
    auth = AuthClient(cfg, sm)

    if args.cmd == "login":
        # Determine authentication method
        auth_method = args.method
        if args.browser_auth:
            auth_method = "webdriver"
        
        try:
            if auth_method == "webdriver" or (auth_method == "auto" and args.interactive):
                # Use WebDriver authentication
                from .webdriver import WebDriverAuthHandler
                from .hybrid import SessionBridge
                
                # Configure WebDriver
                webdriver_config = cfg.webdriver_config.copy()
                if args.headless:
                    webdriver_config["headless"] = True
                
                # Perform WebDriver authentication
                with WebDriverAuthHandler(cfg, webdriver_config) as webdriver_auth:
                    print("🌐 Starting browser-based authentication...")
                    session_data = webdriver_auth.manual_login_flow(
                        account_type=getattr(args, 'account_type', None)
                    )
                    
                    # Transfer session to requests
                    session_bridge = SessionBridge()
                    requests_session = session_bridge.transfer_webdriver_to_requests(session_data, sm.session)
                    
                    # Validate session transfer
                    validation = session_bridge.validate_session_transfer(
                        requests_session, 
                        f"{cfg.base_url}/dashboard"
                    )
                    
                    if validation.get('authenticated'):
                        print("✓ Browser authentication successful")
                        print(f"  Account Type: {session_data.get('account_type', 'Unknown')}")
                        print(f"  Cookies Transferred: {len(session_data.get('cookies', []))}")
                        
                        # Backup session data
                        backup_file = session_bridge.backup_session_data(session_data)
                        print(f"  Session Backup: {backup_file}")
                        
                    else:
                        print("⚠ Warning: Session transfer validation failed")
                        
            else:
                # Use traditional requests-based authentication
                login_info = auth.login(
                    email=args.email, 
                    password=args.password, 
                    totp_code=args.totp, 
                    account_type=getattr(args, 'account_type', None),
                    interactive_mode=args.interactive
                )
                print("✓ Logged in successfully")
                
                # Display post-login summary if available
                if "post_login_data" in login_info:
                    data = login_info["post_login_data"]
                    if data.get("account"):
                        account = data["account"]
                        print(f"  Account Type: {account.account_type}")
                        print(f"  Balance: ${account.balance:,.2f}")
                        print(f"  Available: ${account.available:,.2f}")
                    if data.get("instruments"):
                        print(f"  Available Instruments: {len(data['instruments'])}")
                else:
                    print("  (Run with --browser-auth for enhanced features)")
                
        except CaptchaRequiredError as e:
            if args.interactive or auth_method in ["webdriver", "auto"]:
                print("🔒 Captcha detected - switching to browser authentication...")
                print("Tip: Use --browser-auth for direct browser authentication")
            else:
                print("[error]", e)
                print("Tip: re-run with: plus5 login --browser-auth")
                sys.exit(2)
        except Exception as e:
            print(f"❌ Login failed: {e}")
            sys.exit(1)
        return

    if args.cmd == "whoami":
        acct = AccountClient(cfg, sm).get_account()
        print(acct.model_dump_json(indent=2))
        return

    if args.cmd == "instruments":
        ins = InstrumentsClient(cfg, sm).list_instruments(market=args.market)
        print(f"Found {len(ins)} instruments")
        return

    if args.cmd == "quote":
        q = MarketDataClient(cfg, sm).get_quote(args.id)
        print(q.model_dump_json(indent=2))
        return

    # Trading commands
    if args.cmd == "trade":
        trading_client = TradingClient(cfg, sm)
        
        if args.trade_cmd == "market":
            draft = OrderDraft(
                instrument_id=args.instrument,
                side=args.side,  # type: ignore
                order_type="MARKET",
                qty=Decimal(str(args.qty))
            )
            
            if args.sl or args.tp:
                sl_price = Decimal(str(args.sl)) if args.sl else None
                tp_price = Decimal(str(args.tp)) if args.tp else None
                bracket = trading_client.place_bracket_order(draft, sl_price, tp_price)
                print(f"✓ Bracket order placed: {bracket.parent_order_id}")
                if bracket.stop_loss_order_id:
                    print(f"  Stop Loss: {bracket.stop_loss_order_id}")
                if bracket.take_profit_order_id:
                    print(f"  Take Profit: {bracket.take_profit_order_id}")
            else:
                order = trading_client.place_order(draft)
                print(f"✓ Market order placed: {order.id}")
                
        elif args.trade_cmd == "limit":
            draft = OrderDraft(
                instrument_id=args.instrument,
                side=args.side,  # type: ignore
                order_type="LIMIT",
                qty=Decimal(str(args.qty)),
                limit_price=Decimal(str(args.price))
            )
            
            if args.sl or args.tp:
                sl_price = Decimal(str(args.sl)) if args.sl else None
                tp_price = Decimal(str(args.tp)) if args.tp else None
                bracket = trading_client.place_bracket_order(draft, sl_price, tp_price)
                print(f"✓ Bracket limit order placed: {bracket.parent_order_id}")
            else:
                order = trading_client.place_order(draft)
                print(f"✓ Limit order placed: {order.id}")
                
        elif args.trade_cmd == "stop":
            draft = OrderDraft(
                instrument_id=args.instrument,
                side=args.side,  # type: ignore
                order_type="STOP",
                qty=Decimal(str(args.qty)),
                stop_price=Decimal(str(args.stop_price))
            )
            order = trading_client.place_order(draft)
            print(f"✓ Stop order placed: {order.id}")
        return

    if args.cmd == "positions":
        trading_client = TradingClient(cfg, sm)
        positions = trading_client.get_positions()
        if positions:
            print(f"Found {len(positions)} open positions:")
            for pos in positions:
                pnl_str = f"P&L: ${pos.unrealized_pnl:,.2f}" if pos.unrealized_pnl else "P&L: N/A"
                print(f"  {pos.id}: {pos.side} {pos.qty} {pos.instrument_id} @ ${pos.avg_price} ({pnl_str})")
        else:
            print("No open positions")
        return

    if args.cmd == "orders":
        trading_client = TradingClient(cfg, sm)
        orders = trading_client.get_orders()
        if orders:
            print(f"Found {len(orders)} orders:")
            for order in orders:
                print(f"  {order.id}: {order.status} - Created: {order.create_time}")
        else:
            print("No orders found")
        return

    # Risk management commands
    if args.cmd == "risk":
        trading_client = TradingClient(cfg, sm)
        risk_service = RiskManagementService(cfg, sm, trading_client)
        
        if args.risk_cmd == "partial-tp":
            try:
                # Validate first
                validation = risk_service.validate_partial_take_profit(
                    args.position_id, 
                    Decimal(str(args.qty))
                )
                
                if not validation.is_valid:
                    print("❌ Partial take profit validation failed:")
                    for error in validation.validation_errors:
                        print(f"  • {error}")
                    sys.exit(1)
                
                # Execute if valid
                success = risk_service.execute_partial_take_profit(
                    args.position_id,
                    Decimal(str(args.qty)),
                    Decimal(str(args.price))
                )
                
                if success:
                    print(f"✓ Partial take profit executed successfully")
                    print(f"  Position: {args.position_id}")
                    print(f"  Quantity: {args.qty} contracts")
                    print(f"  Price: ${args.price}")
                    print(f"  Remaining: {validation.remaining_qty_after} contracts")
                
            except ValidationError as e:
                print(f"❌ Error: {e}")
                sys.exit(1)
        return

if __name__ == "__main__":
    main()
