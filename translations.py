"""
Internationalization (i18n) translations for the application.
To add a new language, add a new entry in TRANSLATIONS dictionary.
"""

import locale
import platform

# Language codes
LANG_EN = "en"
LANG_RU = "ru"

# Default language
DEFAULT_LANG = LANG_EN


def detect_system_language():
    """Detect system language preference."""
    try:
        # Try to get system locale
        system_locale = locale.getdefaultlocale()[0]
        if system_locale:
            lang_code = system_locale.split('_')[0].lower()
            if lang_code in [LANG_EN, LANG_RU]:
                return lang_code
    except:
        pass
    
    # Fallback to default
    return DEFAULT_LANG


# Translation dictionary
# Structure: {language_code: {key: translation}}
TRANSLATIONS = {
    LANG_EN: {
        # Window
        "window_title": "Uxas",
        
        # Buttons
        "btn_select_reference": "Select Reference",
        "btn_select_candidates": "Select Candidates",
        "btn_run": "Run",
        "btn_save_results": "Save Results",
        "btn_select_all": "Select All",
        "btn_select_none": "Select None",
        
        # Labels
        "label_reference_not_selected": "Reference not selected",
        "label_candidates_not_selected": "Candidates not selected",
        "label_threshold": "Similarity Threshold:",
        "label_column": "Column:",
        "label_processing": "Processing...",
        "label_processed": "Processed: {current} / {total}",
        
        # Status messages
        "status_processing": "Processing...",
        "status_results_ready": "Results ready",
        
        # Error messages
        "error_title": "Error",
        "error_no_columns": "CSV file does not contain columns",
        "error_read_file": "Failed to read file: {error}",
        "error_select_both_files": "Select both CSV files",
        "error_select_columns": "Select columns for both files",
        "error_threshold_range": "Similarity threshold must be between 0.0 and 1.0",
        "error_invalid_number": "Enter a number",
        "error_no_results_to_save": "No results to save",
        "error_matching_in_progress": "Matching is already in progress. Please wait for it to finish.",
        
        # Success messages
        "success_title": "Done",
        "success_file_saved": "File saved:\n{path}",
        
        # File dialogs
        "file_type_csv": "CSV files",
        "file_extension_csv": "*.csv",
        "default_result_file": "result.csv",
        "dialog_select_reference": "Select Reference File",
        "dialog_select_candidates": "Select Candidates File",
        "dialog_save_results": "Save Results",
        
        # CSV column names
        "csv_column_reference": "reference",
        "csv_column_best_match": "best_match",
        "csv_column_similarity": "similarity",
        
        # Format helpers
        "format_reference": "Reference: {filename}",
        "format_candidates": "Candidates: {filename}",
        
        # Tabs
        "tab_matching": "Matching",
        "tab_output_columns": "Output Columns",
        
        # Column selection
        "column_selection_info": "Select additional columns from reference and candidate files to include in the output CSV.\nThe basic columns (reference, best_match, similarity) are always included.",
        "column_selection_no_files": "No files loaded. Please load reference and candidate files first.",
        "column_selection_ref_columns": "Reference File Columns:",
        "column_selection_cand_columns": "Candidate File Columns:",
        "column_no_header": "Column {index} (no header)",
        
        # Language names
        "lang_english": "English",
        "lang_russian": "Russian",
    },
    
    LANG_RU: {
        # Window
        "window_title": "Uxas",
        
        # Buttons
        "btn_select_reference": "Выбрать источник",
        "btn_select_candidates": "Выбрать сравниваемый",
        "btn_run": "Запустить",
        "btn_save_results": "Сохранить результаты",
        "btn_select_all": "Выбрать все",
        "btn_select_none": "Снять выбор",
        
        # Labels
        "label_reference_not_selected": "Источник не выбран",
        "label_candidates_not_selected": "Сравниваемый не выбран",
        "label_threshold": "Порог сходства:",
        "label_column": "Колонка:",
        "label_processing": "Обработка...",
        "label_processed": "Обработано: {current} / {total}",
        
        # Status messages
        "status_processing": "Обработка...",
        "status_results_ready": "Результаты готовы",
        
        # Error messages
        "error_title": "Ошибка",
        "error_no_columns": "CSV файл не содержит колонок",
        "error_read_file": "Не удалось прочитать файл: {error}",
        "error_select_both_files": "Выбери оба CSV файла",
        "error_select_columns": "Выбери колонки для обоих файлов",
        "error_threshold_range": "Порог сходства должен быть между 0.0 и 1.0",
        "error_invalid_number": "Введите число",
        "error_no_results_to_save": "Нет результатов для сохранения",
        "error_matching_in_progress": "Сопоставление уже выполняется. Пожалуйста, подождите завершения.",
        
        # Success messages
        "success_title": "Готово",
        "success_file_saved": "Файл сохранён:\n{path}",
        
        # File dialogs
        "file_type_csv": "CSV файлы",
        "file_extension_csv": "*.csv",
        "default_result_file": "result.csv",
        "dialog_select_reference": "Выбрать файл источника",
        "dialog_select_candidates": "Выбрать файл для сравнения",
        "dialog_save_results": "Сохранить результаты",
        
        # CSV column names
        "csv_column_reference": "reference",
        "csv_column_best_match": "best_match",
        "csv_column_similarity": "similarity",
        
        # Format helpers
        "format_reference": "Источник: {filename}",
        "format_candidates": "Сравниваемый: {filename}",
        
        # Tabs
        "tab_matching": "Сопоставление",
        "tab_output_columns": "Колонки вывода",
        
        # Column selection
        "column_selection_info": "Выберите дополнительные колонки из файлов источника и сравниваемого файла для включения в выходной CSV.\nБазовые колонки (reference, best_match, similarity) всегда включены.",
        "column_selection_no_files": "Файлы не загружены. Пожалуйста, сначала загрузите файлы источника и сравниваемого файла.",
        "column_selection_ref_columns": "Колонки файла источника:",
        "column_selection_cand_columns": "Колонки сравниваемого файла:",
        "column_no_header": "Колонка {index} (без заголовка)",
        
        # Language names
        "lang_english": "English",
        "lang_russian": "Русский",
    }
}


