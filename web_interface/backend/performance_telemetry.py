"""
Performance telemetry and monitoring for backend operations.

This module provides comprehensive performance monitoring for statistics calculations,
API responses, database operations, and other backend processes.
"""

import time
import logging
import asyncio
import threading
import psutil
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import contextlib

from fastapi import Request, Response
from fastapi.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

class MetricCategory(str, Enum):
    """Performance metric categories."""
    API_RESPONSE = "api_response"
    STATISTICS_CALCULATION = "statistics_calculation"
    DATABASE_QUERY = "database_query"
    CACHE_OPERATION = "cache_operation"
    BATCH_PROCESSING = "batch_processing"
    ERROR_RECOVERY = "error_recovery"
    SYSTEM_RESOURCE = "system_resource"

@dataclass
class PerformanceMetric:
    """Performance metric data structure."""
    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    category: MetricCategory = MetricCategory.API_RESPONSE
    metadata: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary for serialization."""
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp.isoformat(),
            'category': self.category.value,
            'metadata': self.metadata,
            'session_id': self.session_id,
            'user_agent': self.user_agent,
        }

class PerformanceTelemetry:
    """Central performance telemetry system."""
    
    def __init__(self, max_metrics: int = 10000):
        self.metrics: deque[PerformanceMetric] = deque(maxlen=max_metrics)
        self._timers: Dict[str, float] = {}
        self._lock = threading.RLock()
        self._background_task = None
        self._running = True
        self._alert_thresholds = {
            'api_response_time': 1000,      # 1 second
            'statistics_calculation': 5000,  # 5 seconds
            'database_query': 2000,         # 2 seconds
            'memory_usage': 0.8,            # 80%
            'cpu_usage': 0.9,               # 90%
        }
        
        self._start_background_monitoring()
    
    def _start_background_monitoring(self):
        """Start background system monitoring."""
        def monitor_system_resources():
            while self._running:
                try:
                    # Monitor system resources
                    cpu_percent = psutil.cpu_percent(interval=1)
                    memory_info = psutil.virtual_memory()
                    disk_usage = psutil.disk_usage('/')
                    
                    # Record system metrics
                    self.record_metric(
                        name='cpu_usage',
                        value=cpu_percent,
                        category=MetricCategory.SYSTEM_RESOURCE,
                        metadata={
                            'cpu_count': psutil.cpu_count(),
                            'load_average': psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None,
                        }
                    )
                    
                    self.record_metric(
                        name='memory_usage',
                        value=memory_info.percent,
                        category=MetricCategory.SYSTEM_RESOURCE,
                        metadata={
                            'total_gb': round(memory_info.total / 1024**3, 2),
                            'available_gb': round(memory_info.available / 1024**3, 2),
                            'used_gb': round(memory_info.used / 1024**3, 2),
                        }
                    )
                    
                    self.record_metric(
                        name='disk_usage',
                        value=disk_usage.percent,
                        category=MetricCategory.SYSTEM_RESOURCE,
                        metadata={
                            'total_gb': round(disk_usage.total / 1024**3, 2),
                            'free_gb': round(disk_usage.free / 1024**3, 2),
                            'used_gb': round(disk_usage.used / 1024**3, 2),
                        }
                    )
                    
                    # Check alert thresholds
                    self._check_alert_thresholds({
                        'cpu_usage': cpu_percent,
                        'memory_usage': memory_info.percent,
                        'disk_usage': disk_usage.percent,
                    })
                    
                    # Cleanup old metrics (keep last 24 hours)
                    self._cleanup_old_metrics()
                    
                except Exception as e:
                    logger.error(f"Error in background monitoring: {e}")
                
                time.sleep(60)  # Monitor every minute
        
        self._background_task = threading.Thread(target=monitor_system_resources, daemon=True)
        self._background_task.start()
    
    def start_timer(self, operation_id: str) -> None:
        """Start timing an operation."""
        with self._lock:
            self._timers[operation_id] = time.time()
    
    def end_timer(self, 
                  operation_id: str, 
                  category: MetricCategory,
                  metadata: Optional[Dict[str, Any]] = None) -> float:
        """End timing an operation and record the metric."""
        with self._lock:
            start_time = self._timers.pop(operation_id, None)
            if start_time is None:
                logger.warning(f"No start time found for operation: {operation_id}")
                return 0.0
            
            duration_ms = (time.time() - start_time) * 1000
            
            self.record_metric(
                name=operation_id,
                value=duration_ms,
                category=category,
                metadata=metadata or {}
            )
            
            # Check for performance issues
            self._check_performance_threshold(operation_id, duration_ms, category)
            
            return duration_ms
    
    def record_metric(self, 
                     name: str,
                     value: float,
                     category: MetricCategory,
                     metadata: Optional[Dict[str, Any]] = None,
                     session_id: Optional[str] = None,
                     user_agent: Optional[str] = None) -> None:
        """Record a performance metric."""
        metric = PerformanceMetric(
            name=name,
            value=value,
            category=category,
            metadata=metadata or {},
            session_id=session_id,
            user_agent=user_agent,
        )
        
        with self._lock:
            self.metrics.append(metric)
        
        logger.debug(f"Recorded metric: {name} = {value} ({category.value})")
    
    def _check_performance_threshold(self, operation: str, duration_ms: float, category: MetricCategory):
        """Check if operation exceeded performance thresholds."""
        threshold_key = None
        
        if category == MetricCategory.API_RESPONSE:
            threshold_key = 'api_response_time'
        elif category == MetricCategory.STATISTICS_CALCULATION:
            threshold_key = 'statistics_calculation'
        elif category == MetricCategory.DATABASE_QUERY:
            threshold_key = 'database_query'
        
        if threshold_key and threshold_key in self._alert_thresholds:
            threshold = self._alert_thresholds[threshold_key]
            if duration_ms > threshold:
                logger.warning(
                    f"Performance threshold exceeded: {operation} took {duration_ms:.2f}ms "
                    f"(threshold: {threshold}ms)"
                )
                
                # Record performance alert
                self.record_metric(
                    name='performance_alert',
                    value=duration_ms,
                    category=category,
                    metadata={
                        'operation': operation,
                        'threshold': threshold,
                        'severity': 'high' if duration_ms > threshold * 2 else 'medium'
                    }
                )
    
    def _check_alert_thresholds(self, current_values: Dict[str, float]):
        """Check system resource alert thresholds."""
        for metric_name, value in current_values.items():
            if metric_name in self._alert_thresholds:
                threshold = self._alert_thresholds[metric_name]
                
                # Convert percentage to 0-1 scale for comparison
                normalized_value = value / 100 if metric_name.endswith('_usage') else value
                
                if normalized_value > threshold:
                    logger.warning(f"System alert: {metric_name} = {value}% (threshold: {threshold*100}%)")
                    
                    self.record_metric(
                        name='system_alert',
                        value=value,
                        category=MetricCategory.SYSTEM_RESOURCE,
                        metadata={
                            'metric': metric_name,
                            'threshold': threshold * 100,
                            'severity': 'critical' if normalized_value > threshold * 1.2 else 'warning'
                        }
                    )
    
    def _cleanup_old_metrics(self):
        """Remove metrics older than 24 hours."""
        cutoff = datetime.now() - timedelta(hours=24)
        
        with self._lock:
            # Convert deque to list, filter, and recreate deque
            recent_metrics = [m for m in self.metrics if m.timestamp > cutoff]
            self.metrics.clear()
            self.metrics.extend(recent_metrics)
    
    @contextlib.contextmanager
    def measure(self, 
                operation_name: str, 
                category: MetricCategory,
                metadata: Optional[Dict[str, Any]] = None):
        """Context manager for measuring operation duration."""
        operation_id = f"{operation_name}_{int(time.time() * 1000)}"
        self.start_timer(operation_id)
        
        try:
            yield operation_id
        except Exception as e:
            # Record error metrics
            self.record_metric(
                name=f"{operation_name}_error",
                value=1,
                category=category,
                metadata={
                    'error_type': type(e).__name__,
                    'error_message': str(e),
                    **(metadata or {})
                }
            )
            raise
        finally:
            self.end_timer(operation_id, category, metadata)
    
    def get_metrics(self, 
                   category: Optional[MetricCategory] = None,
                   since: Optional[datetime] = None,
                   limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recorded metrics with optional filtering."""
        with self._lock:
            filtered_metrics = list(self.metrics)
        
        if category:
            filtered_metrics = [m for m in filtered_metrics if m.category == category]
        
        if since:
            filtered_metrics = [m for m in filtered_metrics if m.timestamp > since]
        
        # Sort by timestamp (newest first)
        filtered_metrics.sort(key=lambda m: m.timestamp, reverse=True)
        
        if limit:
            filtered_metrics = filtered_metrics[:limit]
        
        return [m.to_dict() for m in filtered_metrics]
    
    def get_performance_summary(self, window_minutes: int = 60) -> Dict[str, Any]:
        """Get performance summary for the specified time window."""
        since = datetime.now() - timedelta(minutes=window_minutes)
        recent_metrics = [m for m in self.metrics if m.timestamp > since]
        
        if not recent_metrics:
            return {
                'window_minutes': window_minutes,
                'total_metrics': 0,
                'categories': {},
                'alerts': 0,
            }
        
        # Group metrics by category
        by_category = defaultdict(list)
        alerts = 0
        
        for metric in recent_metrics:
            by_category[metric.category.value].append(metric.value)
            if metric.name in ['performance_alert', 'system_alert']:
                alerts += 1
        
        # Calculate statistics for each category
        summary = {
            'window_minutes': window_minutes,
            'total_metrics': len(recent_metrics),
            'alerts': alerts,
            'categories': {}
        }
        
        for category, values in by_category.items():
            summary['categories'][category] = {
                'count': len(values),
                'avg': sum(values) / len(values),
                'min': min(values),
                'max': max(values),
                'p95': sorted(values)[int(len(values) * 0.95)] if len(values) > 20 else max(values),
            }
        
        return summary
    
    def shutdown(self):
        """Shutdown the telemetry system."""
        self._running = False
        if self._background_task and self._background_task.is_alive():
            self._background_task.join(timeout=5.0)

