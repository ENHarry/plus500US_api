#!/usr/bin/env python3
"""Test script to verify .env loading and credential handling"""

import os
from plus500us_client import load_config

def test_env_loading():
    print("=== Environment Variable Test ===")
    
    # Check if .env variables are loaded
    env_vars = [
        "PLUS500US_EMAIL",
        "PLUS500US_PASSWORD", 
        "PLUS500US_TOTP_SECRET",
        "PLUS500US_ACCOUNT_TYPE",
        "PLUS500US_BASE_URL"
    ]
    
    print("Environment variables:")
    for var in env_vars:
        value = os.getenv(var)
        if value:
            # Hide password for security
            display_value = "***HIDDEN***" if "PASSWORD" in var else value
            print(f"  {var}: {display_value}")
        else:
            print(f"  {var}: (not set)")
    
    print("\n=== Config Loading Test ===")
    
    try:
        cfg = load_config()
        print("Config loaded successfully:")
        print(f"  Base URL: {cfg.base_url}")
        print(f"  Host URL: {cfg.host_url}")
        print(f"  Account Type: {cfg.account_type}")
        print(f"  Email: {cfg.email if cfg.email else '(not set)'}")
        print(f"  Password: {'***SET***' if cfg.password else '(not set)'}")
        print(f"  TOTP Secret: {'***SET***' if cfg.totp_secret else '(not set)'}")
        
    except Exception as e:
        print(f"Error loading config: {e}")

if __name__ == "__main__":
    test_env_loading()