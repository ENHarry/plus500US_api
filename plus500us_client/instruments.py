"""
Instruments client for the Plus500US API client.
Re-exports the InstrumentsClient for backward compatibility.
"""

from .requests.instruments import InstrumentsClient

__all__ = ['InstrumentsClient']