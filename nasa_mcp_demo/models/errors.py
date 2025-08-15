"""
Error response models and custom exception classes.

This module contains Pydantic models for error responses and custom
exception classes for different types of errors that can occur in the application.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from pydantic import BaseModel, Field, ConfigDict


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(
        None, 
        description="Additional error details"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO timestamp when error occurred"
    )
    request_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique identifier for the request"
    )
    
    model_config = ConfigDict(
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )


class ValidationErrorDetail(BaseModel):
    """Detail for validation errors."""
    
    field: str = Field(..., description="Field that failed validation")
    message: str = Field(..., description="Validation error message")
    invalid_value: Optional[Any] = Field(
        None, 
        description="The invalid value that was provided"
    )


class ValidationErrorResponse(ErrorResponse):
    """Error response for validation failures."""
    
    error: str = Field(default="validation_error", description="Error type")
    validation_errors: list[ValidationErrorDetail] = Field(
        ..., 
        description="List of validation errors"
    )


# Custom Exception Classes

class NASAMCPError(Exception):
    """Base exception for NASA MCP Demo application."""
    
    def __init__(
        self, 
        message: str, 
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None
    ):
        self.message = message
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__
        super().__init__(self.message)
    
    def to_error_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert exception to ErrorResponse model."""
        return ErrorResponse(
            error=self.error_code,
            message=self.message,
            details=self.details,
            request_id=request_id or str(uuid4())
        )


class NASAAPIError(NASAMCPError):
    """Base exception for NASA API related errors."""
    
    def __init__(
        self, 
        message: str, 
        status_code: Optional[int] = None,
        response_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if status_code:
            details['status_code'] = status_code
        if response_data:
            details['response_data'] = response_data
        
        super().__init__(message, details=details, **kwargs)
        self.status_code = status_code
        self.response_data = response_data


class NASAAPIUnavailable(NASAAPIError):
    """NASA API is temporarily unavailable."""
    
    def __init__(self, message: str = "NASA API is temporarily unavailable", **kwargs):
        super().__init__(message, error_code="nasa_api_unavailable", **kwargs)


class NASAAPIRateLimited(NASAAPIError):
    """Rate limit exceeded for NASA API."""
    
    def __init__(
        self, 
        message: str = "NASA API rate limit exceeded",
        retry_after: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if retry_after:
            details['retry_after'] = retry_after
        
        kwargs['error_code'] = "nasa_api_rate_limited"
        super().__init__(message, details=details, **kwargs)
        self.retry_after = retry_after


class NASAAPIInvalidRequest(NASAAPIError):
    """Invalid request parameters for NASA API."""
    
    def __init__(
        self, 
        message: str = "Invalid request parameters",
        invalid_params: Optional[Dict[str, str]] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if invalid_params:
            details['invalid_params'] = invalid_params
        
        kwargs['error_code'] = "nasa_api_invalid_request"
        super().__init__(message, details=details, **kwargs)
        self.invalid_params = invalid_params


class NASAAPITimeout(NASAAPIError):
    """NASA API request timeout."""
    
    def __init__(
        self, 
        message: str = "NASA API request timed out",
        timeout_duration: Optional[float] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if timeout_duration:
            details['timeout_duration'] = timeout_duration
        
        kwargs['error_code'] = "nasa_api_timeout"
        super().__init__(message, details=details, **kwargs)
        self.timeout_duration = timeout_duration


class ConfigurationError(NASAMCPError):
    """Configuration related errors."""
    
    def __init__(
        self, 
        message: str = "Configuration error",
        config_field: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if config_field:
            details['config_field'] = config_field
        
        kwargs['error_code'] = "configuration_error"
        super().__init__(message, details=details, **kwargs)
        self.config_field = config_field


class MCPToolError(NASAMCPError):
    """Base exception for MCP tool errors."""
    
    def __init__(
        self, 
        message: str = "MCP tool error",
        tool_name: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if tool_name:
            details['tool_name'] = tool_name
        
        kwargs['error_code'] = "mcp_tool_error"
        super().__init__(message, details=details, **kwargs)
        self.tool_name = tool_name


class MCPToolValidationError(MCPToolError):
    """MCP tool parameter validation error."""
    
    def __init__(
        self, 
        message: str = "MCP tool parameter validation failed",
        validation_errors: Optional[list[ValidationErrorDetail]] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if validation_errors:
            details['validation_errors'] = [
                error.dict() for error in validation_errors
            ]
        
        kwargs['error_code'] = "mcp_tool_validation_error"
        super().__init__(message, details=details, **kwargs)
        self.validation_errors = validation_errors


class DataProcessingError(NASAMCPError):
    """Error during data processing or transformation."""
    
    def __init__(
        self, 
        message: str = "Data processing error",
        processing_stage: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if processing_stage:
            details['processing_stage'] = processing_stage
        
        kwargs['error_code'] = "data_processing_error"
        super().__init__(message, details=details, **kwargs)
        self.processing_stage = processing_stage


class CacheError(NASAMCPError):
    """Cache related errors."""
    
    def __init__(
        self, 
        message: str = "Cache error",
        cache_operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if cache_operation:
            details['cache_operation'] = cache_operation
        
        kwargs['error_code'] = "cache_error"
        super().__init__(message, details=details, **kwargs)
        self.cache_operation = cache_operation