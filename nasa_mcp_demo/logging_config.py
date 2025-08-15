"""Logging configuration for NASA MCP Demo application."""

import logging
import sys
from typing import Any, Dict

import structlog
from structlog.types import Processor


def setup_logging(logging_config) -> None:
    """Setup structured logging for the application.
    
    Args:
        logging_config: LoggingConfig instance with logging settings
    """
    configure_logging(logging_config.level, logging_config.format == "text")


def configure_logging(log_level: str = "INFO", debug: bool = False) -> None:
    """Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        debug: Enable debug mode with more verbose logging
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog processors
    processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    if debug:
        # Add more detailed processors for development
        processors.extend([
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FILENAME,
                           structlog.processors.CallsiteParameter.LINENO]
            ),
        ])
    
    # Add final processor based on environment
    if debug:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))
    else:
        processors.append(structlog.processors.JSONRenderer())
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Request logging middleware context
def add_request_context(**kwargs: Any) -> Dict[str, Any]:
    """Add request context to log entries.
    
    Args:
        **kwargs: Context variables to add
        
    Returns:
        Context dictionary
    """
    return kwargs