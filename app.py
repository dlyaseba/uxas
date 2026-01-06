import csv
import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from matcher import best_match
from strings import Strings


class App:
    def __init__(self, root):
        self.root = root
        root.title(Strings.WINDOW_TITLE)
        root.geometry("600x400")

        # Keep raw column headers (may include empty strings) separate from what we display.
        self.ref_path = None
        self.cand_path = None
        self.ref_columns_raw = []
        self.cand_columns_raw = []
        self.ref_column = None
        self.cand_column = None
        self._last_results = None

        ref_frame = tk.Frame(root)
        ref_frame.pack(pady=8)
        tk.Button(ref_frame, text=Strings.BTN_SELECT_REFERENCE, command=self.load_ref).pack(side=tk.LEFT, padx=5)
        self.ref_label = tk.Label(ref_frame, text=Strings.LABEL_REFERENCE_NOT_SELECTED)
        self.ref_label.pack(side=tk.LEFT, padx=5)
        self.ref_column_combo = ttk.Combobox(ref_frame, state="readonly", width=25)
        self.ref_column_combo.pack(side=tk.LEFT, padx=5)
        self.ref_column_combo.bind("<<ComboboxSelected>>", self.on_ref_column_selected)

        cand_frame = tk.Frame(root)
        cand_frame.pack(pady=8)
        tk.Button(cand_frame, text=Strings.BTN_SELECT_CANDIDATES, command=self.load_cand).pack(side=tk.LEFT, padx=5)
        self.cand_label = tk.Label(cand_frame, text=Strings.LABEL_CANDIDATES_NOT_SELECTED)
        self.cand_label.pack(side=tk.LEFT, padx=5)
        self.cand_column_combo = ttk.Combobox(cand_frame, state="readonly", width=25)
        self.cand_column_combo.pack(side=tk.LEFT, padx=5)
        self.cand_column_combo.bind("<<ComboboxSelected>>", self.on_cand_column_selected)

        threshold_frame = tk.Frame(root)
        threshold_frame.pack(pady=10)
        tk.Label(threshold_frame, text=Strings.LABEL_THRESHOLD).pack(side=tk.LEFT, padx=5)
        self.threshold_var = tk.DoubleVar(value=0.8)
        self.threshold_scale = tk.Scale(threshold_frame, from_=0.0, to=1.0, resolution=0.01, 
                                        orient=tk.HORIZONTAL, variable=self.threshold_var, length=200,
                                        command=self.on_scale_change)
        self.threshold_scale.pack(side=tk.LEFT)
        self.threshold_entry = tk.Entry(threshold_frame, width=6)
        self.threshold_entry.pack(side=tk.LEFT, padx=5)
        self.threshold_entry.insert(0, "0.80")
        self.threshold_entry.bind("<Return>", self.on_entry_change)
        self.threshold_entry.bind("<FocusOut>", self.on_entry_change)

        self.run_button = tk.Button(root, text=Strings.BTN_RUN, command=self.run)
        self.run_button.pack(pady=5)

        self.save_button = tk.Button(root, text=Strings.BTN_SAVE_RESULTS, command=self.save_results, state="disabled")
        self.save_button.pack(pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(root, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(pady=5)
        
        self.status_label = tk.Label(root, text="")
        self.status_label.pack(pady=5)

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
                            text=Strings.format_reference_label(os.path.basename(path))
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
                            text=Strings.format_candidates_label(os.path.basename(path))
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
        self.status_label.config(text=Strings.STATUS_PROCESSING)
        self.root.update()

        thread = threading.Thread(target=self._run_matching, args=(ref_col, cand_col))
        thread.daemon = True
        thread.start()

    def _run_matching(self, ref_col, cand_col):
        try:
            with open(self.ref_path, encoding="utf-8") as f:
                reference_names = [r.get(ref_col, "") or "" for r in csv.DictReader(f)]

            with open(self.cand_path, encoding="utf-8") as f:
                candidate_names = [r.get(cand_col, "") or "" for r in csv.DictReader(f)]

            result_rows = []
            threshold = self.threshold_var.get()
            total = len(reference_names)

            for idx, ref in enumerate(reference_names):
                match, score = best_match(ref, candidate_names, threshold)
                result_rows.append({
                    Strings.CSV_COLUMN_REFERENCE: ref,
                    Strings.CSV_COLUMN_BEST_MATCH: match,
                    Strings.CSV_COLUMN_SIMILARITY: score
                })
                
                # Update progress
                progress = (idx + 1) / total * 100
                self.progress_var.set(progress)
                self.status_label.config(text=Strings.format_processed(idx + 1, total))
                self.root.update_idletasks()

            # Hand over to main thread to notify user that results are ready.
            self.root.after(0, self._on_results_ready, result_rows)

        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(Strings.ERROR_TITLE, str(e)))
            self.root.after(0, self._reset_ui)

    def _on_results_ready(self, result_rows):
        """Called on main thread when matching is complete."""
        self._last_results = result_rows
        self.status_label.config(text=Strings.STATUS_RESULTS_READY)
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
                writer = csv.DictWriter(
                    f,
                    fieldnames=[Strings.CSV_COLUMN_REFERENCE, Strings.CSV_COLUMN_BEST_MATCH, Strings.CSV_COLUMN_SIMILARITY]
                )
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
        self.status_label.config(text="")
        self.save_button.config(state="disabled")
        self._last_results = None


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
