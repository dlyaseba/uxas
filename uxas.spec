# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for Uxas application

import sys
from pathlib import Path

block_cipher = None

# Project root
project_root = Path(SPECPATH)

a = Analysis(
    ['main_launcher.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('modules', 'modules'),  # Include modules folder
    ],
    hiddenimports=[
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtUiTools',
        'multiprocessing',
        'csv',
        'json',
        'locale',
        'winreg',
        'modules.engine',
        'modules.engine.matcher',
        'modules.engine.csv_processor',
        'modules.engine.processor_utils',
        'modules.config',
        'modules.config.translations',
        'modules.config.strings',
        'modules.config.settings',
        'modules.utils',
        'modules.utils.path_utils',
        'modules.utils.theme_utils',
        'modules.loader',
        'modules.loader.ui_loader',
        'modules.loader.data_loader',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='uxas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='logo.ico' if (project_root / 'logo.ico').exists() else None,
)
