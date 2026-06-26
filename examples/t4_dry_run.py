"""T4 Dry-Run Example.

Shows how to use dry-run mode to build and inspect order messages
without connecting to any server.  Useful for integration testing.

Run:
    python examples/t4_dry_run.py
"""
from __future__ import annotations

from decimal import Decimal

from plus500us_client.t4.config import T4Config
from plus500us_client.t4.codec import (
    build_order_submit,
    build_order_revise,
    build_order_pull,
    price_to_decimal,
)
from plus500us_client.t4.proto.t4.v1 import service_pb2


def inspect_message(label: str, raw: bytes) -> None:
    msg = service_pb2.ClientMessage()
    msg.ParseFromString(raw)
    field = msg.WhichOneof("payload")
    print(f"\n--- {label} ---")
    print(f"  Payload type : {field}")
    if field == "order_submit":
        sub = msg.order_submit
        print(f"  account_id   : {sub.account_id}")
        print(f"  market_id    : {sub.market_id}")
        for i, o in enumerate(sub.orders):
            print(f"  order[{i}]     : side={o.buy_sell} vol={o.volume} "
                  f"limit={price_to_decimal(o.limit_price)}")
    elif field == "order_revise":
        rev = msg.order_revise
        for r in rev.revisions:
            print(f"  revise unique_id={r.unique_id} vol={r.volume}")
    elif field == "order_pull":
        pull = msg.order_pull
        for p in pull.pulls:
            print(f"  pull unique_id={p.unique_id}")
    print(f"  Encoded size : {len(raw)} bytes")


def main():
    print("T4 Dry-Run Example")
    print("==================")
    print("Building protobuf messages without connecting to any server.\n")

    # Limit order
    limit_raw = build_order_submit(
        account_id="SIM-ACCOUNT-001",
        market_id="ESZ25",
        buy_sell="BUY",
        price_type="PRICE_TYPE_LIMIT",
        time_type="TIME_TYPE_DAY",
        volume=1,
        limit_price=Decimal("5500.00"),
        tag="dry-run-limit",
    )
    inspect_message("Limit Order (BUY 1 ESZ25 @ 5500.00)", limit_raw)

    # Market order
    market_raw = build_order_submit(
        account_id="SIM-ACCOUNT-001",
        market_id="ESZ25",
        buy_sell="SELL",
        price_type="PRICE_TYPE_MARKET",
        time_type="TIME_TYPE_DAY",
        volume=2,
        tag="dry-run-market",
    )
    inspect_message("Market Order (SELL 2 ESZ25)", market_raw)

    # Revise order
    revise_raw = build_order_revise(
        unique_id="ORDER-ID-12345",
        account_id="SIM-ACCOUNT-001",
        market_id="ESZ25",
        user_id="USER-001",
        volume=3,
        limit_price=Decimal("5510.25"),
    )
    inspect_message("Revise Order (change vol=3, limit=5510.25)", revise_raw)

    # Cancel order
    pull_raw = build_order_pull(
        unique_id="ORDER-ID-12345",
        account_id="SIM-ACCOUNT-001",
        market_id="ESZ25",
        user_id="USER-001",
    )
    inspect_message("Pull/Cancel Order", pull_raw)

    print("\nAll messages built successfully – no network calls made.")


if __name__ == "__main__":
    main()