class Translator:
    """Translation manager class."""
    
    def __init__(self, language=None):
        """Initialize translator with specified language or system default."""
        if language is None:
            language = detect_system_language()
        self.language = language if language in TRANSLATIONS else DEFAULT_LANG
    
    def set_language(self, language):
        """Change the current language."""
        if language in TRANSLATIONS:
            self.language = language
        else:
            self.language = DEFAULT_LANG
    
    def translate(self, key, **kwargs):
        """
        Translate a key to current language.
        
        Args:
            key: Translation key
            **kwargs: Format arguments for string formatting
            
        Returns:
            Translated string with format arguments applied
        """
        translations = TRANSLATIONS.get(self.language, TRANSLATIONS[DEFAULT_LANG])
        translation = translations.get(key, key)
        
        if kwargs:
            try:
                return translation.format(**kwargs)
            except (KeyError, ValueError):
                return translation
        
        return translation
    
    def get_available_languages(self):
        """Get list of available language codes."""
        return list(TRANSLATIONS.keys())
    
    def get_language_name(self, lang_code):
        """Get display name for a language code."""
        if lang_code in TRANSLATIONS:
            key = f"lang_{lang_code}"
            return TRANSLATIONS[lang_code].get(key, lang_code.upper())
        return lang_code.upper()


# Global translator instance
_translator = Translator()


def t(key, **kwargs):
    """
    Convenience function to translate a key.
    Usage: t("key_name") or t("format_key", arg=value)
    """
    return _translator.translate(key, **kwargs)


def set_language(language):
    """Set the global language."""
    _translator.set_language(language)


def get_translator():
    """Get the global translator instance."""
    return _translator
