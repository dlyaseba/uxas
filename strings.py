# UI Text Strings - Customize labels, messages, and other text here

class Strings:
    # Window
    WINDOW_TITLE = "CSV Similarity Matcher"
    
    # Buttons
    BTN_SELECT_REFERENCE = "Выбрать источник"
    BTN_SELECT_CANDIDATES = "Выбрать сравниваемые"
    BTN_RUN = "Запустить"
    BTN_SAVE_RESULTS = "Сохранить результаты"
    
    # Labels
    LABEL_REFERENCE_NOT_SELECTED = "Источник не выбран"
    LABEL_CANDIDATES_NOT_SELECTED = "Сравниваемый не выбраны"
    LABEL_THRESHOLD = "Порог сходства:"
    LABEL_PROCESSING = "Обработка..."
    LABEL_PROCESSED = "Обработано: {current} / {total}"
    
    # Status messages
    STATUS_PROCESSING = "Обработка..."
    
    # Error messages
    ERROR_TITLE = "Ошибка"
    ERROR_NO_COLUMNS = "CSV файл не содержит колонок"
    ERROR_READ_FILE = "Не удалось прочитать файл: {error}"
    ERROR_SELECT_BOTH_FILES = "Выбери оба CSV файла"
    ERROR_SELECT_COLUMNS = "Выбери колонки для обоих файлов"
    ERROR_THRESHOLD_RANGE = "Порог сходства должен быть между 0.0 и 1.0"
    ERROR_INVALID_NUMBER = "Введите число"
    
    # Success messages
    SUCCESS_TITLE = "Готово"
    SUCCESS_FILE_SAVED = "Файл сохранён:\n{path}"
    
    # File dialogs
    FILE_TYPE_CSV = "CSV files"
    FILE_EXTENSION_CSV = "*.csv"
    DEFAULT_RESULT_FILE = "result.csv"
    
    # CSV column names
    CSV_COLUMN_REFERENCE = "reference"
    CSV_COLUMN_BEST_MATCH = "best_match"
    CSV_COLUMN_SIMILARITY = "similarity"

    STATUS_RESULTS_READY = "Результаты готовы"
    ERROR_NO_RESULTS_TO_SAVE = "Нет результатов для сохранения"
    
    # Format helpers
    @staticmethod
    def format_reference_label(filename):
        return f"Reference: {filename}"
    
    @staticmethod
    def format_candidates_label(filename):
        return f"Candidates: {filename}"
    
    @staticmethod
    def format_processed(current, total):
        return Strings.LABEL_PROCESSED.format(current=current, total=total)
    
    @staticmethod
    def format_file_saved(path):
        return Strings.SUCCESS_FILE_SAVED.format(path=path)
    
    @staticmethod
    def format_read_error(error):
        return Strings.ERROR_READ_FILE.format(error=error)
