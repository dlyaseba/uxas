"""
Main Launcher Script for Uxas Application.

This script loads the engine, UI, and data dynamically at runtime.
It serves as the entry point for both development and production (exe) modes.

The launcher:
1. Loads settings from data/config/
2. Dynamically loads the UI module from ui/
3. Initializes the application with loaded settings
4. Starts the Qt event loop
"""

import sys
import os
from pathlib import Path

# Add modules to path if running as script (not from exe)
if not hasattr(sys, '_MEIPASS'):
    # Running as script - add project root to path
    project_root = Path(__file__).parent
    sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication, QMessageBox

# Import from modules
from modules.config.settings import load_settings, Settings
from modules.utils.path_utils import get_base_path, get_ui_path
from modules.loader.ui_loader import load_ui_module


def main():
    """Main entry point for the application."""
    
    # Create Qt application
    app = QApplication(sys.argv)
    # High DPI scaling is enabled by default in PySide6/Qt6, no need to set these attributes
    
    try:
        # Load settings from external config
        base_path = get_base_path()
        settings = load_settings(base_path=str(base_path))
        
        # Load UI module dynamically
        ui_module = load_ui_module("app_window", get_ui_path())
        
        if ui_module is None:
            QMessageBox.critical(
                None,
                "Error",
                "Failed to load UI module.\n"
                "Please ensure ui/app_window.py exists."
            )
            return 1
        
        # Get the App class from the loaded module
        if not hasattr(ui_module, 'App'):
            QMessageBox.critical(
                None,
                "Error",
                "UI module does not contain 'App' class.\n"
                "Please ensure ui/app_window.py defines an App class."
            )
            return 1
        
        AppWindow = ui_module.App
        
        # Create and show main window
        window = AppWindow(settings=settings)
        window.show()
        
        # Run event loop
        return app.exec()
        
    except Exception as e:
        # Show error dialog if something goes wrong
        import traceback
        error_msg = f"Failed to start application:\n\n{str(e)}\n\n{traceback.format_exc()}"
        
        QMessageBox.critical(
            None,
            "Fatal Error",
            error_msg
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
