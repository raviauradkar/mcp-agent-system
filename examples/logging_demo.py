"""
Logging Demo - Shows how to use the standard Python logging in this project.

Example output:
  Console: 2026-01-14 18:00:00 - PID:12345 - my_module - INFO - This is an info message
  File:    2026-01-14 18:00:00 - PID:12345 - my_module - INFO - main:10 - This is an info message
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_agent.llogger import setup_logger


def main():
    # Create a logger for your module
    logger = setup_logger("my_module", level="DEBUG")

    # Use different log levels
    logger.debug("This is a debug message (only in file)")
    logger.info("This is an info message (console + file)")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

    # Log with variables
    user_id = "user123"
    action = "login"
    logger.info(f"User {user_id} performed action: {action}")

    # Log exceptions
    try:
        result = 1 / 0
    except Exception as e:
        logger.exception("An error occurred")  # Includes stack trace

    print("\n✅ Check 'mcp_agent.log' for detailed logs with function names and line numbers")


if __name__ == "__main__":
    main()
