"""
Structured Logging Configuration
================================
JSON-formatted logging with rotation, levels per component,
and metrics collection for CityEstate.
"""

import json
import logging
import logging.handlers
import sys
from datetime import datetime, timezone
from pathlib import Path


class JSONFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_entry["extra"] = record.extra_data

        return json.dumps(log_entry, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable console formatter."""

    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelname, "")
        reset = self.RESET

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        level = f"{color}{record.levelname:8s}{reset}"
        name = record.name
        message = record.getMessage()

        return f"{timestamp} [{level}] {name}: {message}"


def setup_logging(
    log_dir: str | None = None,
    log_level: str = "INFO",
    enable_json: bool = False,
    enable_file_rotation: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
) -> None:
    """Configure logging for CityEstate.

    Args:
        log_dir: Directory for log files (None = no file logging)
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_json: Enable JSON formatted logs
        enable_file_rotation: Enable rotating file handler
        max_bytes: Maximum log file size before rotation
        backup_count: Number of backup files to keep
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    if enable_json:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(ConsoleFormatter())
    root_logger.addHandler(console_handler)

    # File handler (if log_dir specified)
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

        if enable_file_rotation:
            file_handler = logging.handlers.RotatingFileHandler(
                log_path / "cityestate.log",
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
        else:
            file_handler = logging.FileHandler(
                log_path / "cityestate.log",
                encoding="utf-8",
            )

        if enable_json:
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            ))

        root_logger.addHandler(file_handler)

    # Component-specific log levels
    component_levels = {
        "uvicorn": logging.WARNING,
        "uvicorn.access": logging.WARNING,
        "sqlalchemy.engine": logging.WARNING,
        "playwright": logging.WARNING,
        "httpx": logging.WARNING,
    }
    for component, level in component_levels.items():
        logging.getLogger(component).setLevel(level)

    # Suppress noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)

    logging.info("Logging initialized (level=%s, json=%s)", log_level, enable_json)


class MetricsCollector:
    """Simple in-memory metrics collector."""

    def __init__(self) -> None:
        self._metrics: dict[str, dict] = {}
        self._counters: dict[str, int] = {}
        self._timers: dict[str, list[float]] = {}

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter."""
        self._counters[name] = self._counters.get(name, 0) + value

    def record_timer(self, name: str, duration_ms: float) -> None:
        """Record a timer value."""
        if name not in self._timers:
            self._timers[name] = []
        self._timers[name].append(duration_ms)
        # Keep only last 100 values
        if len(self._timers[name]) > 100:
            self._timers[name] = self._timers[name][-100:]

    def get_counter(self, name: str) -> int:
        """Get counter value."""
        return self._counters.get(name, 0)

    def get_timer_stats(self, name: str) -> dict:
        """Get timer statistics."""
        values = self._timers.get(name, [])
        if not values:
            return {"count": 0, "avg": 0, "min": 0, "max": 0, "p95": 0}

        sorted_values = sorted(values)
        count = len(sorted_values)
        avg = sum(sorted_values) / count
        p95_index = int(count * 0.95)
        p95 = sorted_values[min(p95_index, count - 1)]

        return {
            "count": count,
            "avg": round(avg, 2),
            "min": round(sorted_values[0], 2),
            "max": round(sorted_values[-1], 2),
            "p95": round(p95, 2),
        }

    def get_all_metrics(self) -> dict:
        """Get all metrics."""
        return {
            "counters": self._counters.copy(),
            "timers": {name: self.get_timer_stats(name) for name in self._timers},
        }

    def reset(self) -> None:
        """Reset all metrics."""
        self._counters.clear()
        self._timers.clear()


# Global metrics instance
metrics = MetricsCollector()
