"""
Data Loader for dynamically loading data files, configs, and templates.

Supports loading JSON config files, CSV templates, and other data files.
"""

import json
import csv
from pathlib import Path
from typing import Optional, List, Dict, Any

from modules.utils.path_utils import get_data_path


def load_data_file(relative_path: str, data_path: Optional[Path] = None) -> Optional[Path]:
    """
    Get path to a data file.
    
    Args:
        relative_path: Relative path from data/ directory (e.g., "config/settings.json")
        data_path: Base data path (defaults to get_data_path())
        
    Returns:
        Path to data file, or None if not found
    """
    if data_path is None:
        data_path = get_data_path()
    
    file_path = data_path / relative_path
    
    if file_path.exists():
        return file_path
    
    return None


def load_json_config(config_file: str, subdirectory: str = "config", 
                    data_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Load a JSON configuration file from the data directory.
    
    Args:
        config_file: Name of config file (with or without .json extension)
        subdirectory: Subdirectory within data/ (default: "config")
        data_path: Base data path (defaults to get_data_path())
        
    Returns:
        Dictionary with config data, or None if loading fails
    """
    if data_path is None:
        data_path = get_data_path()
    
    if not config_file.endswith('.json'):
        config_file = f"{config_file}.json"
    
    config_path = data_path / subdirectory / config_file
    
    if not config_path.exists():
        print(f"Warning: Config file {config_path} not found")
        return None
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading config file {config_file}: {e}")
        return None


def load_csv_template(template_file: str, subdirectory: str = "templates",
                     data_path: Optional[Path] = None) -> Optional[List[Dict[str, str]]]:
    """
    Load a CSV template file.
    
    Args:
        template_file: Name of template file (with or without .csv extension)
        subdirectory: Subdirectory within data/ (default: "templates")
        data_path: Base data path (defaults to get_data_path())
        
    Returns:
        List of dictionaries (rows), or None if loading fails
    """
    if data_path is None:
        data_path = get_data_path()
    
    if not template_file.endswith('.csv'):
        template_file = f"{template_file}.csv"
    
    template_path = data_path / subdirectory / template_file
    
    if not template_path.exists():
        print(f"Warning: Template file {template_path} not found")
        return None
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            return list(reader)
    except Exception as e:
        print(f"Error loading template file {template_file}: {e}")
        return None


def list_data_files(subdirectory: str = "", pattern: str = "*",
                   data_path: Optional[Path] = None) -> List[str]:
    """
    List data files in a subdirectory.
    
    Args:
        subdirectory: Subdirectory within data/ (empty string for root)
        pattern: File pattern to match (e.g., "*.json", "*.csv")
        data_path: Base data path (defaults to get_data_path())
        
    Returns:
        List of file names matching the pattern
    """
    if data_path is None:
        data_path = get_data_path()
    
    if subdirectory:
        search_path = data_path / subdirectory
    else:
        search_path = data_path
    
    if not search_path.exists():
        return []
    
    files = []
    for file in search_path.glob(pattern):
        if file.is_file():
            files.append(file.name)
    
    return sorted(files)
