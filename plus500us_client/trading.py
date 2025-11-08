"""
Trading client for the Plus500US API client.
Re-exports the TradingClient for backward compatibility.
"""

from .requests.trading import TradingClient

__all__ = ['TradingClient']