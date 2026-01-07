# UI Text Strings - Uses i18n translations
# This module provides backward compatibility and convenience access to translations

from translations import t, get_translator


class _StringsMeta(type):
    """Metaclass to make Strings attributes work as class attributes."""
    def __getattr__(cls, name):
        # Map attribute names to translation keys
        key_map = {
            "WINDOW_TITLE": "window_title",
            "BTN_SELECT_REFERENCE": "btn_select_reference",
            "BTN_SELECT_CANDIDATES": "btn_select_candidates",
            "BTN_RUN": "btn_run",
            "BTN_SAVE_RESULTS": "btn_save_results",
            "LABEL_REFERENCE_NOT_SELECTED": "label_reference_not_selected",
            "LABEL_CANDIDATES_NOT_SELECTED": "label_candidates_not_selected",
            "LABEL_THRESHOLD": "label_threshold",
            "LABEL_PROCESSING": "label_processing",
            "LABEL_PROCESSED": "label_processed",
            "STATUS_PROCESSING": "status_processing",
            "ERROR_TITLE": "error_title",
            "ERROR_NO_COLUMNS": "error_no_columns",
            "ERROR_READ_FILE": "error_read_file",
            "ERROR_SELECT_BOTH_FILES": "error_select_both_files",
            "ERROR_SELECT_COLUMNS": "error_select_columns",
            "ERROR_THRESHOLD_RANGE": "error_threshold_range",
            "ERROR_INVALID_NUMBER": "error_invalid_number",
            "SUCCESS_TITLE": "success_title",
            "SUCCESS_FILE_SAVED": "success_file_saved",
            "FILE_TYPE_CSV": "file_type_csv",
            "FILE_EXTENSION_CSV": "file_extension_csv",
            "DEFAULT_RESULT_FILE": "default_result_file",
            "CSV_COLUMN_REFERENCE": "csv_column_reference",
            "CSV_COLUMN_BEST_MATCH": "csv_column_best_match",
            "CSV_COLUMN_SIMILARITY": "csv_column_similarity",
            "STATUS_RESULTS_READY": "status_results_ready",
            "ERROR_NO_RESULTS_TO_SAVE": "error_no_results_to_save",
        }
        
        if name in key_map:
            return t(key_map[name])
        raise AttributeError(f"'{cls.__name__}' object has no attribute '{name}'")


class Strings(metaclass=_StringsMeta):
    """String constants using i18n translations."""
    pass
    
    # Format helpers
    @staticmethod
    def format_reference_label(filename):
        return t("format_reference", filename=filename)
    
    @staticmethod
    def format_candidates_label(filename):
        return t("format_candidates", filename=filename)
    
    @staticmethod
    def format_processed(current, total):
        return t("label_processed", current=current, total=total)
    
    @staticmethod
    def format_file_saved(path):
        return t("success_file_saved", path=path)
    
    @staticmethod
    def format_read_error(error):
        return t("error_read_file", error=error)


# Create singleton instance for backward compatibility
_strings = Strings()


# Convenience functions for direct access
def get_strings():
    """Get the Strings instance."""
    return _strings
