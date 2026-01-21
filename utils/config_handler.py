"""
Configuration handler for saving and loading API settings.
Uses JSON file for storage with basic obfuscation for API key.
"""
import json
import base64
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

CONFIG_FILE = "pdf_marker_config.json"

def _obfuscate_api_key(api_key: str) -> str:
    """Basic obfuscation for API key (not secure, just for basic protection)."""
    if not api_key:
        return ""
    # Simple base64 encoding
    encoded = base64.b64encode(api_key.encode('utf-8')).decode('utf-8')
    return encoded

def _deobfuscate_api_key(obfuscated_key: str) -> str:
    """Deobfuscate API key."""
    if not obfuscated_key:
        return ""
    try:
        decoded = base64.b64decode(obfuscated_key.encode('utf-8')).decode('utf-8')
        return decoded
    except Exception as e:
        logger.warning(f"Failed to deobfuscate API key: {e}")
        return ""

def save_config(
    base_url: str,
    api_key: str,
    model: str,
    dpi: int,
    max_tokens: int,
    temperature: float
) -> bool:
    """
    Save configuration to JSON file.

    Args:
        base_url: API base URL
        api_key: API key (will be obfuscated)
        model: Model name
        dpi: Image DPI setting
        max_tokens: Max tokens setting
        temperature: Temperature setting

    Returns:
        True if successful, False otherwise
    """
    config = {
        "base_url": base_url,
        "api_key": _obfuscate_api_key(api_key),
        "model": model,
        "dpi": dpi,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "version": "1.0"
    }

    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        logger.info(f"Configuration saved to {CONFIG_FILE}")
        return True
    except Exception as e:
        logger.error(f"Failed to save configuration: {e}")
        return False

def load_config() -> Optional[Dict[str, Any]]:
    """
    Load configuration from JSON file.

    Returns:
        Dictionary with configuration or None if not found/error
    """
    if not os.path.exists(CONFIG_FILE):
        logger.info(f"No configuration file found at {CONFIG_FILE}")
        return None

    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # Deobfuscate API key
        if "api_key" in config and config["api_key"]:
            config["api_key"] = _deobfuscate_api_key(config["api_key"])

        # Set default values for missing keys
        defaults = {
            "base_url": "https://api.deepseek.com",
            "api_key": "",
            "model": "deepseek-chat",
            "dpi": 300,
            "max_tokens": 2000,
            "temperature": 0.1,
        }

        for key, default_value in defaults.items():
            if key not in config:
                config[key] = default_value

        logger.info(f"Configuration loaded from {CONFIG_FILE}")
        return config
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in configuration file: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        return None

def get_default_config() -> Dict[str, Any]:
    """Get default configuration values."""
    return {
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "model": "deepseek-chat",
        "dpi": 300,
        "max_tokens": 2000,
        "temperature": 0.1,
    }

def clear_config() -> bool:
    """Clear configuration file."""
    try:
        if os.path.exists(CONFIG_FILE):
            os.remove(CONFIG_FILE)
            logger.info(f"Configuration file {CONFIG_FILE} removed")
        return True
    except Exception as e:
        logger.error(f"Failed to clear configuration: {e}")
        return False

def config_exists() -> bool:
    """Check if configuration file exists."""
    return os.path.exists(CONFIG_FILE)