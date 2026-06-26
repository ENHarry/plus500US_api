"""T4 API Simulator Quickstart Example.

Demonstrates:
 1. Connecting to the T4 simulator
 2. Authenticating with API key or username/password
 3. Subscribing to market depth (Level 2)
 4. Subscribing to account updates
 5. Submitting a limit order (dry-run by default)
 6. Revising and cancelling the order
 7. Clean shutdown

SETUP
-----
Copy .env.example to .env and fill in your T4 simulator credentials:

    PLUS500_T4_ENV=sim
    PLUS500_T4_API_KEY=your-api-key-here
    PLUS500_T4_ACCOUNT_ID=your-account-id
    PLUS500_T4_DRY_RUN=true     # set to false to actually submit orders

Then run:
    python examples/t4_simulator_quickstart.py

WARNING: This is an unofficial SDK. You must complete any Plus500/T4
         certification requirements before trading on a live account.
"""
from __future__ import annotations

import os
import time
import signal
from decimal import Decimal

# Load .env from project root
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from plus500us_client.t4 import T4Client, T4Config


def on_depth_update(depth):
    print(
        f"[DEPTH] {depth.market_id}: "
        f"bid={depth.best_bid} ask={depth.best_ask} "
        f"vol={depth.total_volume}"
    )


def on_trade(trade):
    print(f"[TRADE] {trade.market_id}: price={trade.price} vol={trade.volume}")


def on_account_update(state):
    print(
        f"[ACCOUNT] {state.account_id}: "
        f"balance={state.balance} margin={state.margin} rpl={state.rpl}"
    )


def on_order_update(server_msg):
    field = server_msg.WhichOneof("payload")
    print(f"[ORDER] {field}")


def main():
    cfg = T4Config()
    print(f"Config: {cfg}")
    print(f"Environment: {'SIMULATOR' if cfg.is_sim else 'LIVE'}")
    print(f"Dry-run: {cfg.dry_run}")

    account_id = cfg.account_id or os.getenv("PLUS500_T4_ACCOUNT_ID", "")
    market_id = cfg.default_market_id or "ESZ25"   # E-mini S&P 500 Dec 2025
    exchange_id = "CME"
    contract_id = "ES"

    if not account_id:
        print("WARNING: PLUS500_T4_ACCOUNT_ID not set. "
              "Account subscription and order routing will fail.")

    with T4Client(cfg) as client:
        # 1. Connect & authenticate
        print("Connecting…")
        client.connect(timeout=30)
        print(f"Connected! user_id={client.user_id} firm_id={client.firm_id}")

        # 2. Subscribe to market depth
        client.subscribe_depth(
            exchange_id=exchange_id,
            contract_id=contract_id,
            market_id=market_id,
            on_depth=on_depth_update,
            on_trade=on_trade,
            depth_levels=10,
        )
        print(f"Subscribed to depth: {market_id}")

        # 3. Subscribe to account
        if account_id:
            client.subscribe_account(
                account_ids=[account_id],
                on_update=on_account_update,
                on_order_update=on_order_update,
            )
            ready = client.wait_account_ready(timeout=15)
            if ready:
                print(f"Account ready: {account_id}")
            else:
                print("Account subscription timed out")

        # 4. Stream data for a few seconds
        print("Streaming for 10 seconds…")
        time.sleep(10)

        # 5. Submit a limit order (dry-run or real depending on config)
        if account_id and client.account_feed.is_ready:
            user_id = client.user_id or ""
            print(f"\nSubmitting limit order (dry_run={cfg.dry_run})…")
            result = client.submit_order(
                account_id=account_id,
                market_id=market_id,
                buy_sell="BUY",
                price_type="PRICE_TYPE_LIMIT",
                time_type="TIME_TYPE_DAY",
                volume=1,
                limit_price=Decimal("5000.00"),
                tag="quickstart-example",
                user_id=user_id,
            )
            print(f"Submit result: {result}")

            if result.submitted and not cfg.dry_run:
                # Allow a moment for order update to arrive
                time.sleep(2)
                print("Order submitted; check [ORDER] log lines above for updates.")

        print("\nShutting down…")
    print("Done.")


if __name__ == "__main__":
    main()
