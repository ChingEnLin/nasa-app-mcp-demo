"""
Data models for NASA API responses and application configuration.

This package contains all Pydantic models used throughout the NASA MCP Demo application,
including NASA API response models, configuration models, and error handling models.
"""

from .config import AppConfig, CacheConfig, LoggingConfig, NASAConfig
from .errors import (
    CacheError,
    ConfigurationError,
    DataProcessingError,
    ErrorResponse,
    MCPToolError,
    MCPToolValidationError,
    NASAAPIError,
    NASAAPIInvalidRequest,
    NASAAPIRateLimited,
    NASAAPITimeout,
    NASAAPIUnavailable,
    NASAMCPError,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from .nasa_responses import (
    APODResponse,
    MarsPhoto,
    MarsRoverResponse,
    NEOObject,
    NEOResponse,
)

__all__ = [
    # Configuration models
    "AppConfig",
    "CacheConfig", 
    "LoggingConfig",
    "NASAConfig",
    # NASA API response models
    "APODResponse",
    "MarsPhoto",
    "MarsRoverResponse", 
    "NEOObject",
    "NEOResponse",
    # Error models and exceptions
    "ErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "NASAMCPError",
    "NASAAPIError",
    "NASAAPIUnavailable",
    "NASAAPIRateLimited", 
    "NASAAPIInvalidRequest",
    "NASAAPITimeout",
    "ConfigurationError",
    "MCPToolError",
    "MCPToolValidationError",
    "DataProcessingError",
    "CacheError",
]