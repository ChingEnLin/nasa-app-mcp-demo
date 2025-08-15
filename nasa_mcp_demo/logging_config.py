"""Logging configuration for NASA MCP Demo application."""

import logging
import sys
import time
from typing import Any, Dict, Optional
from datetime import datetime
from contextlib import contextmanager

import structlog
from structlog.types import Processor


def setup_logging(logging_config) -> None:
    """Setup structured logging for the application.
    
    Args:
        logging_config: LoggingConfig instance with logging settings
    """
    configure_logging(
        log_level=logging_config.level,
        log_format=logging_config.format,
        enable_request_logging=logging_config.enable_request_logging,
        enable_nasa_api_logging=logging_config.enable_nasa_api_logging
    )


def configure_logging(
    log_level: str = "INFO",
    log_format: str = "json",
    enable_request_logging: bool = True,
    enable_nasa_api_logging: bool = True
) -> None:
    """Configure structured logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Log format (json or text)
        enable_request_logging: Enable HTTP request/response logging
        enable_nasa_api_logging: Enable NASA API call logging
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
        structlog.processors.TimeStamper(fmt="ISO"),
        add_performance_context,
        add_error_context,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
    ]
    
    # Add development-specific processors
    if log_format == "text":
        processors.extend([
            structlog.processors.CallsiteParameterAdder(
                parameters=[
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.FUNC_NAME
                ]
            ),
        ])
    
    # Add final processor based on format
    if log_format == "text":
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
    
    # Store configuration for middleware
    _logging_config.update({
        "enable_request_logging": enable_request_logging,
        "enable_nasa_api_logging": enable_nasa_api_logging,
        "log_level": log_level
    })


def add_performance_context(logger, method_name, event_dict):
    """Add performance context to log entries."""
    # Add timestamp for performance tracking
    event_dict["timestamp"] = datetime.now().isoformat()
    
    # Add performance markers if available
    if "duration_ms" in event_dict:
        duration = event_dict["duration_ms"]
        if duration > 5000:  # 5 seconds
            event_dict["performance_warning"] = "slow_operation"
        elif duration > 1000:  # 1 second
            event_dict["performance_info"] = "moderate_duration"
    
    return event_dict


def add_error_context(logger, method_name, event_dict):
    """Add error context and tracking information."""
    # Add error tracking ID for errors
    if event_dict.get("level") in ["error", "critical"]:
        import uuid
        event_dict["error_id"] = str(uuid.uuid4())
        event_dict["error_timestamp"] = datetime.now().isoformat()
    
    # Add stack trace context for exceptions
    if "exception" in event_dict or "exc_info" in event_dict:
        event_dict["has_exception"] = True
        event_dict["error_category"] = "exception"
    
    return event_dict


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


# Global logging configuration storage
_logging_config: Dict[str, Any] = {}


def get_logging_config() -> Dict[str, Any]:
    """Get current logging configuration."""
    return _logging_config.copy()


# Performance monitoring utilities
class PerformanceMonitor:
    """Performance monitoring utility for tracking operation durations."""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self.start_time: Optional[float] = None
        self.operation_name: Optional[str] = None
    
    def start(self, operation_name: str, **context) -> None:
        """Start monitoring an operation."""
        self.operation_name = operation_name
        self.start_time = time.time()
        self.logger.debug(
            "Operation started",
            operation=operation_name,
            **context
        )
    
    def end(self, **context) -> float:
        """End monitoring and log duration."""
        if self.start_time is None:
            self.logger.warning("Performance monitor end called without start")
            return 0.0
        
        duration_seconds = time.time() - self.start_time
        duration_ms = duration_seconds * 1000
        
        log_level = "info"
        if duration_ms > 5000:  # 5 seconds
            log_level = "warning"
        elif duration_ms > 10000:  # 10 seconds
            log_level = "error"
        
        getattr(self.logger, log_level)(
            "Operation completed",
            operation=self.operation_name,
            duration_seconds=round(duration_seconds, 3),
            duration_ms=round(duration_ms, 2),
            **context
        )
        
        return duration_seconds
    
    @contextmanager
    def monitor(self, operation_name: str, **context):
        """Context manager for monitoring operations."""
        self.start(operation_name, **context)
        try:
            yield self
        finally:
            self.end(**context)


# NASA API specific logging utilities
class NASAAPILogger:
    """Specialized logger for NASA API interactions."""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
        self.performance_monitor = PerformanceMonitor(logger)
    
    def log_request(self, endpoint: str, params: Optional[Dict[str, Any]] = None, **context):
        """Log NASA API request."""
        if not _logging_config.get("enable_nasa_api_logging", True):
            return
        
        self.logger.info(
            "NASA API request",
            endpoint=endpoint,
            params=params or {},
            api_type="nasa",
            **context
        )
    
    def log_response(
        self,
        endpoint: str,
        status_code: int,
        response_size: Optional[int] = None,
        duration_ms: Optional[float] = None,
        **context
    ):
        """Log NASA API response."""
        if not _logging_config.get("enable_nasa_api_logging", True):
            return
        
        log_data = {
            "endpoint": endpoint,
            "status_code": status_code,
            "api_type": "nasa",
            **context
        }
        
        if response_size is not None:
            log_data["response_size_bytes"] = response_size
        
        if duration_ms is not None:
            log_data["duration_ms"] = round(duration_ms, 2)
        
        # Determine log level based on status code
        if 200 <= status_code < 300:
            log_level = "info"
        elif 400 <= status_code < 500:
            log_level = "warning"
        else:
            log_level = "error"
        
        getattr(self.logger, log_level)("NASA API response", **log_data)
    
    def log_error(
        self,
        endpoint: str,
        error: Exception,
        retry_attempt: Optional[int] = None,
        **context
    ):
        """Log NASA API error."""
        error_data = {
            "endpoint": endpoint,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "api_type": "nasa",
            **context
        }
        
        if retry_attempt is not None:
            error_data["retry_attempt"] = retry_attempt
        
        self.logger.error("NASA API error", **error_data)
    
    def log_rate_limit(self, endpoint: str, wait_time: float, **context):
        """Log rate limiting events."""
        self.logger.warning(
            "NASA API rate limited",
            endpoint=endpoint,
            wait_time_seconds=round(wait_time, 2),
            api_type="nasa",
            **context
        )
    
    def log_cache_hit(self, endpoint: str, cache_key: str, **context):
        """Log cache hit events."""
        self.logger.debug(
            "NASA API cache hit",
            endpoint=endpoint,
            cache_key=cache_key,
            api_type="nasa",
            **context
        )
    
    def log_cache_miss(self, endpoint: str, cache_key: str, **context):
        """Log cache miss events."""
        self.logger.debug(
            "NASA API cache miss",
            endpoint=endpoint,
            cache_key=cache_key,
            api_type="nasa",
            **context
        )


# Request logging middleware context
def add_request_context(**kwargs: Any) -> Dict[str, Any]:
    """Add request context to log entries.
    
    Args:
        **kwargs: Context variables to add
        
    Returns:
        Context dictionary
    """
    return kwargs


# Error tracking utilities
class ErrorTracker:
    """Utility for tracking and categorizing errors."""
    
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger
    
    def track_error(
        self,
        error: Exception,
        context: str,
        severity: str = "error",
        **additional_context
    ):
        """Track an error with context and categorization."""
        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "error_context": context,
            "severity": severity,
            **additional_context
        }
        
        # Add error categorization
        if isinstance(error, (ConnectionError, TimeoutError)):
            error_data["error_category"] = "network"
        elif isinstance(error, ValueError):
            error_data["error_category"] = "validation"
        elif isinstance(error, KeyError):
            error_data["error_category"] = "data"
        else:
            error_data["error_category"] = "unknown"
        
        getattr(self.logger, severity)("Error tracked", **error_data)
        
        return error_data.get("error_id")