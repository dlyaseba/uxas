# Uxas - CSV Matching Application

A PySide6-based application for matching and comparing CSV files with external UI and data architecture.

## Project Structure

```
uxas/
├── modules/                  # Engine/runtime code (packaged in exe)
│   ├── engine/              # CSV comparison engine
│   │   ├── __init__.py
│   │   ├── matcher.py       # String matching algorithms
│   │   ├── csv_processor.py # CSV processing and worker threads
│   │   └── processor_utils.py
│   ├── config/              # Configuration handling
│   │   ├── __init__.py
│   │   ├── translations.py  # i18n translations
│   │   ├── strings.py       # UI string constants
│   │   └── settings.py      # Settings management
│   ├── utils/               # Utility functions
│   │   ├── __init__.py
│   │   ├── path_utils.py    # Path resolution utilities
│   │   └── theme_utils.py   # Theme management
│   └── loader/              # Dynamic loading system
│       ├── __init__.py
│       ├── ui_loader.py     # UI module loader
│       └── data_loader.py   # Data file loader
│
├── ui/                       # UI modules (EXTERNAL - not in exe)
│   ├── __init__.py
│   └── app_window.py        # Main application window
│
├── data/                     # Data files (EXTERNAL - not in exe)
│   ├── config/
│   │   └── settings.json    # Application settings
│   ├── templates/           # CSV templates
│   └── profiles/            # CSV profiles
│
├── main_launcher.py         # Entry point script
├── build_exe.py             # Build script
├── uxas.spec                # PyInstaller spec file
├── logo.ico                 # Application icon
└── README.md                # This file
```

## Key Features

- **External UI**: UI modules in `ui/` folder can be updated without rebuilding the exe
- **External Data**: Config, templates, and profiles in `data/` folder are loaded at runtime
- **Modular Architecture**: Clean separation of engine, config, utils, and loader
- **Dynamic Loading**: UI and data files are loaded dynamically at runtime
- **PyInstaller Ready**: Configured for `--onefile` builds with external resources

## Development Setup

### Prerequisites

- Python 3.8+
- PySide6
- PyInstaller (for building exe)

### Installation

```bash
# Install dependencies
pip install PySide6 PyInstaller

# Run the application
python main_launcher.py
```

## Building the Executable

### Quick Build

```bash
python build_exe.py
```

This will create a single executable file in `dist/uxas.exe` (Windows) or `dist/uxas` (Linux/Mac).

### Manual Build with PyInstaller

```bash
pyinstaller uxas.spec
```

Or directly:

```bash
pyinstaller --onefile --windowed --add-data "modules;modules" --name=uxas main_launcher.py
```

### Important Notes for Distribution

1. **Folder Structure**: When distributing the exe, ensure the following structure:
   ```
   release/
   ├── uxas.exe          # The executable
   ├── ui/               # UI folder (required)
   │   └── app_window.py
   └── data/             # Data folder (required)
       ├── config/
       │   └── settings.json
       ├── templates/
       └── profiles/
   ```

2. **External Files**: The `ui/` and `data/` folders must be in the same directory as the exe.

3. **No Rebuild Needed**: You can update UI files in `ui/` and config files in `data/` without rebuilding the exe.

## Updating UI and Data

### Updating UI

1. Edit files in the `ui/` folder
2. Restart the application (no rebuild needed!)
3. Changes take effect immediately

**Supported UI formats:**
- Python modules (`.py`) - Recommended for complex UI
- Qt Designer files (`.ui`) - Loaded at runtime via `QUiLoader`

### Updating Configuration

1. Edit `data/config/settings.json`
2. Restart the application
3. New settings are loaded automatically

**Available settings:**
- `window_width`, `window_height`: Window size
- `min_width`, `min_height`: Minimum window size
- `default_threshold`: Default similarity threshold (0-1)
- `default_language`: Language code (null = auto-detect)
- `default_theme`: "light" or "dark" (null = auto-detect)
- `max_workers`: Maximum parallel processing workers
- `csv_encoding`: CSV file encoding (default: "utf-8")
- `default_result_file`: Default filename for results
- `column_names`: Output CSV column name mappings

### Adding Templates and Profiles

Place CSV template files in `data/templates/` and profile files in `data/profiles/`. These can be loaded programmatically using the data loader utilities.

## Module Documentation

### Engine Module (`modules/engine/`)

Core CSV matching and processing functionality.

- **matcher.py**: String matching algorithms (tokenization, similarity scoring)
- **csv_processor.py**: CSV file processing, worker threads, parallel execution
- **processor_utils.py**: Multiprocessing utilities

### Config Module (`modules/config/`)

Configuration and internationalization.

- **translations.py**: Multi-language support (English, Russian)
- **strings.py**: UI string constants with translation support
- **settings.py**: Application settings management (JSON-based)

### Utils Module (`modules/utils/`)

Utility functions for paths, themes, etc.

- **path_utils.py**: Path resolution for development and production modes
- **theme_utils.py**: Theme detection and application

### Loader Module (`modules/loader/`)

Dynamic loading system for UI and data files.

- **ui_loader.py**: Load Python UI modules or Qt Designer `.ui` files
- **data_loader.py**: Load JSON configs, CSV templates, and other data files

## Architecture Principles

1. **Separation of Concerns**: Engine, UI, and data are completely separate
2. **Runtime Loading**: UI and data loaded at runtime, not bundled in exe
3. **Hot Updates**: UI and config can be updated without rebuilding
4. **Portability**: Single executable + external folders for easy distribution
5. **Maintainability**: Clear module boundaries and responsibilities

## Troubleshooting

### "Failed to load UI module"

- Ensure `ui/app_window.py` exists in the same directory as the exe
- Check that the UI module doesn't have syntax errors
- Verify all imports in the UI module are correct

### "Failed to load settings"

- Ensure `data/config/settings.json` exists
- Check JSON syntax is valid
- Default settings will be used if file is missing or invalid

### Import Errors

- Ensure `modules/` folder is properly included during PyInstaller build
- Check that all required hidden imports are listed in `uxas.spec`
- Verify Python path includes project root when running as script

### Path Resolution Issues

- In production (exe): Uses executable directory as base path
- In development: Uses project root as base path
- Path utilities handle both cases automatically

## Contributing

When adding new features:

1. **Engine code** → `modules/engine/` (requires rebuild)
2. **UI code** → `ui/` (no rebuild needed)
3. **Config/data** → `data/` (no rebuild needed)
4. **Utilities** → `modules/utils/` (requires rebuild)

## License

[Your License Here]

## Version History

- **1.0.0** - Initial modular architecture with external UI and data
