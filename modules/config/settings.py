"""
Application Settings Management.

Handles loading and saving application settings from external JSON config files.
Settings are stored in data/config/ and can be updated without rebuilding the exe.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional


class Settings:
    """Application settings container."""
    
    def __init__(self, settings_dict: Optional[Dict[str, Any]] = None):
        """
        Initialize settings from dictionary.
        
        Args:
            settings_dict: Dictionary of settings, or None to use defaults
        """
        if settings_dict is None:
            settings_dict = get_default_settings()
        
        self.window_width = settings_dict.get("window_width", 700)
        self.window_height = settings_dict.get("window_height", 700)
        self.min_width = settings_dict.get("min_width", 600)
        self.min_height = settings_dict.get("min_height", 550)
        self.default_threshold = settings_dict.get("default_threshold", 0.80)
        self.default_language = settings_dict.get("default_language", None)  # None = auto-detect
        self.default_theme = settings_dict.get("default_theme", None)  # None = auto-detect
        self.max_workers = settings_dict.get("max_workers", 8)
        self.progress_update_interval = settings_dict.get("progress_update_interval", 10)
        self.csv_encoding = settings_dict.get("csv_encoding", "utf-8")
        self.default_result_file = settings_dict.get("default_result_file", "result.csv")
        
        # Column names for output CSV
        self.column_names = settings_dict.get("column_names", {
            "CSV_COLUMN_REFERENCE": "reference",
            "CSV_COLUMN_BEST_MATCH": "best_match",
            "CSV_COLUMN_SIMILARITY": "similarity"
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary for saving."""
        return {
            "window_width": self.window_width,
            "window_height": self.window_height,
            "min_width": self.min_width,
            "min_height": self.min_height,
            "default_threshold": self.default_threshold,
            "default_language": self.default_language,
            "default_theme": self.default_theme,
            "max_workers": self.max_workers,
            "progress_update_interval": self.progress_update_interval,
            "csv_encoding": self.csv_encoding,
            "default_result_file": self.default_result_file,
            "column_names": self.column_names
        }


def get_default_settings() -> Dict[str, Any]:
    """Get default settings dictionary."""
    return {
        "window_width": 700,
        "window_height": 700,
        "min_width": 600,
        "min_height": 550,
        "default_threshold": 0.80,
        "default_language": None,  # Auto-detect
        "default_theme": None,  # Auto-detect
        "max_workers": 8,
        "progress_update_interval": 10,
        "csv_encoding": "utf-8",
        "default_result_file": "result.csv",
        "column_names": {
            "CSV_COLUMN_REFERENCE": "reference",
            "CSV_COLUMN_BEST_MATCH": "best_match",
            "CSV_COLUMN_SIMILARITY": "similarity"
        }
    }


def get_config_path(base_path: Optional[str] = None) -> Path:
    """
    Get the path to the config directory.
    
    Args:
        base_path: Base application path. If None, uses executable directory or current directory.
        
    Returns:
        Path to config directory
    """
    import sys
    
    if base_path is None:
        # Try to get executable directory (for PyInstaller)
        if hasattr(sys, '_MEIPASS'):
            # Running from PyInstaller bundle
            base_path = os.path.dirname(sys.executable)
        else:
            # Running as script - use project root
            from modules.utils.path_utils import get_base_path
            base_path = str(get_base_path())
    
    return Path(base_path) / "data" / "config"


def load_settings(config_file: str = "settings.json", base_path: Optional[str] = None) -> Settings:
    """
    Load settings from JSON config file.
    
    Args:
        config_file: Name of config file (default: settings.json)
        base_path: Base application path for finding data/config folder
        
    Returns:
        Settings object
    """
    
    config_path = get_config_path(base_path) / config_file
    
    if not config_path.exists():
        # Return default settings if config file doesn't exist
        return Settings()
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            settings_dict = json.load(f)
        return Settings(settings_dict)
    except Exception as e:
        # Return default settings if loading fails
        print(f"Warning: Failed to load settings from {config_path}: {e}")
        return Settings()


def save_settings(settings: Settings, config_file: str = "settings.json", base_path: Optional[str] = None):
    """
    Save settings to JSON config file.
    
    Args:
        settings: Settings object to save
        config_file: Name of config file (default: settings.json)
        base_path: Base application path for finding data/config folder
    """
    
    config_path = get_config_path(base_path)
    config_path.mkdir(parents=True, exist_ok=True)
    config_file_path = config_path / config_file
    
    try:
        with open(config_file_path, 'w', encoding='utf-8') as f:
            json.dump(settings.to_dict(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Warning: Failed to save settings to {config_file_path}: {e}")
