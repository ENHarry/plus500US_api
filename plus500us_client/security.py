"""
Security utilities for the Plus500US API client.
Provides secure logging and credential handling functionality.
"""

import logging
import os
from typing import Optional, Dict, Any
from .requests.security import secure_logger as _secure_logger, SecureCredentialHandler as _SecureCredentialHandler

# Re-export the secure_logger function for backward compatibility
def secure_logger(name: str) -> logging.Logger:
    """
    Create a secure logger with sanitized output.
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger instance
    """
    return _secure_logger(name)

# Re-export the SecureCredentialHandler class
SecureCredentialHandler = _SecureCredentialHandler

# Additional security utilities can be added here as needed
__all__ = ['secure_logger', 'SecureCredentialHandler']