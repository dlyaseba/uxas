"""
Utility functions for CSV processing that need to be module-level for multiprocessing.
These must be picklable for use with multiprocessing.Pool.
"""

from typing import Dict, Iterable, List, Optional, Sequence, Tuple


def _norm(col: str) -> str:
    """
    Normalization helper for comparing column names across files.

    In addition to trimming whitespace and lowercasing, this also strips a
    leading UTF‑8 BOM (\\ufeff) which can get embedded into the first header
    name when reading CSVs. Without this, one file might see the header as
    \"\\ufeffID\" while the other sees \"ID\", and they would not be treated
    as the same column.
    """
    if not col:
        return ""
    # Strip common BOM chars then whitespace, then lowercase.
    return col.replace("\ufeff", "").strip().lower()


def build_output_column_mapping(
    ref_columns_order: Sequence[str],
    cand_columns_order: Sequence[str],
    selected_ref_cols: Iterable[str],
    selected_cand_cols: Iterable[str],
    reserved_names: Optional[Iterable[str]] = None,
) -> Dict[Tuple[str, str], str]:
    """
    Build a stable mapping from (source, original_column_name) to the final
    output header name used in the result CSV.

    The mapping:
      - preserves the original column order within each file
      - guarantees that every output header is unique across both files
      - avoids clashing with reserved names such as the basic match columns
      - assigns numeric suffixes when the same name appears multiple times,
        e.g. "ID", "ID(2)", "ID(3)", etc.

    Args:
        ref_columns_order: All reference CSV headers in their original order.
        cand_columns_order: All candidate CSV headers in their original order.
        selected_ref_cols: Columns from reference file selected for output.
        selected_cand_cols: Columns from candidate file selected for output.
        reserved_names: Column names that must not be used for data columns
            (e.g. the "reference"/"best_match"/"similarity" match columns).

    Returns:
        Dict mapping (source, original_name) -> unique output header.
        `source` is "ref" or "cand".
    """
    selected_ref = set(selected_ref_cols or [])
    selected_cand = set(selected_cand_cols or [])

    used_names = set(reserved_names or [])
    counters: Dict[str, int] = {}
    mapping: Dict[Tuple[str, str], str] = {}

    # Detect names that appear (after normalization) in both ref and cand
    # so we can force them to split into *_ref / *_cand variants instead of
    # ever sharing the same header.
    ref_norms = {_norm(c) for c in ref_columns_order or [] if c in selected_ref}
    cand_norms = {_norm(c) for c in cand_columns_order or [] if c in selected_cand}
    shared_norms = {n for n in ref_norms & cand_norms if n}

    def _assign(source: str, col: str):
        if source == "ref":
            if col not in selected_ref:
                return
        else:
            if col not in selected_cand:
                return

        # Clean BOM for human-facing output names, but keep the original
        # column key for looking up values in DictReader rows.
        raw_base = (col or "").replace("\ufeff", "")
        n = _norm(col)

        # If this normalized name is selected from both reference and
        # candidate files, explicitly split the headers so that, e.g.,
        # an "ID" column in both files becomes "ID_ref" and "ID_cand".
        if n in shared_norms and raw_base:
            if source == "ref":
                base = f"{raw_base}_ref"
            else:
                base = f"{raw_base}_cand"
        else:
            base = raw_base

        norm_key = _norm(base) or "__empty__"

        # First occurrence keeps the base name (unless it clashes with
        # a reserved or already-used name), subsequent ones get "(n)" suffix.
        count = counters.get(norm_key, 0) + 1
        counters[norm_key] = count

        if count == 1:
            out_name = base
        else:
            out_name = f"{base}({count})"

        # Ensure global uniqueness across all columns and reserved names.
        while out_name in used_names:
            count += 1
            counters[norm_key] = count
            out_name = f"{base}({count})"

        used_names.add(out_name)
        mapping[(source, col)] = out_name

    for col in ref_columns_order or []:
        _assign("ref", col)

    for col in cand_columns_order or []:
        _assign("cand", col)

    return mapping


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
            - column_mapping (optional): Dict[(source, col)] -> output header
            
    Returns:
        Dictionary containing match result with selected columns
    """
    from .matcher import best_match

    # Support both old and new call signatures for safety.
    if len(args) == 8:
        (
            ref_row,
            ref_col,
            selected_ref_cols,
            candidate_rows,
            cand_col,
            selected_cand_cols,
            threshold,
            column_names,
        ) = args
        column_mapping = None
    else:
        (
            ref_row,
            ref_col,
            selected_ref_cols,
            candidate_rows,
            cand_col,
            selected_cand_cols,
            threshold,
            column_names,
            column_mapping,
        ) = args

    ref_name = ref_row.get(ref_col, "") or ""

    # Normalize selected columns to lists to avoid surprises if None/sets are passed.
    selected_ref_cols = list(selected_ref_cols or [])
    selected_cand_cols = list(selected_cand_cols or [])

    def _make_output_key(col: str, source: str) -> str:
        """
        Compute the output key for a given source/column combination.

        If a precomputed column_mapping is provided (from the main process),
        we rely on it so that multiprocessing and sequential paths, as well
        as the CSV writer, all use exactly the same headers. Otherwise we
        fall back to the original behavior of using the raw column name.
        """
        if column_mapping:
            return column_mapping.get((source, col), col)
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
