import logging
import os
from datetime import datetime

# Define the log directory and file path
LOG_DIR = "SmartVoca_log"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def setup_logger():
    """Configures the logging system."""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
        
    logging.basicConfig(
        filename=LOG_FILE,
        level=logging.ERROR,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        encoding="utf-8"
    )

def log_exception(logger_name, message, exception=None):
    """Logs an exception with a specific logger name."""
    logger = logging.getLogger(logger_name)
    if exception:
        logger.error(f"{message} | Exception: {str(exception)}", exc_info=True)
    else:
        logger.error(message)
        
def log_info(logger_name, message):
    """Logs an info with a specific logger name."""
    logger = logging.getLogger(logger_name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        logger.propagate = False  # Root 로거의 ERROR 필터링을 피하기 위해 전파 차단
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
    logger.info(f"{message}")
