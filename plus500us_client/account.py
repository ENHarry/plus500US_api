"""
Account client for the Plus500US API client.
Re-exports the AccountClient for backward compatibility.
"""

from .requests.account import AccountClient

__all__ = ['AccountClient']