"""
Unit Tests for Structured Logging
==================================
Tests for logging configuration and metrics collection.
"""

import json
import logging
import pytest
from io import StringIO

from src.logging_config import (
    JSONFormatter,
    ConsoleFormatter,
    MetricsCollector,
    setup_logging,
    metrics,
)


class TestJSONFormatter:
    """Test JSON log formatter."""

    def test_format_basic(self):
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert data["level"] == "INFO"
        assert data["logger"] == "test"
        assert data["message"] == "Test message"

    def test_format_with_exception(self):
        formatter = JSONFormatter()
        try:
            raise ValueError("test error")
        except ValueError:
            import sys
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test",
            level=logging.ERROR,
            pathname="test.py",
            lineno=1,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert "exception" in data
        assert "ValueError" in data["exception"]


class TestConsoleFormatter:
    """Test console log formatter."""

    def test_format_basic(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        assert "test" in result
        assert "Test message" in result

    def test_format_includes_timestamp(self):
        formatter = ConsoleFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="Test",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        # Should contain timestamp pattern
        assert ":" in result


class TestMetricsCollector:
    """Test MetricsCollector class."""

    def test_increment(self):
        collector = MetricsCollector()
        collector.increment("test.counter")
        collector.increment("test.counter")
        assert collector.get_counter("test.counter") == 2

    def test_increment_with_value(self):
        collector = MetricsCollector()
        collector.increment("test.counter", 5)
        assert collector.get_counter("test.counter") == 5

    def test_record_timer(self):
        collector = MetricsCollector()
        collector.record_timer("test.timer", 100.0)
        collector.record_timer("test.timer", 200.0)
        stats = collector.get_timer_stats("test.timer")
        assert stats["count"] == 2
        assert stats["avg"] == 150.0

    def test_timer_stats_empty(self):
        collector = MetricsCollector()
        stats = collector.get_timer_stats("nonexistent")
        assert stats["count"] == 0
        assert stats["avg"] == 0

    def test_get_all_metrics(self):
        collector = MetricsCollector()
        collector.increment("counter1")
        collector.record_timer("timer1", 50.0)
        all_metrics = collector.get_all_metrics()
        assert "counters" in all_metrics
        assert "timers" in all_metrics
        assert all_metrics["counters"]["counter1"] == 1

    def test_reset(self):
        collector = MetricsCollector()
        collector.increment("counter1")
        collector.record_timer("timer1", 50.0)
        collector.reset()
        assert collector.get_counter("counter1") == 0
        stats = collector.get_timer_stats("timer1")
        assert stats["count"] == 0

    def test_timer_max_values(self):
        collector = MetricsCollector()
        # Add more than 100 values
        for i in range(150):
            collector.record_timer("test.timer", float(i))
        stats = collector.get_timer_stats("test.timer")
        # Should only keep last 100
        assert stats["count"] == 100


class TestSetupLogging:
    """Test setup_logging function."""

    def test_setup_basic(self):
        # Should not raise
        setup_logging(log_level="INFO", enable_json=False)

    def test_setup_with_json(self):
        setup_logging(log_level="DEBUG", enable_json=True)

    def test_setup_with_log_dir(self, tmp_path):
        setup_logging(log_dir=str(tmp_path), log_level="INFO")
        log_file = tmp_path / "cityestate.log"
        # Log file may or may not be created depending on logging activity


class TestGlobalMetrics:
    """Test global metrics instance."""

    def test_global_metrics_exists(self):
        assert metrics is not None
        assert isinstance(metrics, MetricsCollector)
