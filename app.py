import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from multiprocessing import Pool, cpu_count
import platform

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


class App:
    def __init__(self, root):
        self.root = root
        root.title(Strings.WINDOW_TITLE)
        root.geometry("700x550")
        root.minsize(600, 450)

        # Theme management
        self.current_theme = self._detect_system_theme()
        self._setup_themes()

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

        # Create main container with padding
        main_container = ttk.Frame(root, padding="20")
        main_container.pack(fill=tk.BOTH, expand=True)

        # Header with title and theme switcher
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        title_label = tk.Label(
            header_frame, 
            text=Strings.WINDOW_TITLE, 
            font=("Segoe UI", 24, "bold"),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"]
        )
        title_label.pack(side=tk.LEFT)

        # Theme switcher button
        theme_icon = "🌙" if self.current_theme == "light" else "☀️"
        self.theme_button = tk.Button(
            header_frame,
            text=theme_icon,
            command=self.toggle_theme,
            font=("Segoe UI", 14),
            bg=self.themes[self.current_theme]["button_bg"],
            fg=self.themes[self.current_theme]["button_fg"],
            activebackground=self.themes[self.current_theme]["button_active"],
            activeforeground=self.themes[self.current_theme]["button_fg"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=10,
            pady=5
        )
        self.theme_button.pack(side=tk.RIGHT)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Tab 1: Matching
        matching_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(matching_tab, text="Matching")

        # Tab 2: Column Selection
        column_tab = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(column_tab, text="Output Columns")

        # Reference file section
        ref_section = ttk.LabelFrame(matching_tab, text=" Reference File ", padding="15")
        ref_section.pack(fill=tk.X, pady=(0, 15))
        
        # Setup Column Selection Tab UI
        self._setup_column_selection_tab(column_tab)

        ref_button_frame = ttk.Frame(ref_section)
        ref_button_frame.pack(fill=tk.X, pady=(0, 10))

        self.ref_button = tk.Button(
            ref_button_frame,
            text=Strings.BTN_SELECT_REFERENCE,
            command=self.load_ref,
            font=("Segoe UI", 10),
            bg=self.themes[self.current_theme]["button_bg"],
            fg=self.themes[self.current_theme]["button_fg"],
            activebackground=self.themes[self.current_theme]["button_active"],
            activeforeground=self.themes[self.current_theme]["button_fg"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        self.ref_button.pack(side=tk.LEFT, padx=(0, 15))

        self.ref_label = tk.Label(
            ref_button_frame,
            text=Strings.LABEL_REFERENCE_NOT_SELECTED,
            font=("Segoe UI", 9),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["text_secondary"],
            wraplength=300,
            justify=tk.LEFT
        )
        self.ref_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ref_column_frame = ttk.Frame(ref_section)
        ref_column_frame.pack(fill=tk.X)
        ttk.Label(ref_column_frame, text="Column:").pack(side=tk.LEFT, padx=(0, 10))
        self.ref_column_combo = ttk.Combobox(ref_column_frame, state="readonly", width=30)
        self.ref_column_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.ref_column_combo.bind("<<ComboboxSelected>>", self.on_ref_column_selected)

        # Candidates file section
        cand_section = ttk.LabelFrame(matching_tab, text=" Candidates File ", padding="15")
        cand_section.pack(fill=tk.X, pady=(0, 15))

        cand_button_frame = ttk.Frame(cand_section)
        cand_button_frame.pack(fill=tk.X, pady=(0, 10))

        self.cand_button = tk.Button(
            cand_button_frame,
            text=Strings.BTN_SELECT_CANDIDATES,
            command=self.load_cand,
            font=("Segoe UI", 10),
            bg=self.themes[self.current_theme]["button_bg"],
            fg=self.themes[self.current_theme]["button_fg"],
            activebackground=self.themes[self.current_theme]["button_active"],
            activeforeground=self.themes[self.current_theme]["button_fg"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=20,
            pady=8
        )
        self.cand_button.pack(side=tk.LEFT, padx=(0, 15))

        self.cand_label = tk.Label(
            cand_button_frame,
            text=Strings.LABEL_CANDIDATES_NOT_SELECTED,
            font=("Segoe UI", 9),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["text_secondary"],
            wraplength=300,
            justify=tk.LEFT
        )
        self.cand_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        cand_column_frame = ttk.Frame(cand_section)
        cand_column_frame.pack(fill=tk.X)
        ttk.Label(cand_column_frame, text="Column:").pack(side=tk.LEFT, padx=(0, 10))
        self.cand_column_combo = ttk.Combobox(cand_column_frame, state="readonly", width=30)
        self.cand_column_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.cand_column_combo.bind("<<ComboboxSelected>>", self.on_cand_column_selected)

        # Threshold section
        threshold_section = ttk.LabelFrame(matching_tab, text=" Similarity Threshold ", padding="15")
        threshold_section.pack(fill=tk.X, pady=(0, 15))

        threshold_controls = ttk.Frame(threshold_section)
        threshold_controls.pack(fill=tk.X)

        ttk.Label(threshold_controls, text=Strings.LABEL_THRESHOLD, font=("Segoe UI", 10)).pack(side=tk.LEFT, padx=(0, 15))

        self.threshold_var = tk.DoubleVar(value=0.8)
        self.threshold_scale = tk.Scale(
            threshold_controls,
            from_=0.0,
            to=1.0,
            resolution=0.01,
            orient=tk.HORIZONTAL,
            variable=self.threshold_var,
            length=300,
            command=self.on_scale_change,
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"],
            highlightbackground=self.themes[self.current_theme]["bg"],
            troughcolor=self.themes[self.current_theme]["scale_trough"],
            activebackground=self.themes[self.current_theme]["accent"]
        )
        self.threshold_scale.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        self.threshold_entry = tk.Entry(
            threshold_controls,
            width=6,
            font=("Segoe UI", 10),
            bg=self.themes[self.current_theme]["entry_bg"],
            fg=self.themes[self.current_theme]["fg"],
            insertbackground=self.themes[self.current_theme]["fg"],
            relief=tk.FLAT,
            borderwidth=1
        )
        self.threshold_entry.pack(side=tk.LEFT)
        self.threshold_entry.insert(0, "0.80")
        self.threshold_entry.bind("<Return>", self.on_entry_change)
        self.threshold_entry.bind("<FocusOut>", self.on_entry_change)

        # Action buttons
        action_frame = ttk.Frame(matching_tab)
        action_frame.pack(fill=tk.X, pady=(0, 15))

        self.run_button = tk.Button(
            action_frame,
            text=Strings.BTN_RUN,
            command=self.run,
            font=("Segoe UI", 11, "bold"),
            bg=self.themes[self.current_theme]["accent"],
            fg="white",
            activebackground=self.themes[self.current_theme]["accent_active"],
            activeforeground="white",
            relief=tk.FLAT,
            cursor="hand2",
            padx=30,
            pady=12
        )
        self.run_button.pack(side=tk.LEFT, padx=(0, 10))

        self.save_button = tk.Button(
            action_frame,
            text=Strings.BTN_SAVE_RESULTS,
            command=self.save_results,
            state="disabled",
            font=("Segoe UI", 11),
            bg=self.themes[self.current_theme]["button_bg"],
            fg=self.themes[self.current_theme]["button_fg"],
            activebackground=self.themes[self.current_theme]["button_active"],
            activeforeground=self.themes[self.current_theme]["button_fg"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=30,
            pady=12
        )
        self.save_button.pack(side=tk.LEFT)

        # Progress section
        progress_frame = ttk.Frame(matching_tab)
        progress_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            progress_frame,
            variable=self.progress_var,
            maximum=100,
            length=400,
            mode='determinate'
        )
        self.progress_bar.pack(fill=tk.X, pady=(0, 10))

        self.status_label = tk.Label(
            progress_frame,
            text="",
            font=("Segoe UI", 9),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["text_secondary"]
        )
        self.status_label.pack()

        # Apply theme to root window
        root.configure(bg=self.themes[self.current_theme]["bg"])
        
        # Apply initial theme
        self._apply_theme()

    def _detect_system_theme(self):
        """Detect system theme preference."""
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
        except:
            pass
        # Default to light theme if detection fails
        return "light"

    def _setup_themes(self):
        """Setup light and dark theme color schemes."""
        self.themes = {
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
            }
        }

        # Configure ttk styles
        style = ttk.Style()
        style.theme_use('clam')

        # Light theme styles
        style.configure("TLabelframe", background="#F5F5F5", foreground="#1E1E1E", borderwidth=1)
        style.configure("TLabelframe.Label", background="#F5F5F5", foreground="#1E1E1E", font=("Segoe UI", 9, "bold"))
        style.configure("TFrame", background="#F5F5F5")
        style.configure("TLabel", background="#F5F5F5", foreground="#1E1E1E", font=("Segoe UI", 9))
        style.configure("TCombobox", fieldbackground="#FFFFFF", foreground="#1E1E1E")
        style.configure("TProgressbar", background="#0078D4", troughcolor="#E0E0E0")

        # Dark theme styles (will be applied when needed)
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#2D2D2D")],
                  foreground=[("readonly", "#FFFFFF")])

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self._apply_theme()

    def _apply_theme(self):
        """Apply the current theme to all widgets."""
        theme = self.themes[self.current_theme]
        
        # Update root window
        self.root.configure(bg=theme["bg"])
        
        # Update all labels
        for widget in self.root.winfo_children():
            self._apply_theme_recursive(widget, theme)
        
        # Update theme button icon
        theme_icon = "☀️" if self.current_theme == "light" else "🌙"
        self.theme_button.config(
            text=theme_icon,
            bg=theme["button_bg"],
            fg=theme["button_fg"],
            activebackground=theme["button_active"]
        )

        # Update ttk styles
        style = ttk.Style()
        if self.current_theme == "dark":
            style.configure("TLabelframe", background="#2D2D2D", foreground="#FFFFFF")
            style.configure("TLabelframe.Label", background="#2D2D2D", foreground="#FFFFFF")
            style.configure("TFrame", background="#2D2D2D")
            style.configure("TLabel", background="#2D2D2D", foreground="#FFFFFF")
            style.configure("TCombobox", fieldbackground="#2D2D2D", foreground="#FFFFFF")
            style.map("TCombobox",
                     fieldbackground=[("readonly", "#2D2D2D")],
                     foreground=[("readonly", "#FFFFFF")])
        else:
            style.configure("TLabelframe", background="#F5F5F5", foreground="#1E1E1E")
            style.configure("TLabelframe.Label", background="#F5F5F5", foreground="#1E1E1E")
            style.configure("TFrame", background="#F5F5F5")
            style.configure("TLabel", background="#F5F5F5", foreground="#1E1E1E")
            style.configure("TCombobox", fieldbackground="#FFFFFF", foreground="#1E1E1E")
            style.map("TCombobox",
                     fieldbackground=[("readonly", "#FFFFFF")],
                     foreground=[("readonly", "#1E1E1E")])

    def _apply_theme_recursive(self, widget, theme):
        """Recursively apply theme to widget and its children."""
        try:
            widget_type = widget.winfo_class()
            
            if widget_type == "Label":
                # Skip title label and status label - they're handled separately
                if widget not in [self.status_label] and not hasattr(widget, '_skip_theme'):
                    text = widget.cget("text") if hasattr(widget, "cget") else ""
                    if text != Strings.WINDOW_TITLE:
                        # Check if it's a secondary text label
                        if widget in [self.ref_label, self.cand_label]:
                            widget.config(
                                bg=theme["bg"],
                                fg=theme["text_secondary"]
                            )
                        else:
                            widget.config(
                                bg=theme["bg"],
                                fg=theme["fg"]
                            )
            elif widget_type == "Button":
                if widget not in [self.theme_button]:  # Theme button is handled separately
                    if widget == self.run_button:
                        widget.config(
                            bg=theme["accent"],
                            activebackground=theme["accent_active"]
                        )
                    elif widget in [self.ref_button, self.cand_button, self.save_button]:
                        widget.config(
                            bg=theme["button_bg"],
                            fg=theme["button_fg"],
                            activebackground=theme["button_active"],
                            activeforeground=theme["button_fg"]
                        )
            elif widget_type == "Entry":
                widget.config(
                    bg=theme["entry_bg"],
                    fg=theme["fg"],
                    insertbackground=theme["fg"]
                )
            elif widget_type == "Scale":
                widget.config(
                    bg=theme["bg"],
                    fg=theme["fg"],
                    highlightbackground=theme["bg"],
                    troughcolor=theme["scale_trough"],
                    activebackground=theme["accent"]
                )
            elif widget_type == "Checkbutton":
                widget.config(
                    bg=theme["bg"],
                    fg=theme["fg"],
                    selectcolor=theme["bg"],
                    activebackground=theme["bg"],
                    activeforeground=theme["fg"]
                )
            elif widget_type == "Canvas":
                widget.config(bg=theme["bg"])
            
            # Recursively apply to children
            for child in widget.winfo_children():
                try:
                    self._apply_theme_recursive(child, theme)
                except:
                    pass
        except:
            pass

    def _setup_column_selection_tab(self, tab):
        """Setup the column selection tab with checkboxes."""
        info_label = tk.Label(
            tab,
            text="Select additional columns from reference and candidate files to include in the output CSV.\nThe basic columns (reference, best_match, similarity) are always included.",
            font=("Segoe UI", 9),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["text_secondary"],
            justify=tk.LEFT,
            wraplength=600
        )
        info_label.pack(anchor=tk.W, pady=(0, 15))

        # Create scrollable frame for checkboxes
        canvas_frame = ttk.Frame(tab)
        canvas_frame.pack(fill=tk.BOTH, expand=True)

        canvas = tk.Canvas(
            canvas_frame,
            bg=self.themes[self.current_theme]["bg"],
            highlightthickness=0
        )
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        self.column_checkbox_frame = ttk.Frame(canvas)

        self.column_checkbox_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.column_checkbox_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind mouse wheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Buttons for select all/none
        button_frame = ttk.Frame(tab)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        select_all_btn = tk.Button(
            button_frame,
            text="Select All",
            command=self._select_all_columns,
            font=("Segoe UI", 9),
            bg=self.themes[self.current_theme]["button_bg"],
            fg=self.themes[self.current_theme]["button_fg"],
            activebackground=self.themes[self.current_theme]["button_active"],
            activeforeground=self.themes[self.current_theme]["button_fg"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=5
        )
        select_all_btn.pack(side=tk.LEFT, padx=(0, 10))

        select_none_btn = tk.Button(
            button_frame,
            text="Select None",
            command=self._select_none_columns,
            font=("Segoe UI", 9),
            bg=self.themes[self.current_theme]["button_bg"],
            fg=self.themes[self.current_theme]["button_fg"],
            activebackground=self.themes[self.current_theme]["button_active"],
            activeforeground=self.themes[self.current_theme]["button_fg"],
            relief=tk.FLAT,
            cursor="hand2",
            padx=15,
            pady=5
        )
        select_none_btn.pack(side=tk.LEFT)

    def _select_all_columns(self):
        """Select all column checkboxes."""
        for var in self.column_checkboxes.values():
            var.set(True)

    def _select_none_columns(self):
        """Deselect all column checkboxes."""
        for var in self.column_checkboxes.values():
            var.set(False)

    def _update_column_checkboxes(self):
        """Update the column checkboxes based on loaded files."""
        # Clear existing checkboxes
        for widget in self.column_checkbox_frame.winfo_children():
            widget.destroy()
        self.column_checkboxes.clear()
        self.selected_ref_columns.clear()
        self.selected_cand_columns.clear()

        if not self.ref_columns_raw and not self.cand_columns_raw:
            no_file_label = tk.Label(
                self.column_checkbox_frame,
                text="No files loaded. Please load reference and candidate files first.",
                font=("Segoe UI", 9),
                bg=self.themes[self.current_theme]["bg"],
                fg=self.themes[self.current_theme]["text_secondary"]
            )
            no_file_label.pack(anchor=tk.W, pady=10)
            return

        # Reference file columns section
        if self.ref_columns_raw:
            ref_label = tk.Label(
                self.column_checkbox_frame,
                text="Reference File Columns:",
                font=("Segoe UI", 10, "bold"),
                bg=self.themes[self.current_theme]["bg"],
                fg=self.themes[self.current_theme]["fg"]
            )
            ref_label.pack(anchor=tk.W, pady=(10, 5), padx=5)

            for i, col in enumerate(self.ref_columns_raw):
                var = tk.BooleanVar()
                key = f"ref_{col}"  # Prefix to distinguish from candidate columns
                self.column_checkboxes[key] = var

                # Create display name (same as in combobox)
                display_name = col if (col or "").strip() else f"Column {i+1} (no header)"

                checkbox = tk.Checkbutton(
                    self.column_checkbox_frame,
                    text=display_name,
                    variable=var,
                    command=lambda c=col, v=var: self._on_ref_column_toggle(c, v),
                    font=("Segoe UI", 9),
                    bg=self.themes[self.current_theme]["bg"],
                    fg=self.themes[self.current_theme]["fg"],
                    selectcolor=self.themes[self.current_theme]["bg"],
                    activebackground=self.themes[self.current_theme]["bg"],
                    activeforeground=self.themes[self.current_theme]["fg"]
                )
                checkbox.pack(anchor=tk.W, pady=2, padx=15)

        # Candidate file columns section
        if self.cand_columns_raw:
            cand_label = tk.Label(
                self.column_checkbox_frame,
                text="Candidate File Columns:",
                font=("Segoe UI", 10, "bold"),
                bg=self.themes[self.current_theme]["bg"],
                fg=self.themes[self.current_theme]["fg"]
            )
            cand_label.pack(anchor=tk.W, pady=(15, 5), padx=5)

            for i, col in enumerate(self.cand_columns_raw):
                var = tk.BooleanVar()
                key = f"cand_{col}"  # Prefix to distinguish from reference columns
                self.column_checkboxes[key] = var

                # Create display name (same as in combobox)
                display_name = col if (col or "").strip() else f"Column {i+1} (no header)"

                checkbox = tk.Checkbutton(
                    self.column_checkbox_frame,
                    text=display_name,
                    variable=var,
                    command=lambda c=col, v=var: self._on_cand_column_toggle(c, v),
                    font=("Segoe UI", 9),
                    bg=self.themes[self.current_theme]["bg"],
                    fg=self.themes[self.current_theme]["fg"],
                    selectcolor=self.themes[self.current_theme]["bg"],
                    activebackground=self.themes[self.current_theme]["bg"],
                    activeforeground=self.themes[self.current_theme]["fg"]
                )
                checkbox.pack(anchor=tk.W, pady=2, padx=15)

    def _on_ref_column_toggle(self, column, var):
        """Handle reference column checkbox toggle."""
        if var.get():
            self.selected_ref_columns.add(column)
        else:
            self.selected_ref_columns.discard(column)

    def _on_cand_column_toggle(self, column, var):
        """Handle candidate column checkbox toggle."""
        if var.get():
            self.selected_cand_columns.add(column)
        else:
            self.selected_cand_columns.discard(column)

    def load_ref(self):
        path = filedialog.askopenfilename(filetypes=[(Strings.FILE_TYPE_CSV, Strings.FILE_EXTENSION_CSV)])
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    columns = reader.fieldnames
                    if columns:
                        self.ref_path = path
                        self.ref_label.config(
                            text=Strings.format_reference_label(os.path.basename(path)),
                            fg=self.themes[self.current_theme]["fg"]
                        )
                        # Store raw headers and build user-friendly labels so
                        # "invisible" empty headers become visible in the UI.
                        self.ref_columns_raw = columns
                        display_columns = [
                            col if (col or "").strip()
                            else f"Column {i+1} (no header)"
                            for i, col in enumerate(columns)
                        ]
                        self.ref_column_combo["values"] = display_columns
                        self.ref_column_combo.current(0)
                        self.ref_column = self.ref_columns_raw[0]
                        
                        # Update column checkboxes
                        self._update_column_checkboxes()
                    else:
                        messagebox.showerror(Strings.ERROR_TITLE, Strings.ERROR_NO_COLUMNS)
            except Exception as e:
                messagebox.showerror(Strings.ERROR_TITLE, Strings.format_read_error(str(e)))

    def load_cand(self):
        path = filedialog.askopenfilename(filetypes=[(Strings.FILE_TYPE_CSV, Strings.FILE_EXTENSION_CSV)])
        if path:
            try:
                with open(path, encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    columns = reader.fieldnames
                    if columns:
                        self.cand_path = path
                        self.cand_label.config(
                            text=Strings.format_candidates_label(os.path.basename(path)),
                            fg=self.themes[self.current_theme]["fg"]
                        )
                        # Same idea as for reference: show placeholders for empty headers.
                        self.cand_columns_raw = columns
                        display_columns = [
                            col if (col or "").strip()
                            else f"Column {i+1} (no header)"
                            for i, col in enumerate(columns)
                        ]
                        self.cand_column_combo["values"] = display_columns
                        self.cand_column_combo.current(0)
                        self.cand_column = self.cand_columns_raw[0]
                        
                        # Update column checkboxes
                        self._update_column_checkboxes()
                    else:
                        messagebox.showerror(Strings.ERROR_TITLE, Strings.ERROR_NO_COLUMNS)
            except Exception as e:
                messagebox.showerror(Strings.ERROR_TITLE, Strings.format_read_error(str(e)))

    def on_scale_change(self, value):
        self.threshold_entry.delete(0, tk.END)
        self.threshold_entry.insert(0, f"{float(value):.2f}")

    def on_entry_change(self, event=None):
        try:
            value = float(self.threshold_entry.get())
            if 0.0 <= value <= 1.0:
                self.threshold_var.set(value)
            else:
                messagebox.showerror(Strings.ERROR_TITLE, Strings.ERROR_THRESHOLD_RANGE)
                self.threshold_entry.delete(0, tk.END)
                self.threshold_entry.insert(0, f"{self.threshold_var.get():.2f}")
        except ValueError:
            messagebox.showerror(Strings.ERROR_TITLE, Strings.ERROR_INVALID_NUMBER)
            self.threshold_entry.delete(0, tk.END)
            self.threshold_entry.insert(0, f"{self.threshold_var.get():.2f}")

    def on_ref_column_selected(self, event=None):
        """Update selected reference column using raw headers list."""
        idx = self.ref_column_combo.current()
        if 0 <= idx < len(self.ref_columns_raw):
            self.ref_column = self.ref_columns_raw[idx]

    def on_cand_column_selected(self, event=None):
        """Update selected candidates column using raw headers list."""
        idx = self.cand_column_combo.current()
        if 0 <= idx < len(self.cand_columns_raw):
            self.cand_column = self.cand_columns_raw[idx]

    def run(self):
        if not self.ref_path or not self.cand_path:
            messagebox.showerror(Strings.ERROR_TITLE, Strings.ERROR_SELECT_BOTH_FILES)
            return

        ref_idx = self.ref_column_combo.current()
        cand_idx = self.cand_column_combo.current()

        if ref_idx == -1 or cand_idx == -1:
            messagebox.showerror(Strings.ERROR_TITLE, Strings.ERROR_SELECT_COLUMNS)
            return

        # Map back from what user sees to actual raw CSV header (which can be empty).
        ref_col = self.ref_columns_raw[ref_idx]
        cand_col = self.cand_columns_raw[cand_idx]

        self.run_button.config(state="disabled")
        self.progress_var.set(0)
        self.status_label.config(
            text=Strings.STATUS_PROCESSING,
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"]
        )
        self.root.update()

        thread = threading.Thread(target=self._run_matching, args=(ref_col, cand_col))
        thread.daemon = True
        thread.start()

    def _run_matching(self, ref_col, cand_col):
        try:
            # Read all reference rows (to access all columns)
            with open(self.ref_path, encoding="utf-8") as f:
                reference_rows = list(csv.DictReader(f))

            # Read all candidate rows (to access all columns)
            with open(self.cand_path, encoding="utf-8") as f:
                candidate_rows = list(csv.DictReader(f))

            result_rows = []
            threshold = self.threshold_var.get()
            total = len(reference_rows)
            
            # Get selected columns (convert set to list for pickling)
            selected_ref_cols = list(self.selected_ref_columns)
            selected_cand_cols = list(self.selected_cand_columns)

            # Use parallel processing if we have multiple CPUs and multiple items
            num_workers = min(cpu_count(), 8)  # Cap at 8 to avoid overhead
            
            if num_workers > 1 and total > 1:
                try:
                    # Prepare arguments for parallel processing
                    args_list = [(ref_row, ref_col, selected_ref_cols, candidate_rows, cand_col, selected_cand_cols, threshold) 
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
                                self.root.after(0, self._update_progress, progress, processed, total)
                    
                    # Final progress update
                    self.root.after(0, self._update_progress, 100, total, total)
                    self.root.after(0, self._on_results_ready, result_rows)
                    return
                except Exception:
                    # Fallback to sequential processing if multiprocessing fails
                    pass

            # Sequential processing (fallback or for small datasets)
            candidate_names = [r.get(cand_col, "") or "" for r in candidate_rows]
            
            for idx, ref_row in enumerate(reference_rows):
                ref_name = ref_row.get(ref_col, "") or ""
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
                
                result_rows.append(result)
                
                # Update progress
                if (idx + 1) % 10 == 0 or (idx + 1) == total:
                    progress = (idx + 1) / total * 100
                    self.root.after(0, self._update_progress, progress, idx + 1, total)

            # Hand over to main thread to notify user that results are ready.
            self.root.after(0, self._update_progress, 100, total, total)
            self.root.after(0, self._on_results_ready, result_rows)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(Strings.ERROR_TITLE, str(e)))
            self.root.after(0, self._reset_ui)
    
    def _update_progress(self, progress, current, total):
        """Update progress bar and status label (called from main thread)."""
        self.progress_var.set(progress)
        self.status_label.config(
            text=Strings.format_processed(current, total),
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["text_secondary"]
        )
        self.root.update_idletasks()

    def _on_results_ready(self, result_rows):
        """Called on main thread when matching is complete."""
        self._last_results = result_rows
        self.status_label.config(
            text=Strings.STATUS_RESULTS_READY,
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["fg"]
        )
        self.save_button.config(state="normal")
        self.run_button.config(state="normal")

    def save_results(self):
        """Let user choose where to save the last computed results."""
        if not self._last_results:
            messagebox.showerror(Strings.ERROR_TITLE, Strings.ERROR_NO_RESULTS_TO_SAVE)
            return

        try:
            save_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[(Strings.FILE_TYPE_CSV, Strings.FILE_EXTENSION_CSV)],
                initialfile=Strings.DEFAULT_RESULT_FILE
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

            messagebox.showinfo(Strings.SUCCESS_TITLE, Strings.format_file_saved(save_path))
            self._reset_ui()

        except Exception as e:
            messagebox.showerror(Strings.ERROR_TITLE, str(e))
            self._reset_ui()

    def _reset_ui(self):
        self.run_button.config(state="normal")
        self.progress_var.set(0)
        self.status_label.config(
            text="",
            bg=self.themes[self.current_theme]["bg"],
            fg=self.themes[self.current_theme]["text_secondary"]
        )
        self.save_button.config(state="disabled")
        self._last_results = None


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
