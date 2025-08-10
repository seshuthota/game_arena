"""
Comprehensive unit tests for PerformanceMonitor.

Tests metrics collection, alerting, trend analysis, health reporting,
and system monitoring functionality.
"""

import pytest
import asyncio
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from collections import deque

from performance_monitor import (
    PerformanceMonitor,
    AlertSeverity,
    MetricType,
    PerformanceAlert,
    MetricSample,
    PerformanceTrend,
    SystemHealthReport,
    get_performance_monitor
)
from statistics_cache import StatisticsCache
from batch_statistics_processor import BatchStatisticsProcessor
from cache_manager import CacheManager


class MockStatisticsCache:
    """Mock statistics cache for testing."""
    
    def __init__(self):
        self.stats = {
            'hit_rate': 0.75,
            'cache_size': 150,
            'evictions': 5,
            'total_requests': 100
        }
    
    def get_stats(self):
        return self.stats.copy()


class MockBatchProcessor:
    """Mock batch processor for testing."""
    
    def __init__(self):
        self.performance_metrics = {
            'total_jobs': 10,
            'successful_jobs': 8,
            'failed_jobs': 2,
            'average_processing_time': 1.5,
            'cache_efficiency': 0.80
        }
    
    def get_performance_metrics(self):
        return self.performance_metrics.copy()


class MockCacheManager:
    """Mock cache manager for testing."""
    
    def __init__(self):
        self.performance_report = {
            'overview': {
                'total_requests': 500,
                'overall_hit_rate': 0.70,
                'warming_tasks_completed': 25,
                'optimization_actions': 3
            },
            'cache_profiles': {},
            'cache_stats': {}
        }
    
    def get_performance_report(self):
        return self.performance_report.copy()


class TestPerformanceAlert:
    """Test PerformanceAlert data class."""
    
    def test_performance_alert_creation(self):
        """Test performance alert creation."""
        alert = PerformanceAlert(
            alert_id="test_alert_123",
            metric_type=MetricType.CACHE_HIT_RATE,
            severity=AlertSeverity.HIGH,
            message="Cache hit rate below threshold: 45.0% < 60.0%",
            current_value=45.0,
            threshold=60.0
        )
        
        assert alert.alert_id == "test_alert_123"
        assert alert.metric_type == MetricType.CACHE_HIT_RATE
        assert alert.severity == AlertSeverity.HIGH
        assert "45.0%" in alert.message
        assert alert.current_value == 45.0
        assert alert.threshold == 60.0
        assert not alert.acknowledged
        assert alert.resolution_notes == ""
        assert isinstance(alert.timestamp, datetime)


class TestMetricSample:
    """Test MetricSample data class."""
    
    def test_metric_sample_creation(self):
        """Test metric sample creation."""
        timestamp = datetime.now()
        sample = MetricSample(
            timestamp=timestamp,
            value=75.5,
            metadata={'source': 'test', 'context': 'unit_test'}
        )
        
        assert sample.timestamp == timestamp
        assert sample.value == 75.5
        assert sample.metadata['source'] == 'test'
        assert sample.metadata['context'] == 'unit_test'


class TestPerformanceTrend:
    """Test PerformanceTrend data class."""
    
    def test_performance_trend_creation(self):
        """Test performance trend creation."""
        trend = PerformanceTrend(
            metric_type=MetricType.RESPONSE_TIME,
            trend_direction="increasing",
            trend_strength=0.75,
            recent_average=250.0,
            previous_average=200.0,
            change_percentage=25.0,
            confidence_level=0.85
        )
        
        assert trend.metric_type == MetricType.RESPONSE_TIME
        assert trend.trend_direction == "increasing"
        assert trend.trend_strength == 0.75
        assert trend.recent_average == 250.0
        assert trend.previous_average == 200.0
        assert trend.change_percentage == 25.0
        assert trend.confidence_level == 0.85


