"""
UI Loader for dynamically loading UI modules and files.

Supports loading:
- Python UI modules (.py files) - compiled from Qt Designer .ui files
- Qt Designer .ui files directly (requires PySide6.QtUiTools)
"""

import importlib.util
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any

from modules.utils.path_utils import get_ui_path


def load_ui_module(module_name: str, ui_path: Optional[Path] = None) -> Optional[Any]:
    """
    Dynamically load a UI module from a Python file.
    
    Args:
        module_name: Name of the UI module (without .py extension)
        ui_path: Path to UI directory (defaults to get_ui_path())
        
    Returns:
        Loaded module object, or None if loading fails
        
    Example:
        ui_module = load_ui_module("app_window")
        AppWindow = ui_module.AppWindow  # Get the window class
    """
    if ui_path is None:
        ui_path = get_ui_path()
    
    module_file = ui_path / f"{module_name}.py"
    
    if not module_file.exists():
        print(f"Warning: UI module {module_file} not found")
        return None
    
    try:
        spec = importlib.util.spec_from_file_location(f"ui.{module_name}", module_file)
        if spec is None or spec.loader is None:
            print(f"Warning: Failed to create spec for {module_file}")
            return None
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[f"ui.{module_name}"] = module
        spec.loader.exec_module(module)
        
        return module
    except Exception as e:
        print(f"Error loading UI module {module_name}: {e}")
        return None


def load_ui_file(ui_file: str, ui_path: Optional[Path] = None) -> Optional[Any]:
    """
    Load a Qt Designer .ui file and return the UI widget.
    
    This requires PySide6.QtUiTools. The .ui file is compiled at runtime.
    
    Args:
        ui_file: Name of .ui file (with or without extension)
        ui_path: Path to UI directory (defaults to get_ui_path())
        
    Returns:
        QWidget from the .ui file, or None if loading fails
    """
    try:
        from PySide6.QtUiTools import QUiLoader
        from PySide6.QtCore import QFile, QIODevice
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print("Error: PySide6.QtUiTools not available for loading .ui files")
        return None
    
    if ui_path is None:
        ui_path = get_ui_path()
    
    if not ui_file.endswith('.ui'):
        ui_file = f"{ui_file}.ui"
    
    ui_file_path = ui_path / ui_file
    
    if not ui_file_path.exists():
        print(f"Warning: UI file {ui_file_path} not found")
        return None
    
    try:
        loader = QUiLoader()
        file = QFile(str(ui_file_path))
        if not file.open(QIODevice.ReadOnly):
            print(f"Error: Cannot open {ui_file_path}: {file.errorString()}")
            return None
        
        widget = loader.load(file)
        file.close()
        
        if widget is None:
            print(f"Error: Failed to load UI from {ui_file_path}")
            return None
        
        return widget
    except Exception as e:
        print(f"Error loading UI file {ui_file}: {e}")
        return None


def list_ui_modules(ui_path: Optional[Path] = None) -> List[str]:
    """
    List all available UI modules (Python files) in the UI directory.
    
    Args:
        ui_path: Path to UI directory (defaults to get_ui_path())
        
    Returns:
        List of module names (without .py extension)
    """
    if ui_path is None:
        ui_path = get_ui_path()
    
    if not ui_path.exists():
        return []
    
    modules = []
    for file in ui_path.glob("*.py"):
        if file.name != "__init__.py":
            modules.append(file.stem)
    
    return sorted(modules)
