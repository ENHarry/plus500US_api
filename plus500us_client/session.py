"""
Session management for the Plus500US API client.
Re-exports the SessionManager for backward compatibility.
"""

from .requests.session import SessionManager

__all__ = ['SessionManager']