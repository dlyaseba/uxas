"""
Theme utility functions for detecting and applying UI themes.
"""

import platform
from typing import Dict, Any


def detect_system_theme() -> str:
    """
    Detect system theme preference (light or dark).
    
    Returns:
        "light" or "dark"
    """
    try:
        if platform.system() == "Windows":
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            )
            apps_use_light_theme = winreg.QueryValueEx(key, "AppsUseLightTheme")[0]
            winreg.CloseKey(key)
            return "light" if apps_use_light_theme else "dark"
    except Exception:
        pass
    # Default to light theme if detection fails
    return "light"


def get_theme_colors(theme: str) -> Dict[str, str]:
    """
    Get color scheme for a theme.
    
    Args:
        theme: "light" or "dark"
        
    Returns:
        Dictionary of color values
    """
    themes = {
        "light": {
            "bg": "#FFFFFF",
            "fg": "#1E1E1E",
            "text_secondary": "#666666",
            "button_bg": "#F0F0F0",
            "button_fg": "#1E1E1E",
            "button_active": "#E0E0E0",
            "accent": "#0078D4",
            "accent_active": "#005A9E",
            "entry_bg": "#FFFFFF",
            "scale_trough": "#E0E0E0",
            "groupbox_bg": "#F5F5F5",
        },
        "dark": {
            "bg": "#1E1E1E",
            "fg": "#FFFFFF",
            "text_secondary": "#CCCCCC",
            "button_bg": "#2D2D2D",
            "button_fg": "#FFFFFF",
            "button_active": "#3D3D3D",
            "accent": "#0078D4",
            "accent_active": "#40A6FF",
            "entry_bg": "#2D2D2D",
            "scale_trough": "#3D3D3D",
            "groupbox_bg": "#2D2D2D",
        }
    }
    return themes.get(theme, themes["light"])


def apply_theme(widget, theme: str) -> str:
    """
    Apply a theme stylesheet to a widget.
    
    Args:
        widget: QWidget to apply theme to
        theme: "light" or "dark"
        
    Returns:
        Stylesheet string that was applied
    """
    colors = get_theme_colors(theme)
    
    stylesheet = f"""
        QMainWindow {{
            background-color: {colors["bg"]};
            color: {colors["fg"]};
        }}
        
        QWidget {{
            background-color: {colors["bg"]};
            color: {colors["fg"]};
        }}
        
        QLabel {{
            padding: 10px;
            border-radius: 4px;
            background-color: {colors["bg"]};
            color: {colors["fg"]};
        }}
        
        QPushButton {{
            background-color: {colors["button_bg"]};
            color: {colors["button_fg"]};
            border: none;
            padding: 8px 15px;
            border-radius: 4px;
        }}
        
        QPushButton:hover {{
            background-color: {colors["button_active"]};
        }}
        
        QPushButton:pressed {{
            background-color: {colors["button_active"]};
        }}
        
        QPushButton:disabled {{
            background-color: {colors["button_bg"]};
            color: {colors["text_secondary"]};
        }}
        
        QLineEdit {{
            background-color: {colors["entry_bg"]};
            color: {colors["fg"]};
            border: 1px solid {colors["scale_trough"]};
            border-radius: 3px;
            padding: 4px;
        }}
        
        QComboBox {{
            background-color: {colors["entry_bg"]};
            color: {colors["fg"]};
            border: 1px solid {colors["scale_trough"]};
            border-radius: 3px;
            padding: 4px;
        }}
        
        QComboBox::drop-down {{
            border: none;
        }}
        
        QComboBox QAbstractItemView {{
            background-color: {colors["entry_bg"]};
            color: {colors["fg"]};
            selection-background-color: {colors["accent"]};
            selection-color: white;
        }}
        
        QSlider::groove:horizontal {{
            border: 1px solid {colors["scale_trough"]};
            height: 8px;
            background: {colors["scale_trough"]};
            border-radius: 4px;
        }}
        
        QSlider::handle:horizontal {{
            background: {colors["accent"]};
            border: 1px solid {colors["accent"]};
            width: 18px;
            margin: -2px 0;
            border-radius: 9px;
        }}
        
        QSlider::handle:horizontal:hover {{
            background: {colors["accent_active"]};
        }}
        
        QProgressBar {{
            border: 1px solid {colors["scale_trough"]};
            border-radius: 4px;
            text-align: center;
            background-color: {colors["scale_trough"]};
        }}
        
        QProgressBar::chunk {{
            background-color: {colors["accent"]};
            border-radius: 3px;
        }}
        
        QGroupBox {{
            border: 1px solid {colors["scale_trough"]};
            border-radius: 4px;
            margin-top: 10px;
            padding: 10px;
            background-color: {colors["groupbox_bg"]};
            color: {colors["fg"]};
            font-weight: bold;
        }}
        
        QGroupBox::title {{
            subcontrol-origin: margin;
            border-radius: 4px;
            background-color: {colors["groupbox_bg"]};
        }}
        
        QCheckBox {{
            background-color: {colors["bg"]};
            color: {colors["fg"]};
        }}
        
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 1px solid {colors["scale_trough"]};
            border-radius: 3px;
            background-color: {colors["bg"]};
        }}
        
        QCheckBox::indicator:checked {{
            background-color: {colors["accent"]};
            border-color: {colors["accent"]};
        }}
        
        QTabWidget::pane {{
            border: 1px solid {colors["scale_trough"]};
            background-color: {colors["bg"]};
        }}
        
        QTabBar::tab {{
            background-color: {colors["button_bg"]};
            color: {colors["fg"]};
            padding: 8px 20px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }}
        
        QTabBar::tab:selected {{
            background-color: {colors["bg"]};
            color: {colors["fg"]};
        }}
        
        QScrollArea {{
            border: none;
            background-color: {colors["bg"]};
        }}
        
        QScrollBar:vertical {{
            background-color: {colors["bg"]};
            width: 12px;
            border: none;
        }}
        
        QScrollBar::handle:vertical {{
            background-color: {colors["scale_trough"]};
            min-height: 20px;
            border-radius: 6px;
        }}
        
        QScrollBar::handle:vertical:hover {{
            background-color: {colors["button_bg"]};
        }}
    """
    
    widget.setStyleSheet(stylesheet)
    return stylesheet
