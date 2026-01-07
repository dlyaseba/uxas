import csv
import os
import sys
from multiprocessing import Pool, cpu_count
import platform

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSlider, QLineEdit, QProgressBar,
    QTabWidget, QGroupBox, QCheckBox, QScrollArea, QFileDialog, QMessageBox,
    QFrame
)
from PySide6.QtCore import Qt, QThread, Signal, QCoreApplication
from PySide6.QtGui import QFont

from matcher import best_match
from strings import Strings


# Module-level function for multiprocessing (must be picklable)
def _process_single_match(args):
    """Process a single reference row with candidate rows."""
    ref_row, ref_col, selected_ref_cols, candidate_rows, cand_col, selected_cand_cols, threshold = args
    ref_name = ref_row.get(ref_col, "") or ""
    
    # Extract candidate names for matching
    candidate_names = [r.get(cand_col, "") or "" for r in candidate_rows]
    match, score = best_match(ref_name, candidate_names, threshold)
    
    # Start with basic match columns
    result = {
        Strings.CSV_COLUMN_REFERENCE: ref_name,
        Strings.CSV_COLUMN_BEST_MATCH: match,
        Strings.CSV_COLUMN_SIMILARITY: score
    }
    
    # Add selected columns from reference row
    for col in selected_ref_cols:
        if col in ref_row:
            result[col] = ref_row[col]
    
    # Add selected columns from matched candidate row
    if match:
        # Find the matched candidate row
        matched_row = None
        for cand_row in candidate_rows:
            if (cand_row.get(cand_col, "") or "") == match:
                matched_row = cand_row
                break
        
        if matched_row:
            for col in selected_cand_cols:
                if col in matched_row:
                    result[col] = matched_row[col]
    
    return result


class MatchingWorker(QThread):
    """Worker thread for running matching in background."""
    progress_updated = Signal(float, int, int)  # progress, current, total
    finished = Signal(list)  # result_rows
    error = Signal(str)
    
    def __init__(self, ref_path, cand_path, ref_col, cand_col, selected_ref_cols, selected_cand_cols, threshold):
        super().__init__()
        self.ref_path = ref_path
        self.cand_path = cand_path
        self.ref_col = ref_col
        self.cand_col = cand_col
        self.selected_ref_cols = selected_ref_cols
        self.selected_cand_cols = selected_cand_cols
        self.threshold = threshold
    
    def run(self):
        try:
            # Read all reference rows (to access all columns)
            with open(self.ref_path, encoding="utf-8") as f:
                reference_rows = list(csv.DictReader(f))

            # Read all candidate rows (to access all columns)
            with open(self.cand_path, encoding="utf-8") as f:
                candidate_rows = list(csv.DictReader(f))

            result_rows = []
            total = len(reference_rows)
            
            # Get selected columns (convert set to list for pickling)
            selected_ref_cols = list(self.selected_ref_cols)
            selected_cand_cols = list(self.selected_cand_cols)

            # Use parallel processing if we have multiple CPUs and multiple items
            num_workers = min(cpu_count(), 8)  # Cap at 8 to avoid overhead
            
            if num_workers > 1 and total > 1:
                try:
                    # Prepare arguments for parallel processing
                    args_list = [(ref_row, self.ref_col, selected_ref_cols, candidate_rows, self.cand_col, selected_cand_cols, self.threshold) 
                                for ref_row in reference_rows]
                    
                    # Process in parallel
                    with Pool(processes=num_workers) as pool:
                        results = pool.imap(_process_single_match, args_list)
                        
                        processed = 0
                        for result in results:
                            result_rows.append(result)
                            processed += 1
                            
                            # Update progress periodically for responsiveness
                            if processed % 10 == 0 or processed == total:
                                progress = (processed / total) * 100
                                self.progress_updated.emit(progress, processed, total)
                    
                    # Final progress update
                    self.progress_updated.emit(100, total, total)
                    self.finished.emit(result_rows)
                    return
                except Exception as e:
                    # Fallback to sequential processing if multiprocessing fails
                    pass

            # Sequential processing (fallback or for small datasets)
            candidate_names = [r.get(self.cand_col, "") or "" for r in candidate_rows]
            
            for idx, ref_row in enumerate(reference_rows):
                ref_name = ref_row.get(self.ref_col, "") or ""
                match, score = best_match(ref_name, candidate_names, self.threshold)
                
                # Start with basic match columns
                result = {
                    Strings.CSV_COLUMN_REFERENCE: ref_name,
                    Strings.CSV_COLUMN_BEST_MATCH: match,
                    Strings.CSV_COLUMN_SIMILARITY: score
                }
                
                # Add selected columns from reference row
                for col in selected_ref_cols:
                    if col in ref_row:
                        result[col] = ref_row[col]
                
                # Add selected columns from matched candidate row
                if match:
                    # Find the matched candidate row
                    matched_row = None
                    for cand_row in candidate_rows:
                        if (cand_row.get(self.cand_col, "") or "") == match:
                            matched_row = cand_row
                            break
                    
                    if matched_row:
                        for col in selected_cand_cols:
                            if col in matched_row:
                                result[col] = matched_row[col]
                
                result_rows.append(result)
                
                # Update progress
                if (idx + 1) % 10 == 0 or (idx + 1) == total:
                    progress = (idx + 1) / total * 100
                    self.progress_updated.emit(progress, idx + 1, total)

            # Hand over to main thread to notify user that results are ready.
            self.progress_updated.emit(100, total, total)
            self.finished.emit(result_rows)

        except Exception as e:
            self.error.emit(str(e))


