# Migration Guide

This document explains the changes made during the project restructuring.

## What Changed

### New Structure

The project has been restructured into a modular architecture with external UI and data:

```
uxas/
├── modules/          # Engine/runtime (packaged in exe)
│   ├── engine/      # CSV comparison engine
│   ├── config/      # Configuration & i18n
│   ├── utils/       # Utility functions
│   └── loader/      # Dynamic loading system
├── ui/              # UI modules (external, not in exe)
└── data/            # Config/data files (external, not in exe)
```

### Key Benefits

1. **Hot Updates**: UI and config can be updated without rebuilding the exe
2. **Modularity**: Clear separation of concerns
3. **Maintainability**: Easier to update and extend
4. **Distribution**: Smaller exe, external resources

## File Mapping

### Old → New

| Old Location | New Location | Notes |
|-------------|--------------|-------|
| `matcher.py` | `modules/engine/matcher.py` | Engine code |
| `strings.py` | `modules/config/strings.py` | Config (import path updated) |
| `translations.py` | `modules/config/translations.py` | Config (import path updated) |
| `app_pyside.py` (App class) | `ui/app_window.py` | UI module (dynamically loaded) |
| N/A | `modules/engine/csv_processor.py` | New: CSV processing with worker threads |
| N/A | `modules/config/settings.py` | New: Settings management |
| N/A | `modules/utils/` | New: Utility functions |
| N/A | `modules/loader/` | New: Dynamic loading system |
| N/A | `main_launcher.py` | New: Entry point that loads UI/data dynamically |

## Import Changes

### Old Imports
```python
from matcher import best_match
from strings import Strings
from translations import get_translator, t
```

### New Imports
```python
from modules.engine.csv_processor import CSVProcessor
from modules.config import Strings, get_translator, t, LANG_EN, LANG_RU
from modules.config.settings import Settings, load_settings
```

## Running the Application

### Before (Old Way)
```bash
python app_pyside.py
```

### After (New Way)
```bash
python main_launcher.py
```

## Building the Executable

### Before
Would need to rebuild for any UI/config changes.

### After
```bash
# Build once
python build_exe.py

# Update UI/config without rebuilding
# Just edit files in ui/ and data/ folders
```

## Updating UI

### Before
- Edit `app_pyside.py`
- Rebuild exe

### After
- Edit `ui/app_window.py` (or add new UI modules)
- Restart application (no rebuild needed!)

## Updating Configuration

### Before
- Hardcoded in code or require rebuild

### After
- Edit `data/config/settings.json`
- Restart application (no rebuild needed!)

## Migration Steps

If you have existing code using the old structure:

1. **Update imports**: Change all imports to use new module paths
2. **Update UI code**: Move UI classes to `ui/` folder
3. **Extract settings**: Move hardcoded config to `data/config/settings.json`
4. **Update entry point**: Use `main_launcher.py` instead of direct UI execution

## Backward Compatibility

The old files (`app_pyside.py`, `matcher.py`, etc.) are kept in the root for reference but are no longer used by the new architecture. You can safely remove them once you've verified everything works.

## Testing

After migration:

1. Test in development mode:
   ```bash
   python main_launcher.py
   ```

2. Test exe build:
   ```bash
   python build_exe.py
   ```

3. Test external updates:
   - Edit `ui/app_window.py` (change a label text)
   - Edit `data/config/settings.json` (change default threshold)
   - Restart application
   - Verify changes without rebuild

## Notes

- The `modules/` folder is included in the exe via PyInstaller `--add-data`
- The `ui/` and `data/` folders must be placed alongside the exe
- Path resolution handles both development and production modes automatically
