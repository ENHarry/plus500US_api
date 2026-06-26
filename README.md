# plus500us-client

> **Unofficial** Python SDK for Plus500 Futures / **T4 API**.
>
> ⚠️ This is not an official Plus500 or CTS product. You must complete any
> Plus500/T4 certification and obtain API credentials from Plus500 before
> connecting to a live account.

## What's new in v2

Version 2 replaces the previous REST/WebDriver scraping layer with a proper
**T4 API** client that communicates over **WebSocket Secure (WSS)** using
**Google Protocol Buffers** — exactly as documented at
[docs.t4login.com](https://docs.t4login.com/doku.php?id=developers:api).

The old `plus500us_client.requests.*` modules are preserved for backward
compatibility but should be considered legacy.

---

## Features

- **WebSocket + Protobuf** transport matching the T4 API specification
- API-key **and** username/password authentication
- Automatic **heartbeat** every 20 seconds (T4 requirement)
- **Automatic reconnect**, re-authentication, and re-subscription
- **Market depth** (Level 2, up to 10 levels) subscriptions
- **Market-by-order** (MBO) subscriptions
- **Account feed**: balance, positions, P&L, order updates
- **Order routing**: submit, revise, cancel with local pre-flight validation
- **Dry-run mode**: build and inspect messages without sending
- **Simulator-first**: defaults to `wss://wss-sim.t4login.com/v1`; live requires explicit opt-in
- Safe **Decimal** price handling – no float rounding
- Thread-safe – asyncio loop runs in a background thread

---

## Installation

```bash
pip install "plus500us-client @ git+https://github.com/ENHarry/plus500US_api.git"
```

Or clone and install in development mode:

```bash
git clone https://github.com/ENHarry/plus500US_api.git
cd plus500US_api
pip install -e ".[dev]"
```

### Regenerate protobuf bindings

The generated `*_pb2.py` files are included in the repo. If you change the
`.proto` files under `proto/`, regenerate with:

```bash
python -m grpc_tools.protoc \
  --proto_path=proto \
  --python_out=plus500us_client/t4/proto \
  proto/t4/v1/common/price.proto \
  proto/t4/v1/common/enums.proto \
  proto/t4/v1/auth/auth.proto \
  proto/t4/v1/market/market.proto \
  proto/t4/v1/account/account.proto \
  proto/t4/v1/orderrouting/orderrouting.proto \
  proto/t4/v1/service.proto
```

---

## Configuration

Copy `.env.example` to `.env` and fill in your credentials:

```env
PLUS500_T4_ENV=sim                        # sim (default) or live
PLUS500_T4_API_KEY=your-api-key-here      # OR use firm/username/password below
PLUS500_T4_FIRM=
PLUS500_T4_USERNAME=
PLUS500_T4_PASSWORD=
PLUS500_T4_APP_NAME=
PLUS500_T4_APP_LICENSE=
PLUS500_T4_ACCOUNT_ID=
PLUS500_T4_DEFAULT_MARKET_ID=
PLUS500_T4_LIVE_TRADING_ENABLED=false     # must be "true" for live orders
PLUS500_T4_DRY_RUN=false
PLUS500_T4_LOG_LEVEL=INFO
```

---

## Quick Start

```python
import time
from decimal import Decimal
from plus500us_client.t4 import T4Client, T4Config

cfg = T4Config()  # reads env vars; defaults to simulator

with T4Client(cfg) as client:
    client.connect(timeout=30)
    print(f"Connected: user={client.user_id}")

    # Market depth
    client.subscribe_depth(
        exchange_id="CME", contract_id="ES", market_id="ESZ25",
        on_depth=lambda d: print(f"bid={d.best_bid} ask={d.best_ask}"),
    )

    # Account
    client.subscribe_account(account_ids=["YOUR_ACCOUNT_ID"])
    client.wait_account_ready(timeout=15)

    # Limit order (dry-run unless PLUS500_T4_DRY_RUN=false)
    result = client.submit_order(
        account_id="YOUR_ACCOUNT_ID",
        market_id="ESZ25",
        buy_sell="BUY",
        price_type="PRICE_TYPE_LIMIT",
        time_type="TIME_TYPE_DAY",
        volume=1,
        limit_price=Decimal("5500.00"),
    )
    print(result)

    time.sleep(10)
```

See `examples/t4_simulator_quickstart.py` for a full example and
`examples/t4_dry_run.py` for offline message inspection.

---

## Safety Controls

| Control | Default | How to override |
|---------|---------|-----------------|
| Environment | Simulator | Set `PLUS500_T4_ENV=live` |
| Live trading | Disabled | Set `PLUS500_T4_LIVE_TRADING_ENABLED=true` |
| Dry run | Off | Set `PLUS500_T4_DRY_RUN=true` |
| Credential logging | Never | Hard-coded; never logs API keys/passwords/session IDs |

---

## Testing

```bash
pytest tests/t4/ -v
```

Tests cover config validation, protobuf encode/decode, order validation,
account feed dispatch, and market data dispatch. No real credentials or
network access required.

---

## Migration from v1

The v1 SDK used HTTP REST endpoints (`/ClientRequest/...`) via the
`plus500us_client.requests.*` modules. These endpoints were scraped/reverse-
engineered and may stop working at any time.

The T4 API is the official, documented API. Migrate by:

1. Creating a `T4Config` and `T4Client` instead of `Config` and `SessionManager`.
2. Using `client.subscribe_depth()` instead of `MarketDataClient.get_quote()`.
3. Using `client.submit_order()` instead of `TradingClient.place_order()`.

The legacy `requests` modules remain importable but are no longer maintained.

---

## Known Limitations

- **Certification**: Plus500/CTS may require API certification before granting
  live trading access. Contact [api@t4login.com](mailto:api@t4login.com).
- **Spread / UDS**: `CreateUDS` message is implemented in the protobuf layer
  but not exposed via high-level helpers. Use `client._transport.send(raw)`.
- **MBO callbacks**: MBO snapshot and update messages are routed to registered
  callbacks but not parsed into typed Python objects (raw protobuf).
- **Auth tokens**: `AuthenticationTokenRequest` is defined in the proto layer
  but not yet exposed via the high-level client.

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/t4/ -v
python -m build
```

## License

MIT – see `LICENSE`.

## Disclaimer

This is an **unofficial, community SDK**. It is not affiliated with,
endorsed by, or supported by Plus500 Ltd or CTS Futures. Use at your own risk.
Always test thoroughly in the simulator before attempting live trading.
