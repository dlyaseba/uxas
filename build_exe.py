"""
Build script for creating a PyInstaller executable.

This script builds a onefile executable that contains only the engine/runtime.
UI and data files remain external and can be updated without rebuilding.

Usage:
    python build_exe.py
    
The executable will be created in the dist/ folder.
"""

import PyInstaller.__main__
import sys
from pathlib import Path

# Get project root
project_root = Path(__file__).parent

# PyInstaller arguments
args = [
    'main_launcher.py',           # Entry point
    '--name=uxas',                 # Executable name
    '--onefile',                   # Create single executable
    '--windowed',                  # No console window (GUI app)
    '--icon=logo.ico',             # Application icon (if exists)
    '--add-data', f'modules;modules',  # Include modules folder
    '--hidden-import=PySide6.QtCore',
    '--hidden-import=PySide6.QtGui',
    '--hidden-import=PySide6.QtWidgets',
    '--hidden-import=multiprocessing',
    '--hidden-import=csv',
    '--collect-all', 'PySide6',    # Collect all PySide6 dependencies
    '--noconfirm',                 # Overwrite output without asking
    '--clean',                     # Clean cache before building
]

# Add icon if it exists
if (project_root / 'logo.ico').exists():
    args.extend(['--icon=logo.ico'])

print("Building executable...")
print(f"Project root: {project_root}")
print(f"PyInstaller args: {args}")

try:
    PyInstaller.__main__.run(args)
    print("\n✓ Build complete!")
    print(f"Executable location: {project_root / 'dist' / 'uxas.exe'}")
    print("\nIMPORTANT:")
    print("  - The executable must be placed alongside the 'ui' and 'data' folders")
    print("  - UI files can be updated in ui/ folder without rebuilding")
    print("  - Data/config can be updated in data/ folder without rebuilding")
except Exception as e:
    print(f"\n✗ Build failed: {e}")
    sys.exit(1)