class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(Strings.WINDOW_TITLE)
        self.setGeometry(100, 100, 700, 550)
        self.setMinimumSize(600, 450)

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

        # Header with title and theme switcher
        header_layout = QHBoxLayout()
        title_label = QLabel(Strings.WINDOW_TITLE)
        title_font = QFont("Segoe UI", 24, QFont.Bold)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        # Theme switcher button (placeholder for now - basic UI only)
        self.theme_button = QPushButton("🌙")
        self.theme_button.setMaximumWidth(50)
        self.theme_button.clicked.connect(self.toggle_theme)
        header_layout.addWidget(self.theme_button)
        main_layout.addLayout(header_layout)

        # Create tab widget
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        # Tab 1: Matching
        matching_tab = QWidget()
        matching_layout = QVBoxLayout(matching_tab)
        matching_layout.setContentsMargins(10, 10, 10, 10)
        self.tab_widget.addTab(matching_tab, "Matching")

        # Tab 2: Column Selection
        column_tab = QWidget()
        column_layout = QVBoxLayout(column_tab)
        column_layout.setContentsMargins(10, 10, 10, 10)
        self.tab_widget.addTab(column_tab, "Output Columns")

        # Setup Column Selection Tab UI
        self._setup_column_selection_tab(column_tab, column_layout)

        # Reference file section
        ref_group = QGroupBox(" Reference File ")
        ref_layout = QVBoxLayout(ref_group)

        ref_button_layout = QHBoxLayout()
        self.ref_button = QPushButton(Strings.BTN_SELECT_REFERENCE)
        self.ref_button.clicked.connect(self.load_ref)
        ref_button_layout.addWidget(self.ref_button)

        self.ref_label = QLabel(Strings.LABEL_REFERENCE_NOT_SELECTED)
        ref_button_layout.addWidget(self.ref_label, 1)
        ref_layout.addLayout(ref_button_layout)

        ref_column_layout = QHBoxLayout()
        ref_column_layout.addWidget(QLabel("Column:"))
        self.ref_column_combo = QComboBox()
        self.ref_column_combo.setEditable(False)
        self.ref_column_combo.currentIndexChanged.connect(self.on_ref_column_selected)
        ref_column_layout.addWidget(self.ref_column_combo)
        ref_layout.addLayout(ref_column_layout)

        matching_layout.addWidget(ref_group)

        # Candidates file section
        cand_group = QGroupBox(" Candidates File ")
        cand_layout = QVBoxLayout(cand_group)

        cand_button_layout = QHBoxLayout()
        self.cand_button = QPushButton(Strings.BTN_SELECT_CANDIDATES)
        self.cand_button.clicked.connect(self.load_cand)
        cand_button_layout.addWidget(self.cand_button)

        self.cand_label = QLabel(Strings.LABEL_CANDIDATES_NOT_SELECTED)
        cand_button_layout.addWidget(self.cand_label, 1)
        cand_layout.addLayout(cand_button_layout)

        cand_column_layout = QHBoxLayout()
        cand_column_layout.addWidget(QLabel("Column:"))
        self.cand_column_combo = QComboBox()
        self.cand_column_combo.setEditable(False)
        self.cand_column_combo.currentIndexChanged.connect(self.on_cand_column_selected)
        cand_column_layout.addWidget(self.cand_column_combo)
        cand_layout.addLayout(cand_column_layout)

        matching_layout.addWidget(cand_group)

        # Threshold section
        threshold_group = QGroupBox(" Similarity Threshold ")
        threshold_layout = QVBoxLayout(threshold_group)

        threshold_controls = QHBoxLayout()
        threshold_controls.addWidget(QLabel(Strings.LABEL_THRESHOLD))

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(80)
        self.threshold_slider.valueChanged.connect(self.on_slider_change)
        threshold_controls.addWidget(self.threshold_slider)

        self.threshold_entry = QLineEdit()
        self.threshold_entry.setText("0.80")
        self.threshold_entry.setMaximumWidth(60)
        self.threshold_entry.returnPressed.connect(self.on_entry_change)
        self.threshold_entry.editingFinished.connect(self.on_entry_change)
        threshold_controls.addWidget(self.threshold_entry)

        threshold_layout.addLayout(threshold_controls)
        matching_layout.addWidget(threshold_group)

        # Action buttons
        action_layout = QHBoxLayout()
        self.run_button = QPushButton(Strings.BTN_RUN)
        self.run_button.clicked.connect(self.run)
        action_layout.addWidget(self.run_button)

        self.save_button = QPushButton(Strings.BTN_SAVE_RESULTS)
        self.save_button.clicked.connect(self.save_results)
        self.save_button.setEnabled(False)
        action_layout.addWidget(self.save_button)
        matching_layout.addLayout(action_layout)

        # Progress section
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        matching_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("")
        matching_layout.addWidget(self.status_label)

        matching_layout.addStretch()

    def _setup_column_selection_tab(self, tab, layout):
        """Setup the column selection tab with checkboxes."""
        info_label = QLabel("Select additional columns from reference and candidate files to include in the output CSV.\nThe basic columns (reference, best_match, similarity) are always included.")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Create scrollable area for checkboxes
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.column_checkbox_widget = QWidget()
        self.column_checkbox_layout = QVBoxLayout(self.column_checkbox_widget)
        scroll_area.setWidget(self.column_checkbox_widget)
        layout.addWidget(scroll_area)

        # Buttons for select all/none
        button_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all_columns)
        button_layout.addWidget(select_all_btn)

        select_none_btn = QPushButton("Select None")
        select_none_btn.clicked.connect(self._select_none_columns)
        button_layout.addWidget(select_none_btn)
        layout.addLayout(button_layout)

    def toggle_theme(self):
        """Toggle between light and dark themes - placeholder for now."""
        pass

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
            no_file_label = QLabel("No files loaded. Please load reference and candidate files first.")
            self.column_checkbox_layout.addWidget(no_file_label)
            return

        # Reference file columns section
        if self.ref_columns_raw:
            ref_label = QLabel("Reference File Columns:")
            ref_font = QFont("Segoe UI", 10, QFont.Bold)
            ref_label.setFont(ref_font)
            self.column_checkbox_layout.addWidget(ref_label)

            for i, col in enumerate(self.ref_columns_raw):
                checkbox = QCheckBox()
                display_name = col if (col or "").strip() else f"Column {i+1} (no header)"
                checkbox.setText(display_name)
                key = f"ref_{col}"
                self.column_checkboxes[key] = checkbox
                checkbox.toggled.connect(lambda checked, c=col: self._on_ref_column_toggle(c, checked))
                self.column_checkbox_layout.addWidget(checkbox)

        # Candidate file columns section
        if self.cand_columns_raw:
            cand_label = QLabel("Candidate File Columns:")
            cand_font = QFont("Segoe UI", 10, QFont.Bold)
            cand_label.setFont(cand_font)
            self.column_checkbox_layout.addWidget(cand_label)

            for i, col in enumerate(self.cand_columns_raw):
                checkbox = QCheckBox()
                display_name = col if (col or "").strip() else f"Column {i+1} (no header)"
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
            "Select Reference File",
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
                        # Store raw headers and build user-friendly labels
                        self.ref_columns_raw = columns
                        display_columns = [
                            col if (col or "").strip()
                            else f"Column {i+1} (no header)"
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
            "Select Candidates File",
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
                        # Store raw headers and build user-friendly labels
                        self.cand_columns_raw = columns
                        display_columns = [
                            col if (col or "").strip()
                            else f"Column {i+1} (no header)"
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

        # Create and start worker thread
        self.matching_worker = MatchingWorker(
            self.ref_path,
            self.cand_path,
            ref_col,
            cand_col,
            self.selected_ref_columns,
            self.selected_cand_columns,
            threshold
        )
        self.matching_worker.progress_updated.connect(self._update_progress)
        self.matching_worker.finished.connect(self._on_results_ready)
        self.matching_worker.error.connect(self._on_matching_error)
        self.matching_worker.start()

    def _update_progress(self, progress, current, total):
        """Update progress bar and status label."""
        self.progress_bar.setValue(int(progress))
        self.status_label.setText(Strings.format_processed(current, total))

    def _on_results_ready(self, result_rows):
        """Called when matching is complete."""
        self._last_results = result_rows
        self.status_label.setText(Strings.STATUS_RESULTS_READY)
        self.save_button.setEnabled(True)
        self.run_button.setEnabled(True)
        self.matching_worker = None

    def _on_matching_error(self, error_msg):
        """Handle errors from matching worker."""
        QMessageBox.critical(self, Strings.ERROR_TITLE, error_msg)
        self._reset_ui()

    def save_results(self):
        """Let user choose where to save the last computed results."""
        if not self._last_results:
            QMessageBox.critical(self, Strings.ERROR_TITLE, Strings.ERROR_NO_RESULTS_TO_SAVE)
            return

        try:
            save_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save Results",
                Strings.DEFAULT_RESULT_FILE,
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
                basic_columns = [Strings.CSV_COLUMN_REFERENCE, Strings.CSV_COLUMN_BEST_MATCH, Strings.CSV_COLUMN_SIMILARITY]
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
        self.save_button.setEnabled(False)
        self._last_results = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
