"""T4 WebSocket transport: connection, authentication, heartbeat, reconnect.

Architecture
------------
``T4Transport`` runs an asyncio event loop in a background thread.
Callers interact via:
 - ``on_message``  – callback invoked with each decoded ServerMessage
 - ``on_connected`` / ``on_disconnected`` – lifecycle hooks
 - ``send(bytes)`` – thread-safe message submission
 - ``close()``     – clean shutdown

Heartbeat
---------
The T4 server requires a heartbeat every 20 seconds.  The transport
sends heartbeats on a fixed timer and tracks when the *server* last
sent any message.  If three consecutive 20-second windows pass with no
server message the connection is considered dead and a reconnect starts.
"""
from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Callable, Optional

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError as exc:
    raise ImportError(
        "websockets is required for the T4 transport layer. "
        "Install it with: pip install 'websockets>=12'"
    ) from exc

from .codec import (
    build_heartbeat,
    build_login_request,
    decode_server_message,
)
from .config import (
    HEARTBEAT_INTERVAL_SECONDS,
    HEARTBEAT_TIMEOUT_CYCLES,
    T4Config,
)
from .errors import T4AuthError, T4ConnectionError, T4NotReadyError

logger = logging.getLogger(__name__)


MessageCallback = Callable[["object"], None]  # ServerMessage


