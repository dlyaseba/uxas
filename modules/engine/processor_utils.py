"""
Utility functions for CSV processing that need to be module-level for multiprocessing.
These must be picklable for use with multiprocessing.Pool.
"""


def process_single_match(args):
    """
    Process a single reference row with candidate rows.
    
    This function is module-level and picklable for use with multiprocessing.
    
    Args:
        args: Tuple containing:
            - ref_row: Dictionary of reference row data
            - ref_col: Column name to match from reference
            - selected_ref_cols: List of selected reference columns for output
            - candidate_rows: List of candidate row dictionaries
            - cand_col: Column name to match from candidates
            - selected_cand_cols: List of selected candidate columns for output
            - threshold: Similarity threshold
            - column_names: Dictionary with CSV_COLUMN_* keys for output column names
            
    Returns:
        Dictionary containing match result with selected columns
    """
    from .matcher import best_match
    
    ref_row, ref_col, selected_ref_cols, candidate_rows, cand_col, selected_cand_cols, threshold, column_names = args
    ref_name = ref_row.get(ref_col, "") or ""

    # Normalize selected columns to lists to avoid surprises if None/sets are passed.
    selected_ref_cols = list(selected_ref_cols or [])
    selected_cand_cols = list(selected_cand_cols or [])

    # Compute columns that are selected both for reference and candidate files.
    # For these, we must keep separate output columns instead of letting one
    # overwrite the other in the result dictionary.
    ref_cols_set = set(selected_ref_cols)
    cand_cols_set = set(selected_cand_cols)
    conflicting_cols = {c for c in ref_cols_set & cand_cols_set if c}

    def _make_output_key(col: str, source: str) -> str:
        """
        Compute the output key for a given source/column combination.

        When the same column name is selected in both reference and candidate
        files, we disambiguate them by appending a suffix, e.g. "name (ref)"
        and "name (cand)". This prevents their values from being merged into
        a single column in the output.
        """
        if col in conflicting_cols and col:
            return f"{col} (ref)" if source == "ref" else f"{col} (cand)"
        return col
    
    # Extract candidate names for matching
    candidate_names = [r.get(cand_col, "") or "" for r in candidate_rows]
    match, score = best_match(ref_name, candidate_names, threshold)
    
    # Start with basic match columns
    result = {
        column_names.get("CSV_COLUMN_REFERENCE", "reference"): ref_name,
        column_names.get("CSV_COLUMN_BEST_MATCH", "best_match"): match or "",
        column_names.get("CSV_COLUMN_SIMILARITY", "similarity"): score if score is not None else ""
    }
    
    # Add selected columns from reference row
    for col in selected_ref_cols:
        if col in ref_row:
            key = _make_output_key(col, "ref")
            result[key] = ref_row[col]
    
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
                    key = _make_output_key(col, "cand")
                    result[key] = matched_row[col]
    
    return result
