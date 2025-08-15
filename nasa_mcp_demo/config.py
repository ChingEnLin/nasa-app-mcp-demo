"""Configuration management for NASA MCP Demo application."""

from typing import List
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NASAConfig(BaseModel):
    """Configuration for NASA API integration."""
    
    api_key: str = Field(default="DEMO_KEY", description="NASA API key")
    base_url: str = Field(default="https://api.nasa.gov", description="NASA API base URL")
    timeout: int = Field(default=30, description="Request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum retry attempts")
    rate_limit_per_hour: int = Field(default=1000, description="Rate limit per hour")


class AppConfig(BaseSettings):
    """Main application configuration."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # NASA API Configuration
    nasa_api_key: str = Field(default="DEMO_KEY", alias="NASA_API_KEY")
    nasa_base_url: str = Field(default="https://api.nasa.gov", alias="NASA_BASE_URL")
    nasa_timeout: int = Field(default=30, alias="NASA_TIMEOUT")
    nasa_max_retries: int = Field(default=3, alias="NASA_MAX_RETRIES")
    nasa_rate_limit_per_hour: int = Field(default=1000, alias="NASA_RATE_LIMIT_PER_HOUR")
    
    # Application Configuration
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    enable_mcp: bool = Field(default=False, alias="ENABLE_MCP")
    cors_origins: List[str] = Field(default=["*"], alias="CORS_ORIGINS")
    debug: bool = Field(default=False, alias="DEBUG")
    
    @property
    def nasa_config(self) -> NASAConfig:
        """Get NASA API configuration."""
        return NASAConfig(
            api_key=self.nasa_api_key,
            base_url=self.nasa_base_url,
            timeout=self.nasa_timeout,
            max_retries=self.nasa_max_retries,
            rate_limit_per_hour=self.nasa_rate_limit_per_hour,
        )


# Global configuration instance
config = AppConfig()