"""
Centralised logging configuration for the LightRAG PoC.

Call ``configure_logging()`` once at the entry point of each script or
server instead of calling ``logging.basicConfig(...)`` in every file.

Example usage::

    from logging_config import configure_logging
    configure_logging(level="INFO")

    import logging
    logger = logging.getLogger(__name__)
    logger.info("System started")
"""

import logging
import os
import sys
from typing import Optional


def configure_logging(
    level: Optional[str] = None,
    fmt: Optional[str] = None,
) -> None:
    """
    Configure the root logger with a consistent format.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            Defaults to the LOG_LEVEL environment variable, or INFO.
        fmt: Log format string.
            Defaults to ``"%(levelname)s %(name)s – %(message)s"``.
    """
    level = level or os.getenv("LOG_LEVEL", "INFO")
    fmt = fmt or "%(levelname)s %(name)s – %(message)s"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=fmt,
        stream=sys.stdout,
        force=True,  # Override any earlier basicConfig calls
    )


def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.

    Convenience wrapper so callers don't need to import ``logging`` directly.

    Example::

        from logging_config import get_logger
        logger = get_logger(__name__)
        logger.info("Processing document")
    """
    return logging.getLogger(name)
