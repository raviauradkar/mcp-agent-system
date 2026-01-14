# logger.py
import logging
import sys


import sys

def set_terminal_title(title):
    # \033]0; is the start sequence for setting the title
    # \007 is the string terminator
    sys.stdout.write(f"\x1b]2;{title}\x07")
    sys.stdout.flush()

def setup_logger(name: str = "mcp_agent", level: str = "INFO"):
    """
    Setup a logger with console and file output

    Log format includes:
    - %(asctime)s: Timestamp
    - %(process)d: Process ID
    - %(name)s: Logger name
    - %(levelname)s: Log level (INFO, DEBUG, etc.)
    - %(funcName)s: Function name (file logs only)
    - %(lineno)d: Line number (file logs only)
    - %(message)s: Actual log message

    Args:
        name: Logger name (usually __name__ or module name)
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Avoid duplicate handlers if logger already exists
    if logger.handlers:
        return logger
    
    # Console handler (prints to terminal)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - PID:%(process)d - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_handler.setFormatter(console_format)

    # File handler (saves to file)
    file_handler = logging.FileHandler('mcp_agent.log')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - PID:%(process)d - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create a default logger for the module
logger = setup_logger()