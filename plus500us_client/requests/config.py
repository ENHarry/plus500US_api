from __future__ import annotations
import os
from pathlib import Path
from typing import Optional, Dict, Any
from unittest import result
import yaml
from pydantic import BaseModel, Field

# Removed circular import - trade_manager import not needed here

DEFAULT_CFG_PATH = Path.home() / ".plus500.yaml"
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the project root
project_root = Path(__file__).resolve().parents[1]
result = load_dotenv(project_root / ".env")
# Also try loading from current working directory
result = load_dotenv(".env")

class Config(BaseModel):
    base_url: str = "https://futures.plus500.com" # Use as sender and referer of trade requests
    host_url: str = "https://api-futures.plus500.com" # For trade operations
    trade_url: str = f"{base_url}/trade"
    account_type: str = "demo"  # or "live"
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3"
    accept_language: str = "en-US,en;q=0.9"
    poll_interval_ms: int = 1000
    max_requests_per_minute: int = 60
    futures_metadata: Dict[str, Dict[str, float]] = Field(default_factory=dict)
    
    # WebDriver configuration
    webdriver_config: Dict[str, Any] = Field(default_factory=lambda: {
        "browser": "firefox",
        "headless": False,
        "stealth_mode": True,
        "window_size": (1920, 1080),
        "implicit_wait": 10,
        "page_load_timeout": 30,
        "profile_path": "~/.plus500_profile",
        "disable_images": False
    })
    
    # Automation method preference
    preferred_method: str = "auto"  # "webdriver" or "requests" or "auto"
    
    # Credentials (will be loaded from env/config)
    email: Optional[str] = os.getenv("email") or None
    password: Optional[str] = os.getenv("password") or None
    totp_secret: Optional[str] = os.getenv("totp_secret") or None

def load_config(path: Optional[Path] = None) -> Config:
    path = path or DEFAULT_CFG_PATH
    data: Dict[str, Any] = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

    # Env overrides
    env_map = {
        "email": ("email", None),
        "password": ("password", None),
        "totp_secret": ("totp_secret", None),
        "base_url": ("base_url", None),
        "account_type": ("account_type", None),
        "browser": ("webdriver_config.browser", None),
        "PLUS500_BROWSER": ("webdriver_config.browser", None),  # Backward compatibility
    }
    for env, (key, _) in env_map.items():
        if os.getenv(env):
            if "." in key:
                # Handle nested config like webdriver_config.browser
                parent_key, child_key = key.split(".", 1)
                if parent_key not in data:
                    data[parent_key] = {}
                data[parent_key][child_key] = os.getenv(env)
            else:
                data[key] = os.getenv(env)
            print(f"Using environment variable {env} for {key}")
    return Config(**data)