class TestSystemHealthReport:
    """Test SystemHealthReport data class."""
    
    def test_system_health_report_creation(self):
        """Test system health report creation."""
        alerts = [
            PerformanceAlert("alert1", MetricType.CPU_USAGE, AlertSeverity.MEDIUM, "Test alert", 75.0, 70.0)
        ]
        trends = [
            PerformanceTrend(MetricType.MEMORY_USAGE, "increasing", 0.6, 100.0, 80.0, 25.0, 0.8)
        ]
        recommendations = ["Optimize cache size", "Reduce memory usage"]
        uptime = timedelta(hours=2, minutes=30)
        
        report = SystemHealthReport(
            timestamp=datetime.now(),
            overall_health_score=82.5,
            cache_performance_score=85.0,
            system_resource_score=75.0,
            error_rate_score=90.0,
            alerts=alerts,
            trends=trends,
            recommendations=recommendations,
            uptime=uptime
        )
        
        assert report.overall_health_score == 82.5
        assert report.cache_performance_score == 85.0
        assert report.system_resource_score == 75.0
        assert report.error_rate_score == 90.0
        assert len(report.alerts) == 1
        assert len(report.trends) == 1
        assert len(report.recommendations) == 2
        assert report.uptime == uptime


class TestPerformanceMonitor:
    """Test PerformanceMonitor functionality."""
    
    def setup_method(self):
        """Setup test performance monitor instance."""
        self.mock_cache = MockStatisticsCache()
        self.mock_batch_processor = MockBatchProcessor()
        self.mock_cache_manager = MockCacheManager()
        
        # Custom alert thresholds for testing
        self.test_thresholds = {
            MetricType.CACHE_HIT_RATE: {
                AlertSeverity.MEDIUM.value: 60.0,
                AlertSeverity.HIGH.value: 40.0,
                AlertSeverity.CRITICAL.value: 20.0
            },
            MetricType.RESPONSE_TIME: {
                AlertSeverity.MEDIUM.value: 500.0,
                AlertSeverity.HIGH.value: 1000.0,
                AlertSeverity.CRITICAL.value: 2000.0
            }
        }
        
        self.monitor = PerformanceMonitor(
            cache=self.mock_cache,
            batch_processor=self.mock_batch_processor,
            cache_manager=self.mock_cache_manager,
            collection_interval_seconds=1,  # Fast collection for testing
            history_retention_hours=1,
            alert_thresholds=self.test_thresholds
        )
    
    def teardown_method(self):
        """Cleanup after tests."""
        self.monitor.stop_monitoring()
    
    def test_performance_monitor_initialization(self):
        """Test performance monitor initialization."""
        assert self.monitor.cache == self.mock_cache
        assert self.monitor.batch_processor == self.mock_batch_processor
        assert self.monitor.cache_manager == self.mock_cache_manager
        assert self.monitor.collection_interval == 1
        assert self.monitor.history_retention == timedelta(hours=1)
        
        # Check alert thresholds
        assert self.monitor._alert_thresholds == self.test_thresholds
        
        # Check initial state
        assert not self.monitor._monitoring_active
        assert self.monitor._monitoring_thread is None
        assert len(self.monitor._metrics_history) == 0
        assert len(self.monitor._active_alerts) == 0
    
    def test_start_stop_monitoring(self):
        """Test starting and stopping monitoring."""
        # Start monitoring
        self.monitor.start_monitoring()
        assert self.monitor._monitoring_active
        assert self.monitor._monitoring_thread is not None
        assert self.monitor._monitoring_thread.is_alive()
        
        # Stop monitoring
        self.monitor.stop_monitoring()
        assert not self.monitor._monitoring_active
        
        # Give thread time to stop
        time.sleep(0.1)
        if self.monitor._monitoring_thread:
            assert not self.monitor._monitoring_thread.is_alive()
    
    def test_metric_recording(self):
        """Test metric sample recording."""
        timestamp = datetime.now()
        
        # Record metrics
        self.monitor._record_metric(MetricType.CACHE_HIT_RATE, 85.0, timestamp)
        self.monitor._record_metric(MetricType.RESPONSE_TIME, 150.0, timestamp)
        
        # Verify metrics were recorded
        assert MetricType.CACHE_HIT_RATE in self.monitor._metrics_history
        assert MetricType.RESPONSE_TIME in self.monitor._metrics_history
        
        # Check sample details
        hit_rate_samples = self.monitor._metrics_history[MetricType.CACHE_HIT_RATE]
        assert len(hit_rate_samples) == 1
        
        sample = hit_rate_samples[0]
        assert sample.timestamp == timestamp
        assert sample.value == 85.0
    
    @patch('performance_monitor.psutil.Process')
    def test_collect_all_metrics(self, mock_process_class):
        """Test comprehensive metric collection."""
        # Mock psutil process
        mock_process = Mock()
        mock_process.memory_info.return_value = Mock(rss=512 * 1024 * 1024)  # 512MB
        mock_process.cpu_percent.return_value = 25.5
        mock_process_class.return_value = mock_process
        
        # Collect metrics
        self.monitor._collect_all_metrics()
        
        # Verify cache metrics were collected
        assert MetricType.CACHE_HIT_RATE in self.monitor._metrics_history
        assert MetricType.CACHE_SIZE in self.monitor._metrics_history
        assert MetricType.EVICTION_RATE in self.monitor._metrics_history
        
        # Verify system metrics were collected
        assert MetricType.MEMORY_USAGE in self.monitor._metrics_history
        assert MetricType.CPU_USAGE in self.monitor._metrics_history
        
        # Check values
        hit_rate_sample = self.monitor._metrics_history[MetricType.CACHE_HIT_RATE][-1]
        assert hit_rate_sample.value == 75.0  # 0.75 * 100
        
        memory_sample = self.monitor._metrics_history[MetricType.MEMORY_USAGE][-1]
        assert memory_sample.value == 512.0  # 512MB
        
        cpu_sample = self.monitor._metrics_history[MetricType.CPU_USAGE][-1]
        assert cpu_sample.value == 25.5
    
    def test_get_current_metrics(self):
        """Test current metrics retrieval."""
        # Record some metrics
        timestamp = datetime.now()
        self.monitor._record_metric(MetricType.CACHE_HIT_RATE, 80.0, timestamp)
        self.monitor._record_metric(MetricType.RESPONSE_TIME, 200.0, timestamp)
        
        # Get current metrics
        current_metrics = self.monitor.get_current_metrics()
        
        assert MetricType.CACHE_HIT_RATE in current_metrics
        assert MetricType.RESPONSE_TIME in current_metrics
        assert current_metrics[MetricType.CACHE_HIT_RATE] == 80.0
        assert current_metrics[MetricType.RESPONSE_TIME] == 200.0
    
    def test_get_metric_history(self):
        """Test metric history retrieval."""
        # Record metrics over time
        base_time = datetime.now()
        for i in range(5):
            timestamp = base_time + timedelta(minutes=i)
            self.monitor._record_metric(MetricType.CACHE_HIT_RATE, 70.0 + i, timestamp)
        
        # Get recent history (last 2 hours)
        history = self.monitor.get_metric_history(MetricType.CACHE_HIT_RATE, hours=2)
        
        # Should return all samples (all within 2 hours)
        assert len(history) == 5
        
        # Get very recent history (last 2 minutes)
        recent_history = self.monitor.get_metric_history(MetricType.CACHE_HIT_RATE, hours=0)
        
        # Should return fewer samples
        assert len(recent_history) <= 5
    
    def test_alert_generation(self):
        """Test alert generation for threshold breaches."""
        # Record metric that breaches HIGH threshold (< 40.0)
        timestamp = datetime.now()
        self.monitor._record_metric(MetricType.CACHE_HIT_RATE, 35.0, timestamp)
        
        # Check for alert conditions
        self.monitor._check_alert_conditions()
        
        # Should have generated alert
        assert len(self.monitor._active_alerts) > 0
        
        # Find the alert
        alert = None
        for alert_id, alert_obj in self.monitor._active_alerts.items():
            if alert_obj.metric_type == MetricType.CACHE_HIT_RATE and alert_obj.severity == AlertSeverity.HIGH:
                alert = alert_obj
                break
        
        assert alert is not None
        assert alert.current_value == 35.0
        assert alert.threshold == 40.0
        assert "below threshold" in alert.message
    
    def test_multiple_severity_alerts(self):
        """Test generation of multiple severity alerts."""
        timestamp = datetime.now()
        
        # Record metric that breaches CRITICAL threshold (< 20.0)
        self.monitor._record_metric(MetricType.CACHE_HIT_RATE, 15.0, timestamp)
        
        # Check for alert conditions
        self.monitor._check_alert_conditions()
        
        # Should have generated multiple alerts (CRITICAL, HIGH, MEDIUM)
        cache_alerts = [
            alert for alert in self.monitor._active_alerts.values()
            if alert.metric_type == MetricType.CACHE_HIT_RATE
        ]
        
        # Should have at least critical alert
        severities = [alert.severity for alert in cache_alerts]
        assert AlertSeverity.CRITICAL in severities
    
    def test_trend_analysis(self):
        """Test performance trend analysis."""
        # Create trend data (increasing response time)
        base_time = datetime.now()
        base_value = 100.0
        
        # Add enough samples for trend analysis (20+ samples)
        for i in range(25):
            timestamp = base_time + timedelta(seconds=i)
            # Gradually increasing response time
            value = base_value + (i * 5)  # Increase by 5ms each sample
            self.monitor._record_metric(MetricType.RESPONSE_TIME, value, timestamp)
        
        # Analyze trends
        self.monitor._analyze_trends()
        
        # Should detect increasing trend
        samples = self.monitor._metrics_history[MetricType.RESPONSE_TIME]
        trend = self.monitor._calculate_trend(MetricType.RESPONSE_TIME, samples)
        
        assert trend is not None
        assert trend.trend_direction == "increasing"
        assert trend.change_percentage > 0
        assert trend.recent_average > trend.previous_average
    
    def test_stable_trend_detection(self):
        """Test detection of stable trends."""
        # Create stable data
        base_time = datetime.now()
        stable_value = 200.0
        
        # Add stable samples with minimal variation
        for i in range(25):
            timestamp = base_time + timedelta(seconds=i)
            # Add small random variation (within 5% range)
            variation = (i % 3 - 1) * 2  # -2, 0, +2
            value = stable_value + variation
            self.monitor._record_metric(MetricType.RESPONSE_TIME, value, timestamp)
        
        # Calculate trend
        samples = self.monitor._metrics_history[MetricType.RESPONSE_TIME]
        trend = self.monitor._calculate_trend(MetricType.RESPONSE_TIME, samples)
        
        assert trend is not None
        assert trend.trend_direction == "stable"
        assert abs(trend.change_percentage) < 5  # Less than 5% change
    
    def test_decreasing_trend_detection(self):
        """Test detection of decreasing trends."""
        # Create decreasing data
        base_time = datetime.now()
        base_value = 500.0
        
        # Add decreasing samples
        for i in range(25):
            timestamp = base_time + timedelta(seconds=i)
            # Gradually decreasing response time
            value = base_value - (i * 3)  # Decrease by 3ms each sample
            self.monitor._record_metric(MetricType.RESPONSE_TIME, value, timestamp)
        
        # Calculate trend
        samples = self.monitor._metrics_history[MetricType.RESPONSE_TIME]
        trend = self.monitor._calculate_trend(MetricType.RESPONSE_TIME, samples)
        
        assert trend is not None
        assert trend.trend_direction == "decreasing"
        assert trend.change_percentage < 0
        assert trend.recent_average < trend.previous_average
    
    def test_health_score_calculation(self):
        """Test health score calculations."""
        # Set up performance profiles for health calculation
        self.monitor._performance_profiles = {
            MetricType.CACHE_HIT_RATE: deque([MetricSample(datetime.now(), 75.0)]),
            MetricType.EVICTION_RATE: deque([MetricSample(datetime.now(), 5.0)]),
            MetricType.RESPONSE_TIME: deque([MetricSample(datetime.now(), 200.0)]),
            MetricType.MEMORY_USAGE: deque([MetricSample(datetime.now(), 300.0)]),
            MetricType.CPU_USAGE: deque([MetricSample(datetime.now(), 45.0)]),
            MetricType.ERROR_RATE: deque([MetricSample(datetime.now(), 1.0)])
        }
        
        # Simulate metrics history
        for metric_type, samples in self.monitor._performance_profiles.items():
            self.monitor._metrics_history[metric_type] = samples
        
        # Calculate health scores
        cache_score = self.monitor._calculate_cache_health_score()
        resource_score = self.monitor._calculate_resource_health_score()
        error_score = self.monitor._calculate_error_health_score()
        
        # Should be reasonable scores (good performance metrics)
        assert 80 <= cache_score <= 100  # Good cache performance
        assert 80 <= resource_score <= 100  # Good resource usage
        assert 90 <= error_score <= 100  # Low error rate
    
    def test_poor_health_score_calculation(self):
        """Test health score calculation with poor metrics."""
        # Set up poor performance metrics
        self.monitor._performance_profiles = {
            MetricType.CACHE_HIT_RATE: deque([MetricSample(datetime.now(), 30.0)]),  # Poor
            MetricType.EVICTION_RATE: deque([MetricSample(datetime.now(), 25.0)]),   # High
            MetricType.RESPONSE_TIME: deque([MetricSample(datetime.now(), 1500.0)]), # Slow
            MetricType.MEMORY_USAGE: deque([MetricSample(datetime.now(), 1200.0)]),  # High
            MetricType.CPU_USAGE: deque([MetricSample(datetime.now(), 85.0)]),       # High
            MetricType.ERROR_RATE: deque([MetricSample(datetime.now(), 12.0)])       # High
        }
        
        # Simulate metrics history
        for metric_type, samples in self.monitor._performance_profiles.items():
            self.monitor._metrics_history[metric_type] = samples
        
        # Calculate health scores
        cache_score = self.monitor._calculate_cache_health_score()
        resource_score = self.monitor._calculate_resource_health_score()
        error_score = self.monitor._calculate_error_health_score()
        
        # Should be low scores (poor performance metrics)
        assert cache_score < 70  # Poor cache performance
        assert resource_score < 70  # Poor resource usage
        assert error_score < 60  # High error rate
    
    def test_optimization_recommendations(self):
        """Test optimization recommendation generation."""
        # Create sample alerts and trends
        alerts = [
            PerformanceAlert(
                alert_id="test_alert",
                metric_type=MetricType.CACHE_HIT_RATE,
                severity=AlertSeverity.HIGH,
                message="Low hit rate",
                current_value=35.0,
                threshold=40.0
            )
        ]
        
        trends = [
            PerformanceTrend(
                metric_type=MetricType.RESPONSE_TIME,
                trend_direction="increasing",
                trend_strength=0.8,
                recent_average=800.0,
                previous_average=400.0,
                change_percentage=100.0,
                confidence_level=0.9
            )
        ]
        
        # Generate recommendations
        recommendations = self.monitor._generate_optimization_recommendations(
            overall_score=65.0,  # Below optimal
            alerts=alerts,
            trends=trends
        )
        
        # Should generate recommendations
        assert len(recommendations) > 0
        
        # Should include recommendations for detected issues
        rec_text = " ".join(recommendations).lower()
        assert "health" in rec_text or "performance" in rec_text
        assert "high-severity" in rec_text  # For high severity alert
        assert "response times" in rec_text or "increasing" in rec_text  # For trend
    
    def test_system_health_report_generation(self):
        """Test comprehensive system health report generation."""
        # Add some test data
        timestamp = datetime.now()
        self.monitor._record_metric(MetricType.CACHE_HIT_RATE, 70.0, timestamp)
        self.monitor._record_metric(MetricType.RESPONSE_TIME, 300.0, timestamp)
        
        # Generate health report
        report = self.monitor.generate_health_report()
        
        # Verify report structure
        assert isinstance(report, SystemHealthReport)
        assert isinstance(report.timestamp, datetime)
        assert 0 <= report.overall_health_score <= 100
        assert 0 <= report.cache_performance_score <= 100
        assert 0 <= report.system_resource_score <= 100
        assert 0 <= report.error_rate_score <= 100
        assert isinstance(report.alerts, list)
        assert isinstance(report.trends, list)
        assert isinstance(report.recommendations, list)
        assert isinstance(report.uptime, timedelta)
    
    def test_alert_acknowledgment(self):
        """Test alert acknowledgment functionality."""
        # Create and store an alert
        alert = PerformanceAlert(
            alert_id="ack_test_alert",
            metric_type=MetricType.CPU_USAGE,
            severity=AlertSeverity.MEDIUM,
            message="Test alert",
            current_value=75.0,
            threshold=70.0
        )
        self.monitor._active_alerts[alert.alert_id] = alert
        
        # Acknowledge alert
        result = self.monitor.acknowledge_alert(alert.alert_id, "Acknowledged by admin")
        
        assert result is True
        assert alert.acknowledged is True
        assert alert.resolution_notes == "Acknowledged by admin"
        
        # Test acknowledging non-existent alert
        result = self.monitor.acknowledge_alert("nonexistent_alert", "test")
        assert result is False
    
    def test_alert_clearing(self):
        """Test alert clearing functionality."""
        # Create and store an alert
        alert = PerformanceAlert(
            alert_id="clear_test_alert",
            metric_type=MetricType.MEMORY_USAGE,
            severity=AlertSeverity.LOW,
            message="Test alert",
            current_value=400.0,
            threshold=350.0
        )
        self.monitor._active_alerts[alert.alert_id] = alert
        
        # Clear alert
        result = self.monitor.clear_alert(alert.alert_id)
        
        assert result is True
        assert alert.alert_id not in self.monitor._active_alerts
        
        # Test clearing non-existent alert
        result = self.monitor.clear_alert("nonexistent_alert")
        assert result is False
    
    def test_performance_stats(self):
        """Test performance statistics tracking."""
        # Get initial stats
        stats = self.monitor.get_performance_stats()
        
        # Verify structure
        assert 'monitoring_uptime_seconds' in stats
        assert 'active_alerts_count' in stats
        assert 'total_alerts_history' in stats
        assert 'metrics_tracked' in stats
        assert 'is_monitoring_active' in stats
        
        # Initial values
        assert stats['active_alerts_count'] == 0
        assert stats['total_alerts_history'] == 0
        assert stats['is_monitoring_active'] == False
        
        # Add alert and check stats update
        alert = PerformanceAlert(
            alert_id="stats_test_alert",
            metric_type=MetricType.CACHE_HIT_RATE,
            severity=AlertSeverity.MEDIUM,
            message="Test alert",
            current_value=50.0,
            threshold=60.0
        )
        self.monitor._active_alerts[alert.alert_id] = alert
        self.monitor._alert_history.append(alert)
        
        updated_stats = self.monitor.get_performance_stats()
        assert updated_stats['active_alerts_count'] == 1
        assert updated_stats['total_alerts_history'] == 1
    
    def test_metrics_export(self):
        """Test metrics data export functionality."""
        # Add test metrics
        timestamp = datetime.now()
        self.monitor._record_metric(MetricType.CACHE_HIT_RATE, 75.0, timestamp, {"test": "metadata"})
        self.monitor._record_metric(MetricType.RESPONSE_TIME, 250.0, timestamp)
        
        # Export metrics
        export_data = self.monitor.export_metrics(hours=1, format="json")
        
        # Should be valid JSON
        import json
        parsed_data = json.loads(export_data)
        
        # Verify structure
        assert 'timestamp' in parsed_data
        assert 'export_parameters' in parsed_data
        assert 'metrics' in parsed_data
        
        # Check metrics data
        metrics = parsed_data['metrics']
        assert MetricType.CACHE_HIT_RATE.value in metrics
        assert MetricType.RESPONSE_TIME.value in metrics
        
        # Check sample structure
        hit_rate_samples = metrics[MetricType.CACHE_HIT_RATE.value]
        assert len(hit_rate_samples) == 1
        
        sample = hit_rate_samples[0]
        assert 'timestamp' in sample
        assert 'value' in sample
        assert 'metadata' in sample
        assert sample['value'] == 75.0
    
    def test_default_alert_thresholds(self):
        """Test default alert thresholds."""
        # Create monitor with default thresholds
        default_monitor = PerformanceMonitor()
        
        thresholds = default_monitor._alert_thresholds
        
        # Should have thresholds for all important metrics
        assert MetricType.CACHE_HIT_RATE in thresholds
        assert MetricType.RESPONSE_TIME in thresholds
        assert MetricType.ERROR_RATE in thresholds
        assert MetricType.MEMORY_USAGE in thresholds
        assert MetricType.CPU_USAGE in thresholds
        
        # Each metric should have multiple severity levels
        for metric_type, metric_thresholds in thresholds.items():
            assert AlertSeverity.MEDIUM.value in metric_thresholds
            assert AlertSeverity.HIGH.value in metric_thresholds
            assert AlertSeverity.CRITICAL.value in metric_thresholds
    
    def test_monitor_shutdown(self):
        """Test performance monitor shutdown."""
        # Start monitoring
        self.monitor.start_monitoring()
        assert self.monitor._monitoring_active
        
        # Shutdown
        self.monitor.shutdown()
        
        # Should stop monitoring and clean up
        assert not self.monitor._monitoring_active
        assert len(self.monitor._active_alerts) == 0
        assert len(self.monitor._metrics_history) == 0


class TestPerformanceMonitorGlobalFunction:
    """Test global performance monitor function."""
    
    def test_get_performance_monitor(self):
        """Test global performance monitor retrieval."""
        monitor1 = get_performance_monitor()
        monitor2 = get_performance_monitor()
        
        # Should return same instance
        assert monitor1 is monitor2
        assert isinstance(monitor1, PerformanceMonitor)
        
        # Cleanup
        monitor1.shutdown()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])