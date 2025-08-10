"""
Enhanced logging configuration for error recovery scenarios and data validation results.

This module provides structured logging with context, correlation IDs, and specialized
loggers for different components of the system.
"""

import logging
import logging.config
import json
import time
import uuid
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum

class LogLevel(str, Enum):
    """Extended log levels for specialized logging."""
    DATA_QUALITY = "DATA_QUALITY"
    ERROR_RECOVERY = "ERROR_RECOVERY"
    VALIDATION_RESULT = "VALIDATION_RESULT"
    PERFORMANCE_ALERT = "PERFORMANCE_ALERT"
    USER_ACTION = "USER_ACTION"
    SYSTEM_EVENT = "SYSTEM_EVENT"

@dataclass
class LogContext:
    """Structured logging context."""
    correlation_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    operation: Optional[str] = None
    game_id: Optional[str] = None
    player_id: Optional[str] = None
    component: Optional[str] = None
    additional_data: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        data = asdict(self)
        if self.additional_data:
            data.update(self.additional_data)
        return {k: v for k, v in data.items() if v is not None}

class StructuredFormatter(logging.Formatter):
    """JSON formatter with structured context support."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add context if available
        if hasattr(record, 'context') and record.context:
            if isinstance(record.context, LogContext):
                log_entry['context'] = record.context.to_dict()
            elif isinstance(record.context, dict):
                log_entry['context'] = record.context
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        # Add extra fields from LogRecord
        for key, value in record.__dict__.items():
            if (key not in log_entry and 
                key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                           'filename', 'module', 'lineno', 'funcName', 'created', 
                           'msecs', 'relativeCreated', 'thread', 'threadName',
                           'processName', 'process', 'getMessage', 'context']):
                log_entry[key] = value
        
        return json.dumps(log_entry, default=str, separators=(',', ':'))

class ContextLogger:
    """Logger with built-in context management."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self._context_stack: List[LogContext] = []
    
    def _get_effective_context(self) -> Optional[LogContext]:
        """Get the current effective context."""
        return self._context_stack[-1] if self._context_stack else None
    
    @contextmanager
    def context(self, **kwargs):
        """Context manager for adding logging context."""
        correlation_id = kwargs.get('correlation_id', str(uuid.uuid4()))
        context = LogContext(correlation_id=correlation_id, **kwargs)
        
        self._context_stack.append(context)
        try:
            yield context
        finally:
            self._context_stack.pop()
    
    def _log_with_context(self, level: int, msg: str, *args, **kwargs):
        """Log message with current context."""
        context = kwargs.pop('context', None) or self._get_effective_context()
        
        extra = kwargs.pop('extra', {})
        if context:
            extra['context'] = context
        
        self.logger.log(level, msg, *args, extra=extra, **kwargs)
    
    def debug(self, msg: str, *args, **kwargs):
        """Log debug message with context."""
        self._log_with_context(logging.DEBUG, msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """Log info message with context."""
        self._log_with_context(logging.INFO, msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """Log warning message with context."""
        self._log_with_context(logging.WARNING, msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """Log error message with context."""
        self._log_with_context(logging.ERROR, msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """Log critical message with context."""
        self._log_with_context(logging.CRITICAL, msg, *args, **kwargs)
    
    # Specialized logging methods
    def log_data_quality(self, 
                        data_type: str, 
                        quality_score: float, 
                        issues: List[str], 
                        **kwargs):
        """Log data quality assessment results."""
        msg = f"Data quality assessment: {data_type} (score: {quality_score:.3f})"
        
        extra = kwargs.get('extra', {})
        extra.update({
            'log_type': 'DATA_QUALITY',
            'data_type': data_type,
            'quality_score': quality_score,
            'issues_count': len(issues),
            'issues': issues[:10],  # Limit issues to prevent log spam
        })
        kwargs['extra'] = extra
        
        if quality_score < 0.5:
            self.error(msg, **kwargs)
        elif quality_score < 0.7:
            self.warning(msg, **kwargs)
        else:
            self.info(msg, **kwargs)
    
    def log_error_recovery(self, 
                          error_type: str, 
                          recovery_action: str, 
                          success: bool, 
                          details: Dict[str, Any] = None,
                          **kwargs):
        """Log error recovery attempt and result."""
        status = "successful" if success else "failed"
        msg = f"Error recovery {status}: {error_type} -> {recovery_action}"
        
        extra = kwargs.get('extra', {})
        extra.update({
            'log_type': 'ERROR_RECOVERY',
            'error_type': error_type,
            'recovery_action': recovery_action,
            'recovery_success': success,
            'recovery_details': details or {},
        })
        kwargs['extra'] = extra
        
        if success:
            self.info(msg, **kwargs)
        else:
            self.error(msg, **kwargs)
    
    def log_validation_result(self, 
                            validator_name: str, 
                            data_id: str, 
                            is_valid: bool, 
                            errors: List[str] = None,
                            confidence: Optional[float] = None,
                            **kwargs):
        """Log validation result with details."""
        status = "passed" if is_valid else "failed"
        msg = f"Validation {status}: {validator_name} for {data_id}"
        
        extra = kwargs.get('extra', {})
        extra.update({
            'log_type': 'VALIDATION_RESULT',
            'validator_name': validator_name,
            'data_id': data_id,
            'validation_passed': is_valid,
            'error_count': len(errors or []),
            'validation_errors': errors or [],
            'confidence_level': confidence,
        })
        kwargs['extra'] = extra
        
        if is_valid:
            self.info(msg, **kwargs)
        else:
            self.warning(msg, **kwargs)
    
    def log_performance_alert(self, 
                            operation: str, 
                            duration_ms: float, 
                            threshold_ms: float,
                            severity: str = "medium",
                            **kwargs):
        """Log performance threshold exceeded."""
        msg = f"Performance alert: {operation} took {duration_ms:.2f}ms (threshold: {threshold_ms:.2f}ms)"
        
        extra = kwargs.get('extra', {})
        extra.update({
            'log_type': 'PERFORMANCE_ALERT',
            'operation': operation,
            'duration_ms': duration_ms,
            'threshold_ms': threshold_ms,
            'slowdown_factor': duration_ms / threshold_ms if threshold_ms > 0 else float('inf'),
            'alert_severity': severity,
        })
        kwargs['extra'] = extra
        
        if severity == "critical":
            self.critical(msg, **kwargs)
        elif severity == "high":
            self.error(msg, **kwargs)
        else:
            self.warning(msg, **kwargs)
    
    def log_user_action(self, 
                       action: str, 
                       user_id: str, 
                       success: bool, 
                       details: Dict[str, Any] = None,
                       **kwargs):
        """Log user action for audit trail."""
        status = "completed" if success else "failed"
        msg = f"User action {status}: {action} by {user_id}"
        
        extra = kwargs.get('extra', {})
        extra.update({
            'log_type': 'USER_ACTION',
            'action': action,
            'user_id': user_id,
            'action_success': success,
            'action_details': details or {},
        })
        kwargs['extra'] = extra
        
        self.info(msg, **kwargs)
    
    def log_system_event(self, 
                        event_type: str, 
                        description: str, 
                        metadata: Dict[str, Any] = None,
                        **kwargs):
        """Log system event for monitoring."""
        msg = f"System event: {event_type} - {description}"
        
        extra = kwargs.get('extra', {})
        extra.update({
            'log_type': 'SYSTEM_EVENT',
            'event_type': event_type,
            'description': description,
            'event_metadata': metadata or {},
        })
        kwargs['extra'] = extra
        
        self.info(msg, **kwargs)

class LoggingConfig:
    """Centralized logging configuration."""
    
    @staticmethod
    def setup_logging(
        log_level: str = "INFO",
        log_file: Optional[str] = None,
        structured_logging: bool = True,
        console_output: bool = True
    ) -> Dict[str, ContextLogger]:
        """Setup comprehensive logging configuration."""
        
        # Determine formatter
        if structured_logging:
            formatter_class = "enhanced_logging.StructuredFormatter"
            format_string = ""  # Not used for structured formatter
        else:
            formatter_class = "logging.Formatter"
            format_string = (
                "%(asctime)s - %(name)s - %(levelname)s - "
                "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
            )
        
        # Base logging configuration
        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "detailed": {
                    "class": formatter_class,
                    "format": format_string,
                },
            },
            "handlers": {},
            "loggers": {},
            "root": {
                "level": log_level,
                "handlers": [],
            },
        }
        
        # Console handler
        if console_output:
            config["handlers"]["console"] = {
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "detailed",
                "stream": "ext://sys.stdout",
            }
            config["root"]["handlers"].append("console")
        
        # File handler
        if log_file:
            config["handlers"]["file"] = {
                "class": "logging.handlers.RotatingFileHandler",
                "level": log_level,
                "formatter": "detailed",
                "filename": log_file,
                "maxBytes": 100 * 1024 * 1024,  # 100MB
                "backupCount": 10,
                "encoding": "utf-8",
            }
            config["root"]["handlers"].append("file")
        
        # Specialized loggers
        specialized_loggers = {
            "data_quality": "game_arena.data_quality",
            "error_recovery": "game_arena.error_recovery", 
            "validation": "game_arena.validation",
            "performance": "game_arena.performance",
            "user_actions": "game_arena.user_actions",
            "system_events": "game_arena.system_events",
            "chess_board": "game_arena.chess_board",
            "statistics": "game_arena.statistics",
            "api": "game_arena.api",
            "database": "game_arena.database",
            "cache": "game_arena.cache",
        }
        
        for name, logger_name in specialized_loggers.items():
            config["loggers"][logger_name] = {
                "level": log_level,
                "handlers": config["root"]["handlers"][:],  # Copy handlers
                "propagate": False,
            }
        
        # Apply configuration
        logging.config.dictConfig(config)
        
        # Create context loggers
        context_loggers = {}
        for name, logger_name in specialized_loggers.items():
            context_loggers[name] = ContextLogger(logger_name)
        
        # Add general logger
        context_loggers["general"] = ContextLogger("game_arena.general")
        
        return context_loggers

# Decorator for automatic context logging
def log_function_calls(logger_name: str = "general"):
    """Decorator to automatically log function entry/exit."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get logger (this will need to be passed in or retrieved from a global registry)
            logger = ContextLogger(f"game_arena.{logger_name}")
            
            correlation_id = str(uuid.uuid4())
            function_name = f"{func.__module__}.{func.__name__}"
            
            with logger.context(
                correlation_id=correlation_id,
                operation=function_name,
                component=func.__module__
            ):
                start_time = time.time()
                
                logger.debug(f"Function entry: {function_name}")
                
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    
                    logger.debug(
                        f"Function exit: {function_name} (duration: {duration_ms:.2f}ms)",
                        extra={'execution_time_ms': duration_ms}
                    )
                    
                    return result
                    
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    
                    logger.error(
                        f"Function error: {function_name} - {str(e)} (duration: {duration_ms:.2f}ms)",
                        extra={
                            'execution_time_ms': duration_ms,
                            'error_type': type(e).__name__,
                            'error_message': str(e),
                        },
                        exc_info=True
                    )
                    
                    raise
        
        return wrapper
    return decorator

# Global logger registry
_logger_registry: Dict[str, ContextLogger] = {}

def get_logger(name: str) -> ContextLogger:
    """Get or create a context logger."""
    if name not in _logger_registry:
        _logger_registry[name] = ContextLogger(f"game_arena.{name}")
    return _logger_registry[name]

def initialize_logging(config_file: Optional[str] = None, **kwargs) -> Dict[str, ContextLogger]:
    """Initialize logging system with configuration."""
    if config_file:
        with open(config_file, 'r') as f:
            config = json.load(f)
        logging.config.dictConfig(config)
        
        # Create context loggers based on config
        loggers = {}
        for logger_name in config.get("loggers", {}):
            short_name = logger_name.replace("game_arena.", "")
            loggers[short_name] = ContextLogger(logger_name)
        
        return loggers
    else:
        return LoggingConfig.setup_logging(**kwargs)

# Export main components
__all__ = [
    'LogContext',
    'ContextLogger',
    'LoggingConfig',
    'StructuredFormatter',
    'get_logger',
    'initialize_logging',
    'log_function_calls',
    'LogLevel',
]