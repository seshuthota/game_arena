"""
Performance Monitor for comprehensive cache analytics and system monitoring.

This module provides detailed performance monitoring capabilities for the caching
system, including real-time metrics collection, performance analysis, alerting,
and optimization recommendations.
"""

import asyncio
import logging
import time
import threading
import psutil
from typing import Dict, List, Optional, Any, Callable, Set, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
from enum import Enum
import json
import statistics

from statistics_cache import StatisticsCache, get_statistics_cache
from batch_statistics_processor import BatchStatisticsProcessor, get_batch_processor
from cache_manager import CacheManager, get_cache_manager

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class MetricType(str, Enum):
    """Types of performance metrics."""
    CACHE_HIT_RATE = "cache_hit_rate"
    RESPONSE_TIME = "response_time"
    THROUGHPUT = "throughput"
    ERROR_RATE = "error_rate"
    MEMORY_USAGE = "memory_usage"
    CPU_USAGE = "cpu_usage"
    QUEUE_LENGTH = "queue_length"
    CACHE_SIZE = "cache_size"
    EVICTION_RATE = "eviction_rate"


@dataclass
class PerformanceAlert:
    """Performance alert notification."""
    alert_id: str
    metric_type: MetricType
    severity: AlertSeverity
    message: str
    current_value: float
    threshold: float
    timestamp: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
    resolution_notes: str = ""


@dataclass
class MetricSample:
    """Single performance metric sample."""
    timestamp: datetime
    value: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceTrend:
    """Performance trend analysis."""
    metric_type: MetricType
    trend_direction: str  # "increasing", "decreasing", "stable"
    trend_strength: float  # 0.0 to 1.0
    recent_average: float
    previous_average: float
    change_percentage: float
    confidence_level: float


@dataclass
class SystemHealthReport:
    """Comprehensive system health report."""
    timestamp: datetime
    overall_health_score: float  # 0.0 to 100.0
    cache_performance_score: float
    system_resource_score: float
    error_rate_score: float
    alerts: List[PerformanceAlert]
    trends: List[PerformanceTrend]
    recommendations: List[str]
    uptime: timedelta


