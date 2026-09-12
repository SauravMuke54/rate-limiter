# logging_config.py
"""
Centralized logging configuration for the gateway.
Call setup_logging() once at startup (in main.py's lifespan or module level).
"""
import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)

    # Avoid duplicate handlers if setup_logging is called more than once
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)

    # Quiet down noisy third-party loggers unless you want their debug output
    logging.getLogger("httpx").setLevel("WARNING")
    logging.getLogger("hpack").setLevel("WARNING")


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)