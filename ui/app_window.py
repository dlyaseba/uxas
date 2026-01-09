import csv
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QLineEdit, QProgressBar,
    QTabWidget, QGroupBox, QCheckBox, QScrollArea, QFileDialog, QMessageBox,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

# Import from new modular structure
from modules.engine.csv_processor import CSVProcessor
from modules.config import Strings, get_translator, t, LANG_EN, LANG_RU
from modules.config.settings import Settings, load_settings
from modules.utils.theme_utils import detect_system_theme, get_theme_colors


class App(QMainWindow):
    def __init__(self, settings=None):
        super().__init__()
        # Load settings
        if settings is None:
            settings = load_settings()
        self.settings = settings
        
        # Get column names from settings
        self.column_names = settings.column_names
        self.setWindowTitle(Strings.WINDOW_TITLE)
        self.setGeometry(100, 100, settings.window_width, settings.window_height)
        self.setMinimumSize(settings.min_width, settings.min_height)

        # Theme management
        self.current_theme = self._detect_system_theme()
        self._setup_themes()
        
        # Language management
        self.translator = get_translator()
        self.current_language = self.translator.language

        # Keep raw column headers (may include empty strings) separate from what we display.
        self.ref_path = None
        self.cand_path = None
        self.ref_columns_raw = []
        self.cand_columns_raw = []
        self.ref_column = None
        self.cand_column = None
        self._last_results = None
        self.selected_ref_columns = set()  # Reference columns selected for output
        self.selected_cand_columns = set()  # Candidate columns selected for output
        self.column_checkboxes = {}  # Store checkbox widgets
        self.matching_worker = None

        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(10)

        # Header with title, language selector, and theme switcher
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        self.title_label = QLabel(Strings.WINDOW_TITLE)
        title_font = QFont("Segoe UI", 24, QFont.Bold)
        self.title_label.setFont(title_font)
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()

        # Language selector
        self.language_combo = QComboBox()
        self.language_combo.addItem(t("lang_english"), LANG_EN)
        self.language_combo.addItem(t("lang_russian"), LANG_RU)
        # Set initial language
        lang_index = 0 if self.current_language == LANG_EN else 1
        self.language_combo.setCurrentIndex(lang_index)
        self.language_combo.currentIndexChanged.connect(self.on_language_changed)
        self.language_combo.setMaximumWidth(120)
        language_label = QLabel("🌐")  # Language icon
        language_label.setToolTip(t("lang_english") if self.current_language == LANG_EN else t("lang_russian"))
        header_layout.addWidget(language_label)
        header_layout.addWidget(self.language_combo)

        # Theme switcher button
        theme_icon = "🌙" if self.current_theme == "light" else "☀️"
        self.theme_button = QPushButton(theme_icon)
        self.theme_button.setMaximumWidth(50)
        self.theme_button.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_button)
        main_layout.addLayout(header_layout)

        # Create tab widget with proper size policy
        self.tab_widget = QTabWidget()
        self.tab_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        main_layout.addWidget(self.tab_widget, 1)  # Stretch factor of 1 to make it expand

        # Tab 1: Matching
        matching_tab = QWidget()
        matching_layout = QVBoxLayout(matching_tab)
        matching_layout.setContentsMargins(10, 10, 10, 10)
        matching_layout.setSpacing(10)
        self.matching_tab_index = 0
        self.tab_widget.addTab(matching_tab, t("tab_matching"))

        # Tab 2: Column Selection
        column_tab = QWidget()
        column_layout = QVBoxLayout(column_tab)
        column_layout.setContentsMargins(10, 10, 10, 10)
        column_layout.setSpacing(10)
        self.column_tab_index = 1
        self.tab_widget.addTab(column_tab, t("tab_output_columns"))

        # Setup Column Selection Tab UI
        self._setup_column_selection_tab(column_tab, column_layout)

        # Reference file section
        ref_group = QGroupBox("")
        ref_layout = QVBoxLayout(ref_group)
        ref_layout.setSpacing(8)

        ref_button_layout = QHBoxLayout()
        ref_button_layout.setSpacing(10)
        self.ref_button = QPushButton(Strings.BTN_SELECT_REFERENCE)
        self.ref_button.clicked.connect(self.load_ref)
        ref_button_layout.addWidget(self.ref_button)

        self.ref_label = QLabel(Strings.LABEL_REFERENCE_NOT_SELECTED)
        self.ref_label.setWordWrap(True)
        ref_button_layout.addWidget(self.ref_label, 1)
        ref_layout.addLayout(ref_button_layout)

        ref_column_layout = QHBoxLayout()
        ref_column_layout.setSpacing(10)
        self.ref_column_label = QLabel(t("label_column"))
        ref_column_layout.addWidget(self.ref_column_label)
        self.ref_column_combo = QComboBox()
        self.ref_column_combo.setEditable(False)
        self.ref_column_combo.currentIndexChanged.connect(self.on_ref_column_selected)
        ref_column_layout.addWidget(self.ref_column_combo, 1)
        ref_layout.addLayout(ref_column_layout)

        matching_layout.addWidget(ref_group)

        # Candidates file section
        cand_group = QGroupBox("")
        cand_layout = QVBoxLayout(cand_group)
        cand_layout.setSpacing(8)

        cand_button_layout = QHBoxLayout()
        cand_button_layout.setSpacing(10)
        self.cand_button = QPushButton(Strings.BTN_SELECT_CANDIDATES)
        self.cand_button.clicked.connect(self.load_cand)
        cand_button_layout.addWidget(self.cand_button)

        self.cand_label = QLabel(Strings.LABEL_CANDIDATES_NOT_SELECTED)
        self.cand_label.setWordWrap(True)
        cand_button_layout.addWidget(self.cand_label, 1)
        cand_layout.addLayout(cand_button_layout)

        cand_column_layout = QHBoxLayout()
        cand_column_layout.setSpacing(10)
        self.cand_column_label = QLabel(t("label_column"))
        cand_column_layout.addWidget(self.cand_column_label)
        self.cand_column_combo = QComboBox()
        self.cand_column_combo.setEditable(False)
        self.cand_column_combo.currentIndexChanged.connect(self.on_cand_column_selected)
        cand_column_layout.addWidget(self.cand_column_combo, 1)
        cand_layout.addLayout(cand_column_layout)

        matching_layout.addWidget(cand_group)

        # Threshold section
        threshold_group = QGroupBox("")
        threshold_layout = QVBoxLayout(threshold_group)
        threshold_layout.setSpacing(8)

        threshold_controls = QHBoxLayout()
        threshold_controls.setSpacing(10)
        self.threshold_label = QLabel(Strings.LABEL_THRESHOLD)
        threshold_controls.addWidget(self.threshold_label)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(int(self.settings.default_threshold * 100))
        self.threshold_slider.valueChanged.connect(self.on_slider_change)
        threshold_controls.addWidget(self.threshold_slider, 1)  # Make slider expand

        self.threshold_entry = QLineEdit()
        self.threshold_entry.setText(f"{self.settings.default_threshold:.2f}")
        self.threshold_entry.setMaximumWidth(60)
        self.threshold_entry.setMinimumWidth(60)
        self.threshold_entry.returnPressed.connect(self.on_entry_change)
        self.threshold_entry.editingFinished.connect(self.on_entry_change)
        threshold_controls.addWidget(self.threshold_entry)

        threshold_layout.addLayout(threshold_controls)
        matching_layout.addWidget(threshold_group)

        # Action buttons
        action_layout = QHBoxLayout()
        action_layout.setSpacing(10)
        self.run_button = QPushButton(Strings.BTN_RUN)
        self.run_button.clicked.connect(self.run)
        action_layout.addWidget(self.run_button)

        self.save_button = QPushButton(Strings.BTN_SAVE_RESULTS)
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        action_layout.addWidget(self.save_button)
        action_layout.addStretch()  # Push buttons to the left
        matching_layout.addLayout(action_layout)

        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        matching_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        matching_layout.addWidget(self.status_label)
        
        # Add stretch at the end to push everything up and prevent excessive spacing
        matching_layout.addStretch()
        
        # Apply initial theme after all widgets are created
        self._apply_theme()

    def _setup_column_selection_tab(self, tab, layout):
        """Setup the column selection tab with checkboxes."""
        self.column_info_label = QLabel(t("column_selection_info"))
        self.column_info_label.setWordWrap(True)
        layout.addWidget(self.column_info_label)

        # Create scrollable area for checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.column_checkbox_widget = QWidget()
        self.column_checkbox_layout = QVBoxLayout(self.column_checkbox_widget)
        self.column_checkbox_layout.setSpacing(5)
        scroll_area.setWidget(self.column_checkbox_widget)
        layout.addWidget(scroll_area, 1)  # Give scroll area stretch factor to expand

        # Buttons for select all/none
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        self.select_all_btn = QPushButton(t("btn_select_all"))
        self.select_all_btn.clicked.connect(self._select_all_columns)
        button_layout.addWidget(self.select_all_btn)

        self.select_none_btn = QPushButton(t("btn_select_none"))
        self.select_none_btn.clicked.connect(self._select_none_columns)
        button_layout.addWidget(self.select_none_btn)
        button_layout.addStretch()  # Push buttons to the left
        layout.addLayout(button_layout)

    def _detect_system_theme(self):
        """Detect system theme preference."""
        return detect_system_theme()

    def _setup_themes(self):
        """Setup light and dark theme color schemes."""
        # Themes are now handled by theme_utils, but we store them for easy access
        self.themes = {
            "light": get_theme_colors("light"),
            "dark": get_theme_colors("dark")
        }

    def on_language_changed(self, index):
        """Handle language change."""
        if index >= 0:
            new_lang = self.language_combo.itemData(index)
            if new_lang and new_lang != self.current_language:
                self.translator.set_language(new_lang)
                self.current_language = new_lang
                self._update_ui_language()
    
    def _update_ui_language(self):
        """Update all UI text to reflect current language."""
        # Update title
        self.title_label.setText(Strings.WINDOW_TITLE)
        
        # Update tab titles
        self.tab_widget.setTabText(0, t("tab_matching"))
        self.tab_widget.setTabText(1, t("tab_output_columns"))
        
        # Update buttons
        self.ref_button.setText(Strings.BTN_SELECT_REFERENCE)
        self.cand_button.setText(Strings.BTN_SELECT_CANDIDATES)
        self.run_button.setText(Strings.BTN_RUN)
        self.save_button.setText(Strings.BTN_SAVE_RESULTS)
        self.select_all_btn.setText(t("btn_select_all"))
        self.select_none_btn.setText(t("btn_select_none"))
        
        # Update labels
        self.ref_column_label.setText(t("label_column"))
        self.cand_column_label.setText(t("label_column"))
        self.column_info_label.setText(t("column_selection_info"))
        self.threshold_label.setText(t("label_threshold"))
        
        # Update file selection labels
        if self.ref_path:
            # File is loaded, update with translated format
            self.ref_label.setText(Strings.format_reference_label(os.path.basename(self.ref_path)))
        else:
            # No file loaded, show not selected message
            self.ref_label.setText(Strings.LABEL_REFERENCE_NOT_SELECTED)
        
        if self.cand_path:
            # File is loaded, update with translated format
            self.cand_label.setText(Strings.format_candidates_label(os.path.basename(self.cand_path)))
        else:
            # No file loaded, show not selected message
            self.cand_label.setText(Strings.LABEL_CANDIDATES_NOT_SELECTED)
        
        # Update language combo items
        current_index = self.language_combo.currentIndex()
        self.language_combo.blockSignals(True)
        self.language_combo.setItemText(0, t("lang_english"))
        self.language_combo.setItemText(1, t("lang_russian"))
        self.language_combo.blockSignals(False)
        
        # Update status labels - preserve their state but translate
        status_text = self.status_label.text()
        if status_text:
            # Try to detect which status it is by checking for processed count pattern
            if " / " in status_text or "/" in status_text:
                # Extract current and total from the status text if possible
                # This is tricky, so we'll just translate if we can detect it's a progress message
                # The worker thread will update it properly during processing
                pass
            elif "Processing" in status_text or "Обработка" in status_text or t("status_processing").lower() in status_text.lower():
                self.status_label.setText(Strings.STATUS_PROCESSING)
            elif "Results ready" in status_text or "Результаты готовы" in status_text or t("status_results_ready").lower() in status_text.lower():
                self.status_label.setText(Strings.STATUS_RESULTS_READY)
        
        # Update column combo boxes if files are loaded - refresh display names
        if self.ref_columns_raw:
            display_columns = [
                col if (col or "").strip()
                else t("column_no_header", index=i+1)
                for i, col in enumerate(self.ref_columns_raw)
            ]
            current_ref_index = self.ref_column_combo.currentIndex()
            self.ref_column_combo.blockSignals(True)
            self.ref_column_combo.clear()
            self.ref_column_combo.addItems(display_columns)
            if 0 <= current_ref_index < len(display_columns):
                self.ref_column_combo.setCurrentIndex(current_ref_index)
            self.ref_column_combo.blockSignals(False)
        
        if self.cand_columns_raw:
            display_columns = [
                col if (col or "").strip()
                else t("column_no_header", index=i+1)
                for i, col in enumerate(self.cand_columns_raw)
            ]
            current_cand_index = self.cand_column_combo.currentIndex()
            self.cand_column_combo.blockSignals(True)
            self.cand_column_combo.clear()
            self.cand_column_combo.addItems(display_columns)
            if 0 <= current_cand_index < len(display_columns):
                self.cand_column_combo.setCurrentIndex(current_cand_index)
            self.cand_column_combo.blockSignals(False)
        
        # Refresh column checkboxes if files are loaded
        if self.ref_columns_raw or self.cand_columns_raw:
            self._update_column_checkboxes()

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self._apply_theme()

    def _apply_theme(self):
        """Apply the current theme to all widgets."""
        theme = self.themes[self.current_theme]
        
        # Update theme button icon
        theme_icon = "☀️" if self.current_theme == "light" else "🌙"
        self.theme_button.setText(theme_icon)
        
        # Apply stylesheet to the application
        stylesheet = f"""
            QMainWindow {{
                background-color: {theme["bg"]};
                color: {theme["fg"]};
            }}
            
            QWidget {{
                background-color: {theme["bg"]};
                color: {theme["fg"]};
            }}
            
            QLabel {{
                padding: 10px;
                border-radius: 4px;
                background-color: {theme["bg"]};
                color: {theme["fg"]};
            }}
            
            QPushButton {{
                background-color: {theme["button_bg"]};
                color: {theme["button_fg"]};
                border: none;
                padding: 8px 15px;
                border-radius: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {theme["button_active"]};
            }}
            
            QPushButton:pressed {{
                background-color: {theme["button_active"]};
            }}
            
            QPushButton:disabled {{
                background-color: {theme["button_bg"]};
                color: {theme["text_secondary"]};
            }}
            
            QLineEdit {{
                background-color: {theme["entry_bg"]};
                color: {theme["fg"]};
                border: 1px solid {theme["scale_trough"]};
                border-radius: 3px;
                padding: 4px;
            }}
            
            QComboBox {{
                background-color: {theme["entry_bg"]};
                color: {theme["fg"]};
                border: 1px solid {theme["scale_trough"]};
                border-radius: 3px;
                padding: 4px;
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {theme["entry_bg"]};
                color: {theme["fg"]};
                selection-background-color: {theme["accent"]};
                selection-color: white;
            }}
            
            QSlider::groove:horizontal {{
                border: 1px solid {theme["scale_trough"]};
                height: 8px;
                background: {theme["scale_trough"]};
                border-radius: 4px;
            }}
            
            QSlider::handle:horizontal {{
                background: {theme["accent"]};
                border: 1px solid {theme["accent"]};
                width: 18px;
                margin: -2px 0;
                border-radius: 9px;
            }}
            
            QSlider::handle:horizontal:hover {{
                background: {theme["accent_active"]};
            }}
            
            QProgressBar {{
                border: 1px solid {theme["scale_trough"]};
                border-radius: 4px;
                text-align: center;
                background-color: {theme["scale_trough"]};
            }}
            
            QProgressBar::chunk {{
                background-color: {theme["accent"]};
                border-radius: 3px;
            }}
            
            QGroupBox {{
                border: 1px solid {theme["scale_trough"]};
                border-radius: 4px;
                margin-top: 10px;
                padding: 10px;
                background-color: {theme["groupbox_bg"]};
                color: {theme["fg"]};
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                border-radius: 4px;
                background-color: {theme["groupbox_bg"]};
            }}
            
            QCheckBox {{
                background-color: {theme["bg"]};
                color: {theme["fg"]};
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {theme["scale_trough"]};
                border-radius: 3px;
                background-color: {theme["bg"]};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {theme["accent"]};
                border-color: {theme["accent"]};
            }}
            
            QTabWidget::pane {{
                border: 1px solid {theme["scale_trough"]};
                background-color: {theme["bg"]};
            }}
            
            QTabBar::tab {{
                background-color: {theme["button_bg"]};
                color: {theme["fg"]};
                padding: 8px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            
            QTabBar::tab:selected {{
                background-color: {theme["bg"]};
                color: {theme["fg"]};
            }}
            
            QScrollArea {{
                border: none;
                background-color: {theme["bg"]};
            }}
            
            QScrollBar:vertical {{
                background-color: {theme["bg"]};
                width: 12px;
                border: none;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {theme["scale_trough"]};
                min-height: 20px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {theme["button_bg"]};
            }}
        """
        
        # Special styling for run button
        run_button_style = f"""
            QPushButton {{
                background-color: {theme["accent"]};
                color: white;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {theme["accent_active"]};
            }}
            
            QPushButton:pressed {{
                background-color: {theme["accent_active"]};
            }}
        """
        self.run_button.setStyleSheet(run_button_style)
        
        # Apply main stylesheet
        self.setStyleSheet(stylesheet)
        
        # Update specific labels with secondary text color
        self.ref_label.setStyleSheet(f"color: {theme['text_secondary']}; background-color: {theme['bg']};")
        self.cand_label.setStyleSheet(f"color: {theme['text_secondary']}; background-color: {theme['bg']};")
        self.status_label.setStyleSheet(f"color: {theme['text_secondary']}; background-color: {theme['bg']};")

    def _select_all_columns(self):
        """Select all column checkboxes."""
        for checkbox in self.column_checkboxes.values():
            checkbox.setChecked(True)

    def _select_none_columns(self):
        """Deselect all column checkboxes."""
        for checkbox in self.column_checkboxes.values():
            checkbox.setChecked(False)

    def _update_column_checkboxes(self):
        """Update the column checkboxes based on loaded files."""
        # Clear existing checkboxes
        while self.column_checkbox_layout.count():
            child = self.column_checkbox_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.column_checkboxes.clear()
        self.selected_ref_columns.clear()
        self.selected_cand_columns.clear()

        if not self.ref_columns_raw and not self.cand_columns_raw:
            no_file_label = QLabel(t("column_selection_no_files"))
            self.column_checkbox_layout.addWidget(no_file_label)
            return

        # Reference file columns section
        if self.ref_columns_raw:
            ref_label = QLabel(t("column_selection_ref_columns"))
            ref_font = QFont("Segoe UI", 10, QFont.Bold)
            ref_label.setFont(ref_font)
            self.column_checkbox_layout.addWidget(ref_label)

            for i, col in enumerate(self.ref_columns_raw):
                checkbox = QCheckBox()
                display_name = col if (col or "").strip() else t("column_no_header", index=i+1)
                checkbox.setText(display_name)
                key = f"ref_{col}"
                self.column_checkboxes[key] = checkbox
                checkbox.toggled.connect(lambda checked, c=col: self._on_ref_column_toggle(c, checked))
                self.column_checkbox_layout.addWidget(checkbox)

        # Candidate file columns section
        if self.cand_columns_raw:
            cand_label = QLabel(t("column_selection_cand_columns"))
            cand_font = QFont("Segoe UI", 10, QFont.Bold)
            cand_label.setFont(cand_font)
            self.column_checkbox_layout.addWidget(cand_label)

            for i, col in enumerate(self.cand_columns_raw):
                checkbox = QCheckBox()
                display_name = col if (col or "").strip() else t("column_no_header", index=i+1)
                checkbox.setText(display_name)
                key = f"cand_{col}"
                self.column_checkboxes[key] = checkbox
                checkbox.toggled.connect(lambda checked, c=col: self._on_cand_column_toggle(c, checked))
                self.column_checkbox_layout.addWidget(checkbox)

        self.column_checkbox_layout.addStretch()

    def _on_ref_column_toggle(self, column, checked):
        """Handle reference column checkbox toggle."""
        if checked:
            self.selected_ref_columns.add(column)
        else:
            self.selected_ref_columns.discard(column)

    def _on_cand_column_toggle(self, column, checked):
        """Handle candidate column checkbox toggle."""
        if checked:
            self.selected_cand_columns.add(column)
        else:
            self.selected_cand_columns.discard(column)

    def load_ref(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("dialog_select_reference"),
            "",
            f"{Strings.FILE_TYPE_CSV} ({Strings.FILE_EXTENSION_CSV})"
        )
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    columns = reader.fieldnames
                    if columns:
                        self.ref_path = path
                        self.ref_label.setText(Strings.format_reference_label(os.path.basename(path)))
                        # Update label color when file is loaded (from secondary to primary)
                        theme = self.themes[self.current_theme]
                        self.ref_label.setStyleSheet(f"color: {theme['fg']}; background-color: {theme['bg']};")
                        # Store raw headers and build user-friendly labels
                        self.ref_columns_raw = columns
                        display_columns = [
                            col if (col or "").strip()
                            else t("column_no_header", index=i+1)
                            for i, col in enumerate(columns)
                        ]
                        self.ref_column_combo.clear()
                        self.ref_column_combo.addItems(display_columns)
                        self.ref_column_combo.setCurrentIndex(0)
                        self.ref_column = self.ref_columns_raw[0]
                        
                        # Update column checkboxes
                        self._update_column_checkboxes()
                    else:
                        QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_NO_COLUMNS)
            except Exception as e:
                QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.format_read_error(str(e)))

    def load_cand(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            t("dialog_select_candidates"),
            "",
            f"{Strings.FILE_TYPE_CSV} ({Strings.FILE_EXTENSION_CSV})"
        )
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    columns = reader.fieldnames
                    if columns:
                        self.cand_path = path
                        self.cand_label.setText(Strings.format_candidates_label(os.path.basename(path)))
                        # Update label color when file is loaded (from secondary to primary)
                        theme = self.themes[self.current_theme]
                        self.cand_label.setStyleSheet(f"color: {theme['fg']}; background-color: {theme['bg']};")
                        # Store raw headers and build user-friendly labels
                        self.cand_columns_raw = columns
                        display_columns = [
                            col if (col or "").strip()
                            else t("column_no_header", index=i+1)
                            for i, col in enumerate(columns)
                        ]
                        self.cand_column_combo.clear()
                        self.cand_column_combo.addItems(display_columns)
                        self.cand_column_combo.setCurrentIndex(0)
                        self.cand_column = self.cand_columns_raw[0]
                        
                        # Update column checkboxes
                        self._update_column_checkboxes()
                    else:
                        QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_NO_COLUMNS)
            except Exception as e:
                QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.format_read_error(str(e)))

    def on_slider_change(self, value):
        """Update threshold entry when slider changes."""
        threshold = value / 100.0
        self.threshold_entry.setText(f"{threshold:.2f}")

    def on_entry_change(self):
        """Update threshold slider when entry changes."""
        try:
            value = float(self.threshold_entry.text())
            if 0.0 <= value <= 1.0:
                self.threshold_slider.setValue(int(value * 100))
            else:
                QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_THRESHOLD_RANGE)
                threshold = self.threshold_slider.value() / 100.0
                self.threshold_entry.setText(f"{threshold:.2f}")
        except ValueError:
            QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_INVALID_NUMBER)
            threshold = self.threshold_slider.value() / 100.0
            self.threshold_entry.setText(f"{threshold:.2f}")

    def on_ref_column_selected(self, index):
        """Update selected reference column using raw headers list."""
        if 0 <= index < len(self.ref_columns_raw):
            self.ref_column = self.ref_columns_raw[index]

    def on_cand_column_selected(self, index):
        """Update selected candidates column using raw headers list."""
        if 0 <= index < len(self.cand_columns_raw):
            self.cand_column = self.cand_columns_raw[index]

    def run(self):
        # Check if a worker is already running
        if self.matching_worker and self.matching_worker.isRunning():
            QMessageBox.warning(self, Strings.ERROR_TITLE, t("error_matching_in_progress"))
            return
        
        # Clean up any existing finished worker before creating a new one
        if self.matching_worker and not self.matching_worker.isRunning():
            self.matching_worker.deleteLater()
            self.matching_worker = None
            
        if not self.ref_path or not self.cand_path:
            QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_SELECT_BOTH_FILES)
            return

        ref_idx = self.ref_column_combo.currentIndex()
        cand_idx = self.cand_column_combo.currentIndex()

        if ref_idx == -1 or cand_idx == -1:
            QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_SELECT_COLUMNS)
            return

        # Map back from what user sees to actual raw CSV header (which can be empty).
        ref_col = self.ref_columns_raw[ref_idx]
        cand_col = self.cand_columns_raw[cand_idx]

        threshold = self.threshold_slider.value() / 100.0

        self.run_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.status_label.setText(Strings.STATUS_PROCESSING)
        # Update status label color based on theme
        theme = self.themes[self.current_theme]
        self.status_label.setStyleSheet(f"color: {theme['fg']}; background-color: {theme['bg']};")

        # Create and start worker thread
        self.matching_worker = CSVProcessor.create_worker(
            self.ref_path,
            self.cand_path,
            ref_col,
            cand_col,
            self.selected_ref_columns,
            self.selected_cand_columns,
            threshold,
            self.column_names
        )
        self.matching_worker.progress_updated.connect(self._update_progress)
        self.matching_worker.finished.connect(self._on_results_ready)
        self.matching_worker.error.connect(self._on_matching_error)
        self.matching_worker.start()

    def _update_progress(self, progress, current, total):
        """Update progress bar and status label."""
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(Strings.format_processed(current, total))
        # Update status label color based on theme
        theme = self.themes[self.current_theme]
        self.status_label.setStyleSheet(f"color: {theme['text_secondary']}; background-color: {theme['bg']};")

    def _on_results_ready(self, result_rows):
        """Called when matching is complete."""
        self._last_results = result_rows
        self.status_label.setText(Strings.STATUS_RESULTS_READY)
        # Update status label color based on theme
        theme = self.themes[self.current_theme]
        self.status_label.setStyleSheet(f"color: {theme['fg']}; background-color: {theme['bg']};")
        self.save_button.setEnabled(True)
        self.run_button.setEnabled(True)
        # Clean up worker thread properly
        if self.matching_worker:
            self.matching_worker.deleteLater()
            self.matching_worker = None

    def _on_matching_error(self, error_msg):
        """Handle errors from matching worker."""
        QMessageBox.critical(self, Strings.ERROR_TITLE, error_msg)
        # Clean up worker thread properly
        if self.matching_worker:
            self.matching_worker.deleteLater()
            self.matching_worker = None
        self._reset_ui()

    def save_results(self):
        """Let user choose where to save the last computed results."""
        if not self._last_results:
            QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_NO_RESULTS_TO_SAVE)
            return

        try:
            default_file = self.settings.default_result_file
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                t("dialog_save_results"),
                default_file,
                f"{Strings.FILE_TYPE_CSV} ({Strings.FILE_EXTENSION_CSV})"
            )

            if not save_path:
                # User cancelled; keep results in memory and UI state.
                return

            with open(save_path, "w", newline="", encoding="utf-8") as f:
                # Build fieldnames: selected columns first, then basic match columns
                fieldnames = []
                
                # Add selected reference columns in their original order
                if hasattr(self, 'ref_columns_raw') and self.ref_columns_raw:
                    for col in self.ref_columns_raw:
                        if col in self.selected_ref_columns:
                            fieldnames.append(col)
                
                # Add selected candidate columns in their original order
                if hasattr(self, 'cand_columns_raw') and self.cand_columns_raw:
                    for col in self.cand_columns_raw:
                        if col in self.selected_cand_columns and col not in fieldnames:
                            fieldnames.append(col)
                
                # Always add basic match columns at the end
                basic_columns = [
                    self.column_names.get("CSV_COLUMN_REFERENCE", "reference"),
                    self.column_names.get("CSV_COLUMN_BEST_MATCH", "best_match"),
                    self.column_names.get("CSV_COLUMN_SIMILARITY", "similarity")
                ]
                for col in basic_columns:
                    if col not in fieldnames:
                        fieldnames.append(col)
                
                writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                writer.writerows(self._last_results)

            QMessageBox.information(self, Strings.SUCCESS_TITLE, Strings.format_file_saved(save_path))
            self._reset_ui()

        except Exception as e:
            QMessageBox.critical(self, Strings.ERROR_TITLE, str(e))
            self._reset_ui()

    def _reset_ui(self):
        self.run_button.setEnabled(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("")
        # Update status label color based on theme
        theme = self.themes[self.current_theme]
        self.status_label.setStyleSheet(f"color: {theme['text_secondary']}; background-color: {theme['bg']};")
        self.save_button.setEnabled(False)
        self._last_results = None

    def closeEvent(self, event):
        """Handle window close event - ensure worker thread is cleaned up."""
        if self.matching_worker and self.matching_worker.isRunning():
            # Disconnect signals first to prevent any callbacks during shutdown
            try:
                self.matching_worker.progress_updated.disconnect()
                self.matching_worker.finished.disconnect()
                self.matching_worker.error.disconnect()
            except:
                pass  # Signals may already be disconnected
            
            # Request thread to stop
            self.matching_worker.requestInterruption()
            # Wait for thread to finish (with timeout)
            if not self.matching_worker.wait(5000):  # Wait up to 5 seconds
                # Force terminate if it doesn't stop gracefully
                self.matching_worker.terminate()
                self.matching_worker.wait(1000)  # Wait for termination
            
            # Clean up the worker
            self.matching_worker.deleteLater()
            self.matching_worker = None
        event.accept()