class PerformanceMonitor:
    """
    Comprehensive performance monitoring system for cache analytics.
    
    Provides:
    - Real-time metrics collection and analysis
    - Performance trend detection and forecasting
    - Intelligent alerting based on thresholds and patterns
    - System health scoring and reporting
    - Optimization recommendations
    """
    
    def __init__(
        self,
        cache: Optional[StatisticsCache] = None,
        batch_processor: Optional[BatchStatisticsProcessor] = None,
        cache_manager: Optional[CacheManager] = None,
        collection_interval_seconds: int = 30,
        history_retention_hours: int = 24,
        alert_thresholds: Optional[Dict[MetricType, Dict[str, float]]] = None
    ):
        """Initialize the performance monitor."""
        self.cache = cache or get_statistics_cache()
        self.batch_processor = batch_processor
        self.cache_manager = cache_manager or get_cache_manager()
        self.collection_interval = collection_interval_seconds
        self.history_retention = timedelta(hours=history_retention_hours)
        
        # Metric storage
        self._metrics_history: Dict[MetricType, deque] = defaultdict(
            lambda: deque(maxlen=int(history_retention_hours * 3600 / collection_interval_seconds))
        )
        
        # Alert management
        self._alert_thresholds = alert_thresholds or self._get_default_alert_thresholds()
        self._active_alerts: Dict[str, PerformanceAlert] = {}
        self._alert_history: List[PerformanceAlert] = []
        
        # Monitoring state
        self._monitoring_active = False
        self._monitoring_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._start_time = datetime.now()
        
        # Performance tracking
        self._performance_stats = {
            'total_samples_collected': 0,
            'alerts_generated': 0,
            'trends_detected': 0,
            'health_reports_generated': 0,
            'last_collection_time': 0.0,
            'collection_errors': 0
        }
        
        # Trend analysis
        self._trend_analysis_window = 20  # Number of samples for trend analysis
        self._trend_confidence_threshold = 0.7
        
        # System monitoring
        self._system_process = psutil.Process()
        
        logger.info(f"PerformanceMonitor initialized with {collection_interval_seconds}s intervals")
    
    def start_monitoring(self) -> None:
        """Start the background monitoring process."""
        if self._monitoring_active:
            logger.warning("Performance monitoring already active")
            return
        
        self._monitoring_active = True
        self._shutdown_event.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitoring_loop,
            name="PerformanceMonitor",
            daemon=True
        )
        self._monitoring_thread.start()
        logger.info("Performance monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the background monitoring process."""
        if not self._monitoring_active:
            return
        
        self._monitoring_active = False
        self._shutdown_event.set()
        
        if self._monitoring_thread:
            self._monitoring_thread.join(timeout=10)
            
        logger.info("Performance monitoring stopped")
    
    def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown_event.wait(timeout=self.collection_interval):
            try:
                start_time = time.time()
                self._collect_all_metrics()
                self._analyze_trends()
                self._check_alert_conditions()
                collection_time = time.time() - start_time
                
                self._performance_stats['total_samples_collected'] += 1
                self._performance_stats['last_collection_time'] = collection_time
                
                if collection_time > self.collection_interval * 0.5:
                    logger.warning(f"Metric collection took {collection_time:.2f}s (>{self.collection_interval*0.5:.2f}s)")
                    
            except Exception as e:
                self._performance_stats['collection_errors'] += 1
                logger.error(f"Error in monitoring loop: {e}")
    
    def _collect_all_metrics(self) -> None:
        """Collect all performance metrics."""
        current_time = datetime.now()
        
        # Collect cache metrics
        try:
            cache_stats = self.cache.get_stats()
            
            # Cache hit rate
            hit_rate = cache_stats.get('hit_rate', 0.0) * 100
            self._record_metric(MetricType.CACHE_HIT_RATE, hit_rate, current_time)
            
            # Cache size
            cache_size = cache_stats.get('cache_size', 0)
            self._record_metric(MetricType.CACHE_SIZE, cache_size, current_time)
            
            # Eviction rate (approximate)
            evictions = cache_stats.get('evictions', 0)
            total_requests = cache_stats.get('total_requests', 1)
            eviction_rate = (evictions / total_requests) * 100 if total_requests > 0 else 0
            self._record_metric(MetricType.EVICTION_RATE, eviction_rate, current_time)
            
        except Exception as e:
            logger.error(f"Error collecting cache metrics: {e}")
        
        # Collect system resource metrics
        try:
            # Memory usage
            memory_info = self._system_process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            self._record_metric(MetricType.MEMORY_USAGE, memory_mb, current_time)
            
            # CPU usage
            cpu_percent = self._system_process.cpu_percent()
            self._record_metric(MetricType.CPU_USAGE, cpu_percent, current_time)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
        
        # Collect batch processor metrics if available
        if self.batch_processor:
            try:
                batch_metrics = self.batch_processor.get_performance_metrics()
                
                # Processing time (convert to response time)
                avg_time = batch_metrics.get('average_processing_time', 0.0)
                self._record_metric(MetricType.RESPONSE_TIME, avg_time * 1000, current_time)  # Convert to ms
                
                # Error rate
                total_jobs = batch_metrics.get('total_jobs', 1)
                failed_jobs = batch_metrics.get('failed_jobs', 0)
                error_rate = (failed_jobs / total_jobs) * 100 if total_jobs > 0 else 0
                self._record_metric(MetricType.ERROR_RATE, error_rate, current_time)
                
            except Exception as e:
                logger.error(f"Error collecting batch processor metrics: {e}")
        
        # Collect cache manager metrics if available
        if self.cache_manager:
            try:
                manager_report = self.cache_manager.get_performance_report()
                overview = manager_report.get('overview', {})
                
                # Overall hit rate
                overall_hit_rate = overview.get('overall_hit_rate', 0.0) * 100
                self._record_metric(MetricType.CACHE_HIT_RATE, overall_hit_rate, current_time)
                
            except Exception as e:
                logger.error(f"Error collecting cache manager metrics: {e}")
    
    def _record_metric(
        self,
        metric_type: MetricType,
        value: float,
        timestamp: datetime,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a performance metric sample."""
        sample = MetricSample(
            timestamp=timestamp,
            value=value,
            metadata=metadata or {}
        )
        
        self._metrics_history[metric_type].append(sample)
        
        # Clean up old metrics beyond retention period
        cutoff_time = timestamp - self.history_retention
        while (self._metrics_history[metric_type] and 
               self._metrics_history[metric_type][0].timestamp < cutoff_time):
            self._metrics_history[metric_type].popleft()
    
    def _analyze_trends(self) -> None:
        """Analyze performance trends for all metrics."""
        for metric_type, samples in self._metrics_history.items():
            if len(samples) < self._trend_analysis_window:
                continue
            
            try:
                trend = self._calculate_trend(metric_type, samples)
                if trend and trend.confidence_level >= self._trend_confidence_threshold:
                    self._performance_stats['trends_detected'] += 1
                    logger.debug(f"Trend detected for {metric_type}: {trend.trend_direction} "
                               f"({trend.change_percentage:+.1f}%)")
                    
            except Exception as e:
                logger.error(f"Error analyzing trend for {metric_type}: {e}")
    
    def _calculate_trend(
        self,
        metric_type: MetricType,
        samples: deque
    ) -> Optional[PerformanceTrend]:
        """Calculate trend for a specific metric."""
        if len(samples) < self._trend_analysis_window:
            return None
        
        recent_samples = list(samples)[-self._trend_analysis_window:]
        values = [sample.value for sample in recent_samples]
        
        # Split into two halves for comparison
        mid_point = len(values) // 2
        first_half = values[:mid_point]
        second_half = values[mid_point:]
        
        first_avg = statistics.mean(first_half)
        second_avg = statistics.mean(second_half)
        
        # Calculate change
        change_percentage = ((second_avg - first_avg) / first_avg * 100) if first_avg != 0 else 0
        
        # Determine trend direction
        if abs(change_percentage) < 5:  # Less than 5% change is considered stable
            trend_direction = "stable"
            trend_strength = 0.0
        elif change_percentage > 0:
            trend_direction = "increasing"
            trend_strength = min(abs(change_percentage) / 50.0, 1.0)  # Normalize to 0-1
        else:
            trend_direction = "decreasing"
            trend_strength = min(abs(change_percentage) / 50.0, 1.0)
        
        # Calculate confidence based on consistency
        try:
            recent_stddev = statistics.stdev(values)
            recent_mean = statistics.mean(values)
            coefficient_of_variation = (recent_stddev / recent_mean) if recent_mean != 0 else 1.0
            confidence_level = max(0.0, 1.0 - coefficient_of_variation)
        except:
            confidence_level = 0.5
        
        return PerformanceTrend(
            metric_type=metric_type,
            trend_direction=trend_direction,
            trend_strength=trend_strength,
            recent_average=second_avg,
            previous_average=first_avg,
            change_percentage=change_percentage,
            confidence_level=confidence_level
        )
    
    def _check_alert_conditions(self) -> None:
        """Check for alert conditions and generate alerts."""
        current_time = datetime.now()
        
        for metric_type, samples in self._metrics_history.items():
            if not samples:
                continue
            
            try:
                latest_sample = samples[-1]
                thresholds = self._alert_thresholds.get(metric_type, {})
                
                for severity_str, threshold in thresholds.items():
                    severity = AlertSeverity(severity_str)
                    alert_id = f"{metric_type}_{severity}_{int(current_time.timestamp())}"
                    
                    # Check if threshold is breached
                    breached = False
                    if metric_type in [MetricType.CACHE_HIT_RATE]:
                        # For metrics where lower is worse
                        breached = latest_sample.value < threshold
                    else:
                        # For metrics where higher is worse
                        breached = latest_sample.value > threshold
                    
                    if breached and alert_id not in self._active_alerts:
                        alert = PerformanceAlert(
                            alert_id=alert_id,
                            metric_type=metric_type,
                            severity=severity,
                            message=f"{metric_type} {('below' if metric_type == MetricType.CACHE_HIT_RATE else 'above')} threshold: "
                                   f"{latest_sample.value:.2f} {'<' if metric_type == MetricType.CACHE_HIT_RATE else '>'} {threshold}",
                            current_value=latest_sample.value,
                            threshold=threshold,
                            timestamp=current_time
                        )
                        
                        self._active_alerts[alert_id] = alert
                        self._alert_history.append(alert)
                        self._performance_stats['alerts_generated'] += 1
                        
                        logger.warning(f"Performance alert: {alert.message}")
                        
            except Exception as e:
                logger.error(f"Error checking alerts for {metric_type}: {e}")
    
    def get_current_metrics(self) -> Dict[MetricType, float]:
        """Get the most recent values for all metrics."""
        current_metrics = {}
        
        for metric_type, samples in self._metrics_history.items():
            if samples:
                current_metrics[metric_type] = samples[-1].value
        
        return current_metrics
    
    def get_metric_history(
        self,
        metric_type: MetricType,
        hours: int = 1
    ) -> List[MetricSample]:
        """Get historical data for a specific metric."""
        if metric_type not in self._metrics_history:
            return []
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        samples = self._metrics_history[metric_type]
        
        return [
            sample for sample in samples
            if sample.timestamp >= cutoff_time
        ]
    
    def generate_health_report(self) -> SystemHealthReport:
        """Generate a comprehensive system health report."""
        current_time = datetime.now()
        uptime = current_time - self._start_time
        
        # Calculate health scores
        cache_score = self._calculate_cache_health_score()
        resource_score = self._calculate_resource_health_score()
        error_score = self._calculate_error_health_score()
        
        # Overall health score (weighted average)
        overall_score = (cache_score * 0.5 + resource_score * 0.3 + error_score * 0.2)
        
        # Get active alerts
        active_alerts = list(self._active_alerts.values())
        
        # Generate trends
        trends = []
        for metric_type in self._metrics_history.keys():
            trend = self._calculate_trend(metric_type, self._metrics_history[metric_type])
            if trend and trend.confidence_level >= self._trend_confidence_threshold:
                trends.append(trend)
        
        # Generate recommendations
        recommendations = self._generate_optimization_recommendations(overall_score, active_alerts, trends)
        
        self._performance_stats['health_reports_generated'] += 1
        
        return SystemHealthReport(
            timestamp=current_time,
            overall_health_score=overall_score,
            cache_performance_score=cache_score,
            system_resource_score=resource_score,
            error_rate_score=error_score,
            alerts=active_alerts,
            trends=trends,
            recommendations=recommendations,
            uptime=uptime
        )
    
    def _calculate_cache_health_score(self) -> float:
        """Calculate cache performance health score (0-100)."""
        score = 100.0
        
        # Check cache hit rate
        hit_rate_samples = self._metrics_history.get(MetricType.CACHE_HIT_RATE)
        if hit_rate_samples:
            recent_hit_rate = statistics.mean([s.value for s in list(hit_rate_samples)[-10:]])
            if recent_hit_rate < 50:
                score -= 30
            elif recent_hit_rate < 70:
                score -= 15
        
        # Check eviction rate
        eviction_samples = self._metrics_history.get(MetricType.EVICTION_RATE)
        if eviction_samples:
            recent_eviction_rate = statistics.mean([s.value for s in list(eviction_samples)[-10:]])
            if recent_eviction_rate > 20:
                score -= 20
            elif recent_eviction_rate > 10:
                score -= 10
        
        # Check response time
        response_samples = self._metrics_history.get(MetricType.RESPONSE_TIME)
        if response_samples:
            recent_response_time = statistics.mean([s.value for s in list(response_samples)[-10:]])
            if recent_response_time > 1000:  # > 1 second
                score -= 25
            elif recent_response_time > 500:  # > 500ms
                score -= 10
        
        return max(0.0, score)
    
    def _calculate_resource_health_score(self) -> float:
        """Calculate system resource health score (0-100)."""
        score = 100.0
        
        # Check memory usage
        memory_samples = self._metrics_history.get(MetricType.MEMORY_USAGE)
        if memory_samples:
            recent_memory = statistics.mean([s.value for s in list(memory_samples)[-10:]])
            if recent_memory > 1000:  # > 1GB
                score -= 20
            elif recent_memory > 500:  # > 500MB
                score -= 10
        
        # Check CPU usage
        cpu_samples = self._metrics_history.get(MetricType.CPU_USAGE)
        if cpu_samples:
            recent_cpu = statistics.mean([s.value for s in list(cpu_samples)[-10:]])
            if recent_cpu > 80:
                score -= 30
            elif recent_cpu > 60:
                score -= 15
        
        return max(0.0, score)
    
    def _calculate_error_health_score(self) -> float:
        """Calculate error rate health score (0-100)."""
        score = 100.0
        
        error_samples = self._metrics_history.get(MetricType.ERROR_RATE)
        if error_samples:
            recent_error_rate = statistics.mean([s.value for s in list(error_samples)[-10:]])
            if recent_error_rate > 10:
                score -= 50
            elif recent_error_rate > 5:
                score -= 25
            elif recent_error_rate > 1:
                score -= 10
        
        return max(0.0, score)
    
    def _generate_optimization_recommendations(
        self,
        overall_score: float,
        alerts: List[PerformanceAlert],
        trends: List[PerformanceTrend]
    ) -> List[str]:
        """Generate optimization recommendations based on current state."""
        recommendations = []
        
        # Based on overall health
        if overall_score < 60:
            recommendations.append("Overall system health is poor. Investigate critical performance issues immediately.")
        elif overall_score < 80:
            recommendations.append("System health is below optimal. Consider performance optimizations.")
        
        # Based on alerts
        high_severity_alerts = [a for a in alerts if a.severity in [AlertSeverity.HIGH, AlertSeverity.CRITICAL]]
        if high_severity_alerts:
            recommendations.append(f"Address {len(high_severity_alerts)} high-severity performance alerts.")
        
        # Based on trends
        for trend in trends:
            if trend.trend_direction == "decreasing" and trend.metric_type == MetricType.CACHE_HIT_RATE:
                recommendations.append("Cache hit rate is declining. Consider increasing cache size or adjusting TTL values.")
            elif trend.trend_direction == "increasing" and trend.metric_type == MetricType.RESPONSE_TIME:
                recommendations.append("Response times are increasing. Investigate performance bottlenecks.")
            elif trend.trend_direction == "increasing" and trend.metric_type == MetricType.MEMORY_USAGE:
                recommendations.append("Memory usage is growing. Consider implementing memory optimization strategies.")
        
        # Specific metric-based recommendations
        current_metrics = self.get_current_metrics()
        
        if current_metrics.get(MetricType.CACHE_HIT_RATE, 100) < 70:
            recommendations.append("Low cache hit rate detected. Consider implementing cache warming strategies.")
        
        if current_metrics.get(MetricType.EVICTION_RATE, 0) > 15:
            recommendations.append("High cache eviction rate. Consider increasing cache size or optimizing TTL values.")
        
        if current_metrics.get(MetricType.CPU_USAGE, 0) > 70:
            recommendations.append("High CPU usage detected. Consider optimizing computational workloads.")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def _get_default_alert_thresholds(self) -> Dict[MetricType, Dict[str, float]]:
        """Get default alert thresholds for all metrics."""
        return {
            MetricType.CACHE_HIT_RATE: {
                AlertSeverity.MEDIUM.value: 60.0,
                AlertSeverity.HIGH.value: 40.0,
                AlertSeverity.CRITICAL.value: 20.0
            },
            MetricType.RESPONSE_TIME: {
                AlertSeverity.MEDIUM.value: 500.0,  # 500ms
                AlertSeverity.HIGH.value: 1000.0,  # 1s
                AlertSeverity.CRITICAL.value: 2000.0  # 2s
            },
            MetricType.ERROR_RATE: {
                AlertSeverity.MEDIUM.value: 2.0,  # 2%
                AlertSeverity.HIGH.value: 5.0,   # 5%
                AlertSeverity.CRITICAL.value: 10.0  # 10%
            },
            MetricType.MEMORY_USAGE: {
                AlertSeverity.MEDIUM.value: 500.0,  # 500MB
                AlertSeverity.HIGH.value: 1000.0,   # 1GB
                AlertSeverity.CRITICAL.value: 2000.0  # 2GB
            },
            MetricType.CPU_USAGE: {
                AlertSeverity.MEDIUM.value: 60.0,  # 60%
                AlertSeverity.HIGH.value: 80.0,    # 80%
                AlertSeverity.CRITICAL.value: 95.0   # 95%
            },
            MetricType.EVICTION_RATE: {
                AlertSeverity.MEDIUM.value: 10.0,  # 10%
                AlertSeverity.HIGH.value: 20.0,    # 20%
                AlertSeverity.CRITICAL.value: 35.0   # 35%
            }
        }
    
    def acknowledge_alert(self, alert_id: str, notes: str = "") -> bool:
        """Acknowledge an active alert."""
        if alert_id in self._active_alerts:
            alert = self._active_alerts[alert_id]
            alert.acknowledged = True
            alert.resolution_notes = notes
            logger.info(f"Alert acknowledged: {alert_id}")
            return True
        return False
    
    def clear_alert(self, alert_id: str) -> bool:
        """Clear an active alert."""
        if alert_id in self._active_alerts:
            del self._active_alerts[alert_id]
            logger.info(f"Alert cleared: {alert_id}")
            return True
        return False
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get monitoring performance statistics."""
        uptime = datetime.now() - self._start_time
        return {
            **self._performance_stats,
            'monitoring_uptime_seconds': uptime.total_seconds(),
            'active_alerts_count': len(self._active_alerts),
            'total_alerts_history': len(self._alert_history),
            'metrics_tracked': len(self._metrics_history),
            'is_monitoring_active': self._monitoring_active
        }
    
    def export_metrics(
        self,
        hours: int = 1,
        format: str = "json"
    ) -> str:
        """Export metrics data for external analysis."""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'export_parameters': {
                'hours': hours,
                'format': format
            },
            'metrics': {}
        }
        
        for metric_type in self._metrics_history.keys():
            history = self.get_metric_history(metric_type, hours)
            export_data['metrics'][metric_type.value] = [
                {
                    'timestamp': sample.timestamp.isoformat(),
                    'value': sample.value,
                    'metadata': sample.metadata
                }
                for sample in history
            ]
        
        if format == "json":
            return json.dumps(export_data, indent=2)
        else:
            return str(export_data)
    
    def shutdown(self) -> None:
        """Shutdown the performance monitor."""
        logger.info("Shutting down PerformanceMonitor")
        self.stop_monitoring()
        
        # Clear active alerts
        self._active_alerts.clear()
        
        # Clear metrics history
        self._metrics_history.clear()


# Global performance monitor instance
_global_performance_monitor: Optional[PerformanceMonitor] = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the global performance monitor instance."""
    global _global_performance_monitor
    if _global_performance_monitor is None:
        _global_performance_monitor = PerformanceMonitor()
    return _global_performance_monitor