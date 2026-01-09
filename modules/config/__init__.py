"""
Configuration Module.

This module handles application configuration, translations, strings, and settings.
All configuration data should be external and loadable from the data/ folder.
"""

from .translations import Translator, get_translator, t, set_language, LANG_EN, LANG_RU, detect_system_language
from .strings import Strings, get_strings
from .settings import Settings, load_settings, save_settings, get_default_settings

__all__ = [
    'Translator',
    'get_translator',
    't',
    'set_language',
    'LANG_EN',
    'LANG_RU',
    'detect_system_language',
    'Strings',
    'get_strings',
    'Settings',
    'load_settings',
    'save_settings',
    'get_default_settings',
]
