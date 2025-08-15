"""
Configuration models for the NASA MCP Demo application.

This module contains Pydantic models for application configuration,
including NASA API settings and general application settings.
"""

from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from pydantic_settings import BaseSettings


class NASAConfig(BaseModel):
    """Configuration for NASA API client."""
    
    api_key: str = Field(
        default="DEMO_KEY",
        description="NASA API key (use DEMO_KEY for limited access)"
    )
    base_url: HttpUrl = Field(
        default="https://api.nasa.gov",
        description="Base URL for NASA API"
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
        ge=1,
        le=300
    )
    max_retries: int = Field(
        default=3,
        description="Maximum number of retry attempts",
        ge=0,
        le=10
    )
    rate_limit_per_hour: int = Field(
        default=1000,
        description="Rate limit per hour (DEMO_KEY limit is 1000)",
        ge=1
    )
    retry_backoff_factor: float = Field(
        default=1.0,
        description="Backoff factor for exponential retry",
        ge=0.1,
        le=10.0
    )
    retry_backoff_factor: float = Field(
        default=1.0,
        description="Backoff factor for exponential retry",
        ge=0.1,
        le=10.0
    )
    
    @field_validator('api_key')
    @classmethod
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v or len(v.strip()) == 0:
            raise ValueError('api_key cannot be empty')
        return v.strip()


class LoggingConfig(BaseModel):
    """Configuration for application logging."""
    
    level: str = Field(
        default="INFO",
        description="Logging level"
    )
    format: str = Field(
        default="json",
        description="Log format (json or text)"
    )
    enable_request_logging: bool = Field(
        default=True,
        description="Enable HTTP request/response logging"
    )
    enable_nasa_api_logging: bool = Field(
        default=True,
        description="Enable NASA API call logging"
    )
    
    @field_validator('level')
    @classmethod
    def validate_log_level(cls, v):
        """Validate logging level."""
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'level must be one of: {", ".join(valid_levels)}')
        return v.upper()
    
    @field_validator('format')
    @classmethod
    def validate_log_format(cls, v):
        """Validate log format."""
        valid_formats = ['json', 'text']
        if v.lower() not in valid_formats:
            raise ValueError(f'format must be one of: {", ".join(valid_formats)}')
        return v.lower()


class CacheConfig(BaseModel):
    """Configuration for caching."""
    
    enable_caching: bool = Field(
        default=True,
        description="Enable response caching"
    )
    apod_cache_ttl: int = Field(
        default=3600,
        description="APOD cache TTL in seconds",
        ge=60
    )
    mars_photos_cache_ttl: int = Field(
        default=7200,
        description="Mars photos cache TTL in seconds",
        ge=60
    )
    neo_cache_ttl: int = Field(
        default=1800,
        description="NEO data cache TTL in seconds",
        ge=60
    )
    max_cache_size: int = Field(
        default=1000,
        description="Maximum number of cached items",
        ge=10
    )


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    # Application settings
    app_name: str = Field(
        default="NASA MCP Demo",
        description="Application name"
    )
    app_version: str = Field(
        default="1.0.0",
        description="Application version"
    )
    debug: bool = Field(
        default=False,
        description="Enable debug mode"
    )
    
    # Server settings
    host: str = Field(
        default="0.0.0.0",
        description="Server host"
    )
    port: int = Field(
        default=8000,
        description="Server port",
        ge=1,
        le=65535
    )
    
    # CORS settings
    cors_origins: List[str] = Field(
        default=["*"],
        description="Allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(
        default=True,
        description="Allow CORS credentials"
    )
    cors_allow_methods: List[str] = Field(
        default=["*"],
        description="Allowed CORS methods"
    )
    cors_allow_headers: List[str] = Field(
        default=["*"],
        description="Allowed CORS headers"
    )
    
    # MCP settings
    enable_mcp: bool = Field(
        default=False,
        description="Enable MCP server functionality"
    )
    mcp_server_name: str = Field(
        default="nasa-mcp-demo",
        description="MCP server name"
    )
    
    # Component configurations
    nasa: NASAConfig = Field(
        default_factory=NASAConfig,
        description="NASA API configuration"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Cache configuration"
    )
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        case_sensitive=False,
        env_prefix="NASA_MCP_"
    )
    
    @field_validator('cors_origins')
    @classmethod
    def validate_cors_origins(cls, v):
        """Validate CORS origins."""
        if not v:
            return ["*"]
        
        # Validate each origin
        for origin in v:
            if origin != "*" and not origin.startswith(("http://", "https://")):
                raise ValueError(f'Invalid CORS origin: {origin}')
        
        return v
    
    def get_nasa_api_key(self) -> str:
        """Get the NASA API key, with fallback to DEMO_KEY."""
        return self.nasa.api_key if self.nasa.api_key != "DEMO_KEY" else "DEMO_KEY"
    
    def is_demo_mode(self) -> bool:
        """Check if running in demo mode (using DEMO_KEY)."""
        return self.nasa.api_key == "DEMO_KEY"
    
    def get_server_url(self) -> str:
        """Get the full server URL."""
        protocol = "https" if not self.debug else "http"
        return f"{protocol}://{self.host}:{self.port}"