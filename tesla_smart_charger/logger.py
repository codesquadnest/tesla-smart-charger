import logging
import os
import sys


DEFAULT_LOG_FILE = "tesla-smart-charger.log"


def get_logger(
    name: str = __name__, verbose: bool = False, log_file: str = None
) -> logging.Logger:
    """
    Set up a logger instance and return it.

    Args:
        name: str - name of the logger
        verbose: bool - whether to log debug messages
        log_file: str - path to the log file

    Returns:
        logger: logging.Logger - the logger instance
    """
    if "TSM_VERBOSE" in os.environ:
        verbose = True

    logger = logging.getLogger(name)

    # logger itself is ensured to be a singleton
    # but handlers should only be added once
    if len(logger.handlers) == 0:
        logger.setLevel(logging.DEBUG if verbose else logging.INFO)
        console_handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S %z"
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        if log_file := DEFAULT_LOG_FILE:
            file_handler = logging.FileHandler(log_file)

        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
