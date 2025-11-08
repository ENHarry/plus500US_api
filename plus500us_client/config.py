"""
Configuration module for the Plus500US API client.
Re-exports the Config class for backward compatibility.
"""

from .requests.config import Config, load_config

__all__ = ['Config', 'load_config']