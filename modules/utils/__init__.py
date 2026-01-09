"""
Utility Functions Module.

Contains helper functions for file paths, resource loading, and other utilities.
"""

from .path_utils import get_base_path, get_ui_path, get_data_path, get_resource_path
from .theme_utils import detect_system_theme, apply_theme

__all__ = [
    'get_base_path',
    'get_ui_path',
    'get_data_path',
    'get_resource_path',
    'detect_system_theme',
    'apply_theme',
]
