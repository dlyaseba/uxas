"""
CSV Processing Engine.

This module handles CSV file reading, processing, and matching operations.
It uses multiprocessing for parallel execution when beneficial.
"""

import csv
from multiprocessing import Pool, cpu_count
from PySide6.QtCore import QThread, Signal

from .matcher import best_match
from .processor_utils import process_single_match


class MatchingWorker(QThread):
    """Worker thread for running matching in background."""
    
    progress_updated = Signal(float, int, int)  # progress, current, total
    finished = Signal(list)  # result_rows
    error = Signal(str)
    
    def __init__(
        self,
        ref_path,
        cand_path,
        ref_col,
        cand_col,
        selected_ref_cols,
        selected_cand_cols,
        threshold,
        column_names=None,
        parent=None,
    ):
        """
        Initialize matching worker.
        
        Args:
            ref_path: Path to reference CSV file
            cand_path: Path to candidate CSV file
            ref_col: Column name in reference file for matching
            cand_col: Column name in candidate file for matching
            selected_ref_cols: Set of reference columns to include in output
            selected_cand_cols: Set of candidate columns to include in output
            threshold: Similarity threshold (0-1)
            column_names: Dict with CSV_COLUMN_* keys for output column names
        """
        # Parent the thread to the main window (or provided parent) so that its
        # lifetime is tied to the UI and it can be managed safely on shutdown.
        super().__init__(parent)
        self.ref_path = ref_path
        self.cand_path = cand_path
        self.ref_col = ref_col
        self.cand_col = cand_col
        self.selected_ref_cols = selected_ref_cols
        self.selected_cand_cols = selected_cand_cols
        self.threshold = threshold
        self.column_names = column_names or {}
    
    def run(self):
        """Execute the matching process."""
        try:
            # Check for interruption before starting
            if self.isInterruptionRequested():
                return
            
            # Read all reference rows (to access all columns)
            with open(self.ref_path, encoding="utf-8") as f:
                reference_rows = list(csv.DictReader(f))

            # Check for interruption after file read
            if self.isInterruptionRequested():
                return

            # Read all candidate rows (to access all columns)
            with open(self.cand_path, encoding="utf-8") as f:
                candidate_rows = list(csv.DictReader(f))

            # Check for interruption after file read
            if self.isInterruptionRequested():
                return

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
                    args_list = [
                        (ref_row, self.ref_col, selected_ref_cols, candidate_rows, 
                         self.cand_col, selected_cand_cols, self.threshold, self.column_names)
                        for ref_row in reference_rows
                    ]
                    
                    # Process in parallel
                    with Pool(processes=num_workers) as pool:
                        results = pool.imap(process_single_match, args_list)
                        
                        processed = 0
                        for result in results:
                            # Check for interruption during processing
                            if self.isInterruptionRequested():
                                return
                                
                            result_rows.append(result)
                            processed += 1
                            
                            # Update progress periodically for responsiveness
                            if processed % 10 == 0 or processed == total:
                                progress = (processed / total) * 100
                                self.progress_updated.emit(progress, processed, total)
                    
                    # Resolve conflicts where the same candidate was matched
                    # to multiple references by keeping only the best-scoring
                    # reference per candidate.
                    result_rows = self._resolve_candidate_conflicts(
                        result_rows, selected_cand_cols
                    )

                    # Check for interruption before final emit
                    if not self.isInterruptionRequested():
                        # Final progress update
                        self.progress_updated.emit(100, total, total)
                        self.finished.emit(result_rows)
                    return
                except Exception as e:
                    # Fallback to sequential processing if multiprocessing fails
                    pass

            # Sequential processing (fallback or for small datasets)
            candidate_names = [r.get(self.cand_col, "") or "" for r in candidate_rows]

            ref_col_name = self.column_names.get("CSV_COLUMN_REFERENCE", "reference")
            match_col_name = self.column_names.get("CSV_COLUMN_BEST_MATCH", "best_match")
            similarity_col_name = self.column_names.get("CSV_COLUMN_SIMILARITY", "similarity")
            
            for idx, ref_row in enumerate(reference_rows):
                # Check for interruption during processing
                if self.isInterruptionRequested():
                    return
                    
                ref_name = ref_row.get(self.ref_col, "") or ""
                match, score = best_match(ref_name, candidate_names, self.threshold)
                
                # Start with basic match columns
                result = {
                    ref_col_name: ref_name,
                    match_col_name: match or "",
                    similarity_col_name: score if score is not None else ""
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
            if not self.isInterruptionRequested():
                # Resolve conflicts where the same candidate was matched to
                # multiple references by keeping only the best-scoring
                # reference per candidate.
                result_rows = self._resolve_candidate_conflicts(
                    result_rows, selected_cand_cols
                )
                self.progress_updated.emit(100, total, total)
                self.finished.emit(result_rows)

        except Exception as e:
            if not self.isInterruptionRequested():
                self.error.emit(str(e))

    def _resolve_candidate_conflicts(self, result_rows, selected_cand_cols):
        """
        Post-process result rows to ensure that each candidate string is used
        at most once, assigning it to the reference with the highest score.

        This is a lightweight global conflict resolution step that:
          - looks at all (reference, candidate, score) triples
          - for each candidate string, keeps only the row with the best score
          - clears the match, similarity, and candidate-side columns for
            weaker rows that pointed to the same candidate.

        This approach:
          - avoids building a full score matrix
          - works for both multiprocessing and sequential paths
          - ensures "later better" matches can win, regardless of order
        """
        if not result_rows:
            return result_rows

        match_col_name = self.column_names.get("CSV_COLUMN_BEST_MATCH", "best_match")
        similarity_col_name = self.column_names.get("CSV_COLUMN_SIMILARITY", "similarity")

        # Track the best row index per candidate string
        best_for_candidate = {}  # candidate_str -> (best_score, row_index)
        losers = set()

        for idx, row in enumerate(result_rows):
            cand = (row.get(match_col_name) or "").strip()
            if not cand:
                continue

            raw_score = row.get(similarity_col_name, "")
            try:
                score = float(raw_score) if raw_score != "" else 0.0
            except (TypeError, ValueError):
                score = 0.0

            prev = best_for_candidate.get(cand)
            if prev is None or score > prev[0]:
                # Mark previous best (if any) as loser
                if prev is not None:
                    losers.add(prev[1])
                best_for_candidate[cand] = (score, idx)
            else:
                losers.add(idx)

        if not losers:
            return result_rows

        # Clear matches and candidate-side columns for losing rows
        for idx in losers:
            row = result_rows[idx]
            row[match_col_name] = ""
            row[similarity_col_name] = ""
            for col in selected_cand_cols:
                if col in row:
                    row[col] = ""

        return result_rows


class CSVProcessor:
    """
    High-level CSV processing interface.
    
    This class provides a clean API for processing CSV files without
    directly dealing with threads.
    """
    
    @staticmethod
    def create_worker(
        ref_path,
        cand_path,
        ref_col,
        cand_col,
        selected_ref_cols,
        selected_cand_cols,
        threshold,
        column_names=None,
        parent=None,
    ):
        """
        Create a matching worker for processing CSV files.
        
        Returns:
            MatchingWorker instance ready to start
        """
        return MatchingWorker(
            ref_path,
            cand_path,
            ref_col,
            cand_col,
            selected_ref_cols,
            selected_cand_cols,
            threshold,
            column_names,
            parent,
        )
    
    @staticmethod
    def read_csv_columns(csv_path):
        """
        Read column names from a CSV file.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            List of column names, or empty list if file doesn't exist or has no columns
        """
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames
                return list(columns) if columns else []
        except Exception:
            return []
    
    @staticmethod
    def validate_csv_file(csv_path):
        """
        Validate that a CSV file exists and is readable.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                columns = reader.fieldnames
                if not columns:
                    return False, "CSV file does not contain columns"
            return True, None
        except FileNotFoundError:
            return False, f"File not found: {csv_path}"
        except Exception as e:
            return False, f"Failed to read file: {str(e)}"