class T4Transport:
    """Thread-safe T4 WebSocket transport.

    Usage::

        def on_msg(server_msg):
            ...

        transport = T4Transport(config, on_message=on_msg)
        transport.start()          # connects, authenticates, starts heartbeat
        transport.send(raw_bytes)  # enqueue outbound bytes from any thread
        transport.close()          # graceful shutdown
    """

    def __init__(
        self,
        config: T4Config,
        on_message: Optional[MessageCallback] = None,
        on_connected: Optional[Callable[[], None]] = None,
        on_disconnected: Optional[Callable[[Exception | None], None]] = None,
        on_authenticated: Optional[Callable[["object"], None]] = None,
    ) -> None:
        self._cfg = config
        self._on_message = on_message
        self._on_connected = on_connected
        self._on_disconnected = on_disconnected
        self._on_authenticated = on_authenticated

        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None
        self._ws = None  # websockets connection handle
        self._send_queue: asyncio.Queue | None = None

        self._authenticated = threading.Event()
        self._stopped = threading.Event()
        self._last_server_msg_ts: float = 0.0
        self._login_response = None  # holds the last LoginResponse

        # Re-subscription registry: list of raw bytes to re-send after reconnect
        self._resubscribe_payloads: list[bytes] = []
        self._resubscribe_lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def start(self, timeout: float = 30.0) -> None:
        """Start the transport in a background thread.

        Blocks until authenticated or *timeout* seconds elapse.
        Raises ``T4ConnectionError`` or ``T4AuthError`` on failure.
        """
        if self._thread and self._thread.is_alive():
            raise RuntimeError("Transport already running")
        self._stopped.clear()
        self._authenticated.clear()
        self._loop = asyncio.new_event_loop()
        self._thread = threading.Thread(
            target=self._run_loop, daemon=True, name="T4Transport"
        )
        self._thread.start()
        if not self._authenticated.wait(timeout=timeout):
            self._stopped.set()
            raise T4ConnectionError(
                f"T4 transport did not authenticate within {timeout}s"
            )

    def send(self, data: bytes) -> None:
        """Enqueue *data* to be written on the WebSocket (thread-safe)."""
        if self._loop is None or self._send_queue is None:
            raise T4NotReadyError("Transport is not running")
        self._loop.call_soon_threadsafe(self._send_queue.put_nowait, data)

    def register_resubscribe(self, payload: bytes) -> None:
        """Register *payload* to be re-sent after every reconnect."""
        with self._resubscribe_lock:
            if payload not in self._resubscribe_payloads:
                self._resubscribe_payloads.append(payload)

    def unregister_resubscribe(self, payload: bytes) -> None:
        """Remove a previously registered re-subscribe payload."""
        with self._resubscribe_lock:
            try:
                self._resubscribe_payloads.remove(payload)
            except ValueError:
                pass

    def close(self) -> None:
        """Shut down the transport gracefully."""
        self._stopped.set()
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)
        if self._thread:
            self._thread.join(timeout=10)

    @property
    def is_authenticated(self) -> bool:
        return self._authenticated.is_set()

    @property
    def login_response(self):
        return self._login_response

    # ------------------------------------------------------------------
    # Internal asyncio loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._connect_loop())
        finally:
            self._loop.close()

    async def _connect_loop(self) -> None:
        attempt = 0
        while not self._stopped.is_set():
            delay = min(
                self._cfg.reconnect_base_delay * (2 ** attempt),
                self._cfg.reconnect_max_delay,
            )
            if attempt > 0:
                logger.info("Reconnecting in %.1fs (attempt %d)", delay, attempt + 1)
                await asyncio.sleep(delay)

            if attempt >= self._cfg.reconnect_max_attempts:
                logger.error("Max reconnect attempts reached; giving up")
                break

            try:
                await self._connect_once()
                attempt = 0  # reset on clean disconnect
            except T4AuthError:
                logger.exception("Authentication error – not reconnecting")
                break
            except Exception as exc:
                logger.warning("Connection lost: %s", exc)
                attempt += 1
                self._authenticated.clear()
                if self._on_disconnected:
                    self._on_disconnected(exc)

    async def _connect_once(self) -> None:
        url = self._cfg.ws_url
        logger.info("Connecting to %s", url)

        self._send_queue = asyncio.Queue()

        async with websockets.connect(url, ssl=True, ping_interval=None) as ws:
            self._ws = ws
            logger.info("WebSocket connected; sending LoginRequest")

            if self._on_connected:
                self._on_connected()

            # Send login immediately
            login_bytes = self._build_login()
            await ws.send(login_bytes)

            # Run receiver, heartbeat, and sender concurrently
            await asyncio.gather(
                self._receiver(ws),
                self._heartbeat_sender(ws),
                self._queue_sender(ws),
            )

    def _build_login(self) -> bytes:
        return build_login_request(
            api_key=self._cfg.api_key,
            firm=self._cfg.firm,
            username=self._cfg.username,
            password=self._cfg.password,
            app_name=self._cfg.app_name,
            app_license=self._cfg.app_license,
        )

    async def _receiver(self, ws) -> None:
        async for raw in ws:
            if self._stopped.is_set():
                break
            self._last_server_msg_ts = time.monotonic()
            try:
                server_msg = decode_server_message(raw)
            except Exception:
                logger.exception("Failed to decode server message")
                continue

            field = server_msg.WhichOneof("payload")

            if field == "login_response":
                await self._handle_login_response(server_msg.login_response)
            elif field == "heartbeat":
                logger.debug("Server heartbeat received")
            else:
                if self._on_message:
                    try:
                        self._on_message(server_msg)
                    except Exception:
                        logger.exception("Error in on_message callback")

    async def _handle_login_response(self, lr) -> None:
        result_name = lr.result
        # Check by value; LoginResult.LOGIN_SUCCESS == 1
        try:
            from .proto.t4.v1.common import enums_pb2  # type: ignore
            success_val = enums_pb2.LoginResult.Value("LOGIN_SUCCESS")
        except Exception:
            success_val = 1

        if lr.result == success_val:
            logger.info(
                "Authenticated: user_id=%s firm_id=%s session_id=%s",
                lr.user_id,
                lr.firm_id,
                "***",  # never log session IDs
            )
            self._login_response = lr
            self._authenticated.set()
            if self._on_authenticated:
                self._on_authenticated(lr)
            # Re-send any registered subscriptions
            await self._resubscribe()
        else:
            # Map numeric to name if possible
            try:
                from .proto.t4.v1.common import enums_pb2  # type: ignore
                code = enums_pb2.LoginResult.Name(lr.result)
            except Exception:
                code = str(lr.result)
            raise T4AuthError(code, f"result={lr.result}")

    async def _resubscribe(self) -> None:
        with self._resubscribe_lock:
            payloads = list(self._resubscribe_payloads)
        for payload in payloads:
            try:
                await self._ws.send(payload)
                logger.debug("Re-subscribed (%d bytes)", len(payload))
            except Exception:
                logger.exception("Failed to re-subscribe")

    async def _heartbeat_sender(self, ws) -> None:
        missed = 0
        while not self._stopped.is_set():
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            if self._stopped.is_set():
                break
            # Check if server has gone silent
            elapsed = time.monotonic() - self._last_server_msg_ts
            if (
                self._last_server_msg_ts > 0
                and elapsed > HEARTBEAT_INTERVAL_SECONDS * HEARTBEAT_TIMEOUT_CYCLES
            ):
                missed += 1
                logger.warning(
                    "No server message for %.0fs (%d missed cycles)",
                    elapsed,
                    missed,
                )
                if missed >= HEARTBEAT_TIMEOUT_CYCLES:
                    logger.error("Server heartbeat timeout; closing connection")
                    await ws.close()
                    return
            else:
                missed = 0

            try:
                await ws.send(build_heartbeat())
                logger.debug("Heartbeat sent")
            except ConnectionClosed:
                return

    async def _queue_sender(self, ws) -> None:
        while not self._stopped.is_set():
            try:
                data = await asyncio.wait_for(
                    self._send_queue.get(), timeout=1.0
                )
            except asyncio.TimeoutError:
                continue
            try:
                await ws.send(data)
            except ConnectionClosed:
                return