# Global telemetry instance
telemetry = PerformanceTelemetry()

# Middleware for automatic API monitoring
class PerformanceMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for automatic performance monitoring."""
    
    async def dispatch(self, request: Request, call_next):
        """Monitor API request performance."""
        start_time = time.time()
        operation_id = f"api_{request.method}_{request.url.path.replace('/', '_')}"
        
        # Extract session information
        session_id = request.headers.get('X-Session-ID')
        user_agent = request.headers.get('User-Agent')
        
        response = None
        error = None
        
        try:
            response = await call_next(request)
        except Exception as e:
            error = e
            # Create error response
            from fastapi import HTTPException
            from fastapi.responses import JSONResponse
            
            if isinstance(e, HTTPException):
                response = JSONResponse(
                    status_code=e.status_code,
                    content={"error": e.detail}
                )
            else:
                response = JSONResponse(
                    status_code=500,
                    content={"error": "Internal server error"}
                )
        
        # Record performance metrics
        duration_ms = (time.time() - start_time) * 1000
        
        telemetry.record_metric(
            name=operation_id,
            value=duration_ms,
            category=MetricCategory.API_RESPONSE,
            metadata={
                'method': request.method,
                'path': str(request.url.path),
                'status_code': response.status_code if response else 500,
                'query_params': dict(request.query_params),
                'error': str(error) if error else None,
                'request_size': request.headers.get('Content-Length', 0),
                'response_size': len(response.body) if hasattr(response, 'body') else 0,
            },
            session_id=session_id,
            user_agent=user_agent,
        )
        
        # Add performance headers to response
        if response:
            response.headers['X-Response-Time'] = f"{duration_ms:.2f}ms"
            response.headers['X-Request-ID'] = operation_id
        
        return response

# Decorator for measuring function performance
def measure_performance(category: MetricCategory, metadata_func: Optional[Callable] = None):
    """Decorator for measuring function performance."""
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            metadata = metadata_func(*args, **kwargs) if metadata_func else None
            
            with telemetry.measure(operation_name, category, metadata):
                return await func(*args, **kwargs)
        
        def sync_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            metadata = metadata_func(*args, **kwargs) if metadata_func else None
            
            with telemetry.measure(operation_name, category, metadata):
                return func(*args, **kwargs)
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator

# Specialized decorators for common operations
def measure_statistics_calculation(func):
    """Decorator for statistics calculation functions."""
    return measure_performance(MetricCategory.STATISTICS_CALCULATION)(func)

def measure_database_query(func):
    """Decorator for database query functions."""
    return measure_performance(MetricCategory.DATABASE_QUERY)(func)

def measure_cache_operation(func):
    """Decorator for cache operations."""
    return measure_performance(MetricCategory.CACHE_OPERATION)(func)

def measure_batch_processing(func):
    """Decorator for batch processing operations."""
    return measure_performance(MetricCategory.BATCH_PROCESSING)(func)

# Export the telemetry instance and utilities
__all__ = [
    'telemetry',
    'PerformanceMiddleware', 
    'measure_performance',
    'measure_statistics_calculation',
    'measure_database_query',
    'measure_cache_operation',
    'measure_batch_processing',
    'MetricCategory',
    'PerformanceMetric',
]