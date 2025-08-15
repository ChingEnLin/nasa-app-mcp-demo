"""
Middleware for NASA MCP Demo application.

This module contains FastAPI middleware for logging, monitoring,
and request/response tracking.
"""

import time
import uuid
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from fastapi import Request, Response
from fastapi.responses import JSONResponse
import structlog

from .logging_config import get_logging_config, PerformanceMonitor, ErrorTracker
from .models.errors import NASAAPIError


logger = structlog.get_logger(__name__)


class RequestLoggingMiddleware:
    """Middleware for comprehensive request/response logging."""
    
    def __init__(self, app):
        self.app = app
        self.performance_monitor = PerformanceMonitor(logger)
        self.error_tracker = ErrorTracker(logger)
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        
        # Add request ID for tracking
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        
        # Get logging configuration
        logging_config = get_logging_config()
        
        # Start performance monitoring
        start_time = time.time()
        
        # Log request start
        if logging_config.get("enable_request_logging", True):
            await self._log_request_start(request, request_id)
        
        # Process request
        response = None
        error = None
        
        try:
            # Create response wrapper to capture response data
            response_data = {}
            
            async def send_wrapper(message):
                if message["type"] == "http.response.start":
                    response_data["status_code"] = message["status"]
                    response_data["headers"] = dict(message.get("headers", []))
                elif message["type"] == "http.response.body":
                    response_data["body"] = message.get("body", b"")
                await send(message)
            
            await self.app(scope, receive, send_wrapper)
            
            # Calculate duration
            duration_seconds = time.time() - start_time
            duration_ms = duration_seconds * 1000
            
            # Log successful response
            if logging_config.get("enable_request_logging", True):
                await self._log_request_success(
                    request,
                    request_id,
                    response_data.get("status_code", 200),
                    duration_ms,
                    len(response_data.get("body", b""))
                )
            
        except Exception as e:
            error = e
            duration_seconds = time.time() - start_time
            duration_ms = duration_seconds * 1000
            
            # Log error
            if logging_config.get("enable_request_logging", True):
                await self._log_request_error(request, request_id, error, duration_ms)
            
            # Track error for debugging
            if logging_config.get("enable_error_tracking", True):
                self.error_tracker.track_error(
                    error,
                    context="request_processing",
                    request_id=request_id,
                    path=request.url.path,
                    method=request.method
                )
            
            # Re-raise the exception
            raise
    
    async def _log_request_start(self, request: Request, request_id: str):
        """Log request start."""
        # Get client information
        client_ip = None
        if request.client:
            client_ip = request.client.host
        
        # Get user agent
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Get request size
        content_length = request.headers.get("content-length")
        request_size = int(content_length) if content_length else 0
        
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": client_ip,
            "user_agent": user_agent,
            "request_size_bytes": request_size,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add request body if configured (be careful with sensitive data)
        logging_config = get_logging_config()
        if logging_config.get("log_request_body", False) and request_size > 0:
            try:
                # This is a simplified approach - in production, you'd want to
                # be more careful about reading the body without consuming it
                log_data["request_body_logged"] = True
            except Exception:
                log_data["request_body_error"] = "failed_to_read"
        
        logger.info("HTTP request started", **log_data)
    
    async def _log_request_success(
        self,
        request: Request,
        request_id: str,
        status_code: int,
        duration_ms: float,
        response_size: int
    ):
        """Log successful request completion."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
            "duration_seconds": round(duration_ms / 1000, 3),
            "response_size_bytes": response_size,
            "timestamp": datetime.now().isoformat()
        }
        
        # Add performance warnings
        logging_config = get_logging_config()
        performance_threshold = logging_config.get("performance_threshold_ms", 1000)
        slow_threshold = logging_config.get("slow_operation_threshold_ms", 5000)
        
        if duration_ms > slow_threshold:
            log_data["performance_warning"] = "slow_request"
            log_level = "warning"
        elif duration_ms > performance_threshold:
            log_data["performance_info"] = "moderate_duration"
            log_level = "info"
        else:
            log_level = "info"
        
        # Add status code category
        if 200 <= status_code < 300:
            log_data["status_category"] = "success"
        elif 300 <= status_code < 400:
            log_data["status_category"] = "redirect"
        elif 400 <= status_code < 500:
            log_data["status_category"] = "client_error"
            log_level = "warning"
        else:
            log_data["status_category"] = "server_error"
            log_level = "error"
        
        getattr(logger, log_level)("HTTP request completed", **log_data)
    
    async def _log_request_error(
        self,
        request: Request,
        request_id: str,
        error: Exception,
        duration_ms: float
    ):
        """Log request error."""
        log_data = {
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "duration_ms": round(duration_ms, 2),
            "duration_seconds": round(duration_ms / 1000, 3),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add error categorization
        if isinstance(error, NASAAPIError):
            log_data["error_category"] = "nasa_api"
        elif isinstance(error, ValueError):
            log_data["error_category"] = "validation"
        elif isinstance(error, (ConnectionError, TimeoutError)):
            log_data["error_category"] = "network"
        else:
            log_data["error_category"] = "unknown"
        
        logger.error("HTTP request failed", **log_data, exc_info=True)


class PerformanceMonitoringMiddleware:
    """Middleware for performance monitoring and metrics collection."""
    
    def __init__(self, app):
        self.app = app
        self.request_metrics: Dict[str, Any] = {
            "total_requests": 0,
            "total_errors": 0,
            "total_duration_ms": 0.0,
            "endpoint_metrics": {}
        }
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        request = Request(scope, receive)
        endpoint = f"{request.method} {request.url.path}"
        
        # Initialize endpoint metrics if not exists
        if endpoint not in self.request_metrics["endpoint_metrics"]:
            self.request_metrics["endpoint_metrics"][endpoint] = {
                "count": 0,
                "errors": 0,
                "total_duration_ms": 0.0,
                "min_duration_ms": float('inf'),
                "max_duration_ms": 0.0,
                "avg_duration_ms": 0.0
            }
        
        start_time = time.time()
        error_occurred = False
        
        try:
            await self.app(scope, receive, send)
        except Exception as e:
            error_occurred = True
            raise
        finally:
            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000
            
            # Update metrics
            self._update_metrics(endpoint, duration_ms, error_occurred)
            
            # Log performance metrics periodically
            if self.request_metrics["total_requests"] % 100 == 0:
                self._log_performance_summary()
    
    def _update_metrics(self, endpoint: str, duration_ms: float, error_occurred: bool):
        """Update performance metrics."""
        # Update global metrics
        self.request_metrics["total_requests"] += 1
        self.request_metrics["total_duration_ms"] += duration_ms
        
        if error_occurred:
            self.request_metrics["total_errors"] += 1
        
        # Update endpoint metrics
        endpoint_metrics = self.request_metrics["endpoint_metrics"][endpoint]
        endpoint_metrics["count"] += 1
        endpoint_metrics["total_duration_ms"] += duration_ms
        
        if error_occurred:
            endpoint_metrics["errors"] += 1
        
        # Update min/max duration
        endpoint_metrics["min_duration_ms"] = min(
            endpoint_metrics["min_duration_ms"], duration_ms
        )
        endpoint_metrics["max_duration_ms"] = max(
            endpoint_metrics["max_duration_ms"], duration_ms
        )
        
        # Calculate average duration
        endpoint_metrics["avg_duration_ms"] = (
            endpoint_metrics["total_duration_ms"] / endpoint_metrics["count"]
        )
    
    def _log_performance_summary(self):
        """Log performance summary."""
        total_requests = self.request_metrics["total_requests"]
        total_errors = self.request_metrics["total_errors"]
        avg_duration = (
            self.request_metrics["total_duration_ms"] / total_requests
            if total_requests > 0 else 0
        )
        error_rate = (total_errors / total_requests * 100) if total_requests > 0 else 0
        
        logger.info(
            "Performance summary",
            total_requests=total_requests,
            total_errors=total_errors,
            error_rate_percent=round(error_rate, 2),
            avg_duration_ms=round(avg_duration, 2),
            endpoint_count=len(self.request_metrics["endpoint_metrics"])
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        return self.request_metrics.copy()


class HealthCheckMiddleware:
    """Middleware for health monitoring and status tracking."""
    
    def __init__(self, app):
        self.app = app
        self.health_status = {
            "status": "healthy",
            "last_error": None,
            "error_count": 0,
            "uptime_start": datetime.now(),
            "last_health_check": None
        }
    
    async def __call__(self, scope, receive, send):
        """ASGI middleware implementation."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        
        try:
            await self.app(scope, receive, send)
            # Reset error status on successful requests
            if self.health_status["status"] == "unhealthy":
                self.health_status["status"] = "recovering"
        except Exception as e:
            # Track errors for health monitoring
            self.health_status["error_count"] += 1
            self.health_status["last_error"] = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "type": type(e).__name__
            }
            
            # Mark as unhealthy if too many errors
            if self.health_status["error_count"] > 10:
                self.health_status["status"] = "unhealthy"
            
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status."""
        uptime = datetime.now() - self.health_status["uptime_start"]
        
        return {
            **self.health_status,
            "uptime_seconds": int(uptime.total_seconds()),
            "uptime_human": str(uptime).split('.')[0]  # Remove microseconds
        }