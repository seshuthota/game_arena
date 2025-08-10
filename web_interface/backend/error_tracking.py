"""
Error tracking and reporting system for data quality issues and user problems.

This module provides comprehensive error tracking, categorization, and reporting
capabilities for both automated error detection and user-reported issues.
"""

import logging
import json
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict, Counter
import traceback
import hashlib

from fastapi import HTTPException, Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class ErrorCategory(str, Enum):
    """Error categories for classification."""
    DATA_QUALITY = "data_quality"
    VALIDATION = "validation"
    PERFORMANCE = "performance"
    USER_INTERFACE = "user_interface"
    API = "api"
    DATABASE = "database"
    CACHE = "cache"
    SYSTEM = "system"
    USER_REPORTED = "user_reported"

class ErrorSource(str, Enum):
    """Source of error detection."""
    AUTOMATIC = "automatic"
    USER_REPORT = "user_report"
    MONITORING = "monitoring"
    VALIDATION = "validation"
    EXCEPTION_HANDLER = "exception_handler"

@dataclass
class ErrorContext:
    """Context information for an error."""
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    user_agent: Optional[str] = None
    url: Optional[str] = None
    request_id: Optional[str] = None
    game_id: Optional[str] = None
    player_id: Optional[str] = None
    operation: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None
    additional_data: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ErrorReport:
    """Comprehensive error report structure."""
    error_id: str
    timestamp: datetime
    category: ErrorCategory
    severity: ErrorSeverity
    source: ErrorSource
    title: str
    description: str
    context: ErrorContext
    error_hash: str
    count: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolution_notes: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error report to dictionary."""
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'first_seen': self.first_seen.isoformat(),
            'last_seen': self.last_seen.isoformat(),
        }

class UserErrorReport(BaseModel):
    """User-submitted error report."""
    title: str
    description: str
    steps_to_reproduce: Optional[str] = None
    expected_behavior: Optional[str] = None
    actual_behavior: Optional[str] = None
    browser_info: Optional[Dict[str, Any]] = None
    screenshot_url: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    category: ErrorCategory = ErrorCategory.USER_INTERFACE
    context: Optional[Dict[str, Any]] = None

class ErrorTracker:
    """Central error tracking and management system."""
    
    def __init__(self, max_errors: int = 50000):
        self.errors: Dict[str, ErrorReport] = {}
        self.error_patterns: Dict[str, List[str]] = defaultdict(list)
        self.max_errors = max_errors
        self._cleanup_interval = 3600  # 1 hour
        self._last_cleanup = time.time()
        
        # Error categorization patterns
        self._categorization_patterns = {
            ErrorCategory.DATA_QUALITY: [
                'invalid fen', 'missing move', 'corrupted game', 'inconsistent data',
                'data validation failed', 'quality check failed'
            ],
            ErrorCategory.VALIDATION: [
                'validation error', 'invalid input', 'schema validation',
                'parameter validation', 'format error'
            ],
            ErrorCategory.PERFORMANCE: [
                'timeout', 'slow query', 'memory limit', 'cpu limit',
                'performance threshold', 'resource exhausted'
            ],
            ErrorCategory.USER_INTERFACE: [
                'chess board', 'component render', 'ui error', 'display error',
                'navigation error', 'interaction error'
            ],
            ErrorCategory.API: [
                'api error', 'endpoint error', 'response error', 'request failed',
                'http error', 'service unavailable'
            ],
            ErrorCategory.DATABASE: [
                'database error', 'query failed', 'connection error',
                'transaction error', 'constraint violation'
            ],
            ErrorCategory.CACHE: [
                'cache miss', 'cache error', 'cache timeout', 'cache invalidation',
                'redis error', 'memcache error'
            ],
            ErrorCategory.SYSTEM: [
                'system error', 'os error', 'file system', 'network error',
                'permission denied', 'disk space'
            ],
        }
    
    def track_error(self,
                   title: str,
                   description: str,
                   category: Optional[ErrorCategory] = None,
                   severity: Optional[ErrorSeverity] = None,
                   source: ErrorSource = ErrorSource.AUTOMATIC,
                   context: Optional[ErrorContext] = None,
                   exception: Optional[Exception] = None) -> str:
        """Track an error and return the error ID."""
        
        # Auto-categorize if not specified
        if not category:
            category = self._auto_categorize_error(title, description)
        
        # Auto-determine severity if not specified
        if not severity:
            severity = self._auto_determine_severity(title, description, exception)
        
        # Create error context if not provided
        if not context:
            context = ErrorContext()
        
        # Add stack trace if exception provided
        if exception and not context.stack_trace:
            context.stack_trace = traceback.format_exc()
        
        # Generate error hash for deduplication
        error_hash = self._generate_error_hash(title, description, category, context)
        
        # Check if this is a duplicate error
        existing_error = self._find_duplicate_error(error_hash)
        if existing_error:
            existing_error.count += 1
            existing_error.last_seen = datetime.now()
            logger.debug(f"Duplicate error tracked: {existing_error.error_id} (count: {existing_error.count})")
            return existing_error.error_id
        
        # Create new error report
        error_id = str(uuid.uuid4())
        now = datetime.now()
        
        error_report = ErrorReport(
            error_id=error_id,
            timestamp=now,
            category=category,
            severity=severity,
            source=source,
            title=title,
            description=description,
            context=context,
            error_hash=error_hash,
            first_seen=now,
            last_seen=now,
            tags=self._generate_tags(title, description, context)
        )
        
        # Store error report
        self.errors[error_id] = error_report
        self.error_patterns[error_hash].append(error_id)
        
        # Log error based on severity
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(severity, logging.ERROR)
        
        logger.log(log_level, f"Error tracked: {title} [{error_id}] - {description}")
        
        # Trigger alerts for high severity errors
        if severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self._trigger_alert(error_report)
        
        # Cleanup old errors periodically
        self._periodic_cleanup()
        
        return error_id
    
    def track_user_report(self, 
                         user_report: UserErrorReport,
                         context: Optional[ErrorContext] = None) -> str:
        """Track a user-reported error."""
        
        if not context:
            context = ErrorContext()
        
        # Add user report specific context
        if user_report.context:
            context.additional_data.update(user_report.context)
        
        if user_report.browser_info:
            context.additional_data['browser_info'] = user_report.browser_info
        
        if user_report.screenshot_url:
            context.additional_data['screenshot_url'] = user_report.screenshot_url
        
        context.additional_data.update({
            'steps_to_reproduce': user_report.steps_to_reproduce,
            'expected_behavior': user_report.expected_behavior,
            'actual_behavior': user_report.actual_behavior,
        })
        
        return self.track_error(
            title=user_report.title,
            description=user_report.description,
            category=user_report.category,
            severity=user_report.severity,
            source=ErrorSource.USER_REPORT,
            context=context
        )
    
    def track_validation_error(self,
                              field: str,
                              value: Any,
                              validation_type: str,
                              context: Optional[ErrorContext] = None) -> str:
        """Track a data validation error."""
        
        if not context:
            context = ErrorContext()
        
        context.additional_data.update({
            'field': field,
            'invalid_value': str(value)[:1000],  # Limit to prevent huge values
            'validation_type': validation_type,
        })
        
        title = f"Validation Error: {field}"
        description = f"Field '{field}' failed {validation_type} validation with value: {str(value)[:200]}"
        
        return self.track_error(
            title=title,
            description=description,
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            source=ErrorSource.VALIDATION,
            context=context
        )
    
    def track_data_quality_issue(self,
                                data_type: str,
                                issue_description: str,
                                confidence_level: Optional[float] = None,
                                context: Optional[ErrorContext] = None) -> str:
        """Track a data quality issue."""
        
        if not context:
            context = ErrorContext()
        
        context.additional_data.update({
            'data_type': data_type,
            'confidence_level': confidence_level,
        })
        
        # Determine severity based on confidence level
        if confidence_level is not None:
            if confidence_level < 0.3:
                severity = ErrorSeverity.CRITICAL
            elif confidence_level < 0.5:
                severity = ErrorSeverity.HIGH
            elif confidence_level < 0.7:
                severity = ErrorSeverity.MEDIUM
            else:
                severity = ErrorSeverity.LOW
        else:
            severity = ErrorSeverity.MEDIUM
        
        title = f"Data Quality Issue: {data_type}"
        description = f"Data quality issue detected in {data_type}: {issue_description}"
        
        return self.track_error(
            title=title,
            description=description,
            category=ErrorCategory.DATA_QUALITY,
            severity=severity,
            source=ErrorSource.AUTOMATIC,
            context=context
        )
    
    def track_performance_issue(self,
                               operation: str,
                               duration_ms: float,
                               threshold_ms: float,
                               context: Optional[ErrorContext] = None) -> str:
        """Track a performance issue."""
        
        if not context:
            context = ErrorContext()
        
        context.operation = operation
        context.additional_data.update({
            'duration_ms': duration_ms,
            'threshold_ms': threshold_ms,
            'slowdown_factor': duration_ms / threshold_ms if threshold_ms > 0 else float('inf'),
        })
        
        # Determine severity based on how much threshold was exceeded
        slowdown_factor = duration_ms / threshold_ms if threshold_ms > 0 else 1
        if slowdown_factor > 5:
            severity = ErrorSeverity.CRITICAL
        elif slowdown_factor > 3:
            severity = ErrorSeverity.HIGH
        elif slowdown_factor > 2:
            severity = ErrorSeverity.MEDIUM
        else:
            severity = ErrorSeverity.LOW
        
        title = f"Performance Issue: {operation}"
        description = f"Operation '{operation}' took {duration_ms:.2f}ms (threshold: {threshold_ms:.2f}ms)"
        
        return self.track_error(
            title=title,
            description=description,
            category=ErrorCategory.PERFORMANCE,
            severity=severity,
            source=ErrorSource.MONITORING,
            context=context
        )
    
    def _auto_categorize_error(self, title: str, description: str) -> ErrorCategory:
        """Automatically categorize error based on title and description."""
        text = (title + " " + description).lower()
        
        # Score each category based on pattern matches
        category_scores = {}
        for category, patterns in self._categorization_patterns.items():
            score = sum(1 for pattern in patterns if pattern in text)
            if score > 0:
                category_scores[category] = score
        
        # Return category with highest score, or default to SYSTEM
        if category_scores:
            return max(category_scores.items(), key=lambda x: x[1])[0]
        
        return ErrorCategory.SYSTEM
    
    def _auto_determine_severity(self, 
                                title: str, 
                                description: str, 
                                exception: Optional[Exception]) -> ErrorSeverity:
        """Automatically determine error severity."""
        text = (title + " " + description).lower()
        
        # Critical patterns
        critical_patterns = [
            'critical', 'fatal', 'crash', 'system failure', 'data loss',
            'security breach', 'authentication failed', 'authorization failed'
        ]
        
        # High severity patterns
        high_patterns = [
            'error', 'exception', 'failed', 'timeout', 'unavailable',
            'corrupted', 'invalid', 'missing', 'broken'
        ]
        
        # Medium severity patterns
        medium_patterns = [
            'warning', 'deprecated', 'slow', 'performance', 'validation'
        ]
        
        # Check patterns in order of severity
        if any(pattern in text for pattern in critical_patterns):
            return ErrorSeverity.CRITICAL
        
        if any(pattern in text for pattern in high_patterns):
            return ErrorSeverity.HIGH
        
        if any(pattern in text for pattern in medium_patterns):
            return ErrorSeverity.MEDIUM
        
        # Check exception type
        if exception:
            if isinstance(exception, (SystemExit, KeyboardInterrupt, MemoryError)):
                return ErrorSeverity.CRITICAL
            elif isinstance(exception, (ValueError, TypeError, AttributeError)):
                return ErrorSeverity.HIGH
            elif isinstance(exception, (Warning, DeprecationWarning)):
                return ErrorSeverity.LOW
        
        return ErrorSeverity.LOW
    
    def _generate_error_hash(self, 
                            title: str, 
                            description: str, 
                            category: ErrorCategory,
                            context: ErrorContext) -> str:
        """Generate a hash for error deduplication."""
        # Create a normalized string for hashing
        hash_components = [
            title.lower().strip(),
            description.lower().strip()[:500],  # Limit description length
            category.value,
            context.operation or "",
        ]
        
        # Add relevant context for deduplication
        if context.game_id:
            hash_components.append(f"game:{context.game_id}")
        if context.player_id:
            hash_components.append(f"player:{context.player_id}")
        
        hash_string = "|".join(hash_components)
        return hashlib.md5(hash_string.encode()).hexdigest()
    
    def _find_duplicate_error(self, error_hash: str) -> Optional[ErrorReport]:
        """Find an existing error with the same hash."""
        error_ids = self.error_patterns.get(error_hash, [])
        
        for error_id in error_ids:
            if error_id in self.errors and not self.errors[error_id].resolved:
                return self.errors[error_id]
        
        return None
    
    def _generate_tags(self, 
                      title: str, 
                      description: str, 
                      context: ErrorContext) -> List[str]:
        """Generate tags for error categorization and filtering."""
        tags = []
        
        # Add tags based on context
        if context.game_id:
            tags.append(f"game:{context.game_id}")
        if context.player_id:
            tags.append(f"player:{context.player_id}")
        if context.operation:
            tags.append(f"operation:{context.operation}")
        if context.url:
            tags.extend([f"endpoint:{path}" for path in context.url.split('/') if path])
        
        # Add tags based on content
        text = (title + " " + description).lower()
        
        if 'chess' in text:
            tags.append('chess-related')
        if 'board' in text:
            tags.append('chess-board')
        if 'statistics' in text:
            tags.append('statistics')
        if 'leaderboard' in text:
            tags.append('leaderboard')
        if 'api' in text:
            tags.append('api')
        if 'database' in text or 'db' in text:
            tags.append('database')
        if 'cache' in text:
            tags.append('cache')
        if 'performance' in text or 'slow' in text:
            tags.append('performance')
        
        return list(set(tags))  # Remove duplicates
    
    def _trigger_alert(self, error_report: ErrorReport):
        """Trigger alert for high severity errors."""
        logger.critical(
            f"HIGH SEVERITY ERROR ALERT: {error_report.title} [{error_report.error_id}]\n"
            f"Category: {error_report.category.value}\n"
            f"Severity: {error_report.severity.value}\n"
            f"Description: {error_report.description}\n"
            f"Context: {error_report.context}"
        )
        
        # Here you could integrate with external alerting systems
        # like Slack, PagerDuty, email notifications, etc.
    
    def _periodic_cleanup(self):
        """Periodically clean up old resolved errors."""
        current_time = time.time()
        
        if current_time - self._last_cleanup > self._cleanup_interval:
            self._cleanup_old_errors()
            self._last_cleanup = current_time
    
    def _cleanup_old_errors(self):
        """Remove old resolved errors to prevent memory bloat."""
        cutoff_date = datetime.now() - timedelta(days=30)  # Keep 30 days of resolved errors
        
        errors_to_remove = []
        for error_id, error_report in self.errors.items():
            if (error_report.resolved and 
                error_report.last_seen < cutoff_date and
                len(self.errors) > self.max_errors * 0.8):  # Only cleanup if approaching limit
                errors_to_remove.append(error_id)
        
        for error_id in errors_to_remove:
            error_report = self.errors.pop(error_id, None)
            if error_report:
                # Remove from patterns as well
                if error_report.error_hash in self.error_patterns:
                    self.error_patterns[error_report.error_hash] = [
                        eid for eid in self.error_patterns[error_report.error_hash] 
                        if eid != error_id
                    ]
        
        if errors_to_remove:
            logger.info(f"Cleaned up {len(errors_to_remove)} old resolved errors")
    
    def get_error(self, error_id: str) -> Optional[ErrorReport]:
        """Get a specific error by ID."""
        return self.errors.get(error_id)
    
    def get_errors(self,
                   category: Optional[ErrorCategory] = None,
                   severity: Optional[ErrorSeverity] = None,
                   resolved: Optional[bool] = None,
                   limit: int = 100,
                   offset: int = 0) -> List[ErrorReport]:
        """Get errors with optional filtering."""
        filtered_errors = list(self.errors.values())
        
        # Apply filters
        if category:
            filtered_errors = [e for e in filtered_errors if e.category == category]
        if severity:
            filtered_errors = [e for e in filtered_errors if e.severity == severity]
        if resolved is not None:
            filtered_errors = [e for e in filtered_errors if e.resolved == resolved]
        
        # Sort by last seen (most recent first)
        filtered_errors.sort(key=lambda e: e.last_seen, reverse=True)
        
        # Apply pagination
        return filtered_errors[offset:offset + limit]
    
    def get_error_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get error summary statistics."""
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_errors = [e for e in self.errors.values() if e.first_seen > cutoff_date]
        
        if not recent_errors:
            return {
                'total_errors': 0,
                'by_category': {},
                'by_severity': {},
                'resolved_rate': 0,
                'top_errors': [],
            }
        
        # Count by category
        by_category = Counter(e.category.value for e in recent_errors)
        
        # Count by severity
        by_severity = Counter(e.severity.value for e in recent_errors)
        
        # Calculate resolution rate
        resolved_count = sum(1 for e in recent_errors if e.resolved)
        resolved_rate = resolved_count / len(recent_errors) if recent_errors else 0
        
        # Top errors by count
        error_counts = [(e.title, e.count, e.severity.value) for e in recent_errors]
        error_counts.sort(key=lambda x: x[1], reverse=True)
        top_errors = error_counts[:10]
        
        return {
            'total_errors': len(recent_errors),
            'unique_errors': len(set(e.error_hash for e in recent_errors)),
            'by_category': dict(by_category),
            'by_severity': dict(by_severity),
            'resolved_rate': resolved_rate,
            'top_errors': top_errors,
            'days': days,
        }
    
    def resolve_error(self, error_id: str, resolution_notes: Optional[str] = None) -> bool:
        """Mark an error as resolved."""
        error_report = self.errors.get(error_id)
        if not error_report:
            return False
        
        error_report.resolved = True
        error_report.resolution_notes = resolution_notes
        logger.info(f"Error resolved: {error_id} - {resolution_notes or 'No notes provided'}")
        
        return True

# Global error tracker instance
error_tracker = ErrorTracker()

# Exception handler decorator
def track_exceptions(category: ErrorCategory = ErrorCategory.SYSTEM):
    """Decorator to automatically track exceptions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Create context from function info
                context = ErrorContext(
                    operation=f"{func.__module__}.{func.__name__}",
                    parameters={
                        'args': [str(arg)[:100] for arg in args],  # Limit parameter length
                        'kwargs': {k: str(v)[:100] for k, v in kwargs.items()},
                    }
                )
                
                error_tracker.track_error(
                    title=f"Exception in {func.__name__}",
                    description=str(e),
                    category=category,
                    source=ErrorSource.EXCEPTION_HANDLER,
                    context=context,
                    exception=e
                )
                
                raise  # Re-raise the exception
        
        return wrapper
    return decorator

# Export the error tracker and utilities
__all__ = [
    'error_tracker',
    'ErrorTracker',
    'ErrorReport',
    'ErrorContext',
    'UserErrorReport',
    'ErrorSeverity',
    'ErrorCategory',
    'ErrorSource',
    'track_exceptions',
]