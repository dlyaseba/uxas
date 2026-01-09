"""
Path utility functions for locating resources, UI files, and data files.

These functions handle both development (script) and production (PyInstaller exe) modes.
"""

import os
import sys
from pathlib import Path
from typing import Optional


def get_base_path() -> Path:
    """
    Get the base application path.
    
    In PyInstaller bundle: Returns directory containing the executable
    In script mode: Returns the project root directory
    
    Returns:
        Path to base application directory
    """
    if hasattr(sys, '_MEIPASS'):
        # Running from PyInstaller bundle - use executable directory as base
        return Path(os.path.dirname(sys.executable))
    else:
        # Running as script - use project root (parent of modules/)
        script_path = Path(__file__).resolve()
        # Go from modules/utils/path_utils.py to project root
        return script_path.parent.parent.parent


def get_ui_path() -> Path:
    """
    Get the path to the UI directory.
    
    UI files can be .ui files (Qt Designer) or .py files (compiled UI).
    
    Returns:
        Path to ui/ directory
    """
    base_path = get_base_path()
    return base_path / "ui"


def get_data_path() -> Path:
    """
    Get the path to the data directory.
    
    Data directory contains config, templates, and profiles.
    
    Returns:
        Path to data/ directory
    """
    base_path = get_base_path()
    return base_path / "data"


def get_resource_path(*relative_path_parts: str) -> Path:
    """
    Get a path to a resource file.
    
    Args:
        *relative_path_parts: Relative path parts (e.g., "config", "settings.json")
        
    Returns:
        Path to resource file
        
    Example:
        get_resource_path("config", "settings.json")
        get_resource_path("templates", "template.csv")
    """
    data_path = get_data_path()
    return data_path / Path(*relative_path_parts)


def ensure_directory(path: Path) -> Path:
    """
    Ensure a directory exists, creating it if necessary.
    
    Args:
        path: Path to directory
        
    Returns:
        Path object (same as input)
    """
    path.mkdir(parents=True, exist_ok=True)
    return path
