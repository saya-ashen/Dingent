"""
Enhanced logging manager with structured logging support for dashboard display.
"""

import threading
from collections import deque
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Literal

from loguru import logger


@dataclass
class LogEntry:
    """Structured log entry for dashboard display."""

    timestamp: datetime
    level: str
    message: str
    module: str
    function: str
    context: dict[str, Any] | None = None
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert log entry to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class LogManager:
    """
    Enhanced logging manager that captures structured logs for dashboard display.

    Features:
    - In-memory log storage with configurable retention
    - Structured logging with context and correlation IDs
    - Thread-safe operations
    - Dashboard integration ready
    """

    def __init__(self, max_logs: int = 1000):
        """
        Initialize the log manager.

        Args:
            max_logs: Maximum number of logs to keep in memory
        """
        self.max_logs = max_logs
        self._logs: deque[LogEntry] = deque(maxlen=max_logs)
        self._lock = threading.RLock()
        self._setup_loguru_handler()

    def _setup_loguru_handler(self):
        """Set up loguru handler to capture logs for dashboard."""

        def log_sink(message):
            try:
                record = message.record
                log_entry = LogEntry(
                    timestamp=record["time"],
                    level=record["level"].name,
                    message=record["message"],
                    module=record["module"],
                    function=record["function"],
                    context=record.get("extra", {}),
                    correlation_id=record.get("extra", {}).get("correlation_id"),
                )
                self._add_log_entry(log_entry)
            except Exception as e:
                # Avoid infinite recursion by using basic print
                print(f"Error in log sink: {e}")

        # Add custom sink to loguru
        logger.add(log_sink, level="DEBUG", format="{message}")

    def _add_log_entry(self, entry: LogEntry):
        """Thread-safe addition of log entry."""
        with self._lock:
            self._logs.append(entry)

    def get_logs(self, level: str | None = None, module: str | None = None, limit: int | None = None, search: str | None = None) -> list[LogEntry]:
        """
        Retrieve logs with optional filtering.

        Args:
            level: Filter by log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            module: Filter by module name
            limit: Maximum number of logs to return
            search: Search term in message content

        Returns:
            List of matching log entries
        """
        with self._lock:
            logs = list(self._logs)

        # Apply filters
        if level:
            logs = [log for log in logs if log.level == level.upper()]

        if module:
            logs = [log for log in logs if module.lower() in log.module.lower()]

        if search:
            search_lower = search.lower()
            logs = [log for log in logs if search_lower in log.message.lower()]

        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.timestamp, reverse=True)

        # Apply limit
        if limit:
            logs = logs[:limit]

        return logs

    def get_log_stats(self) -> dict[str, Any]:
        """Get logging statistics for dashboard display."""
        with self._lock:
            logs = list(self._logs)

        if not logs:
            return {"total_logs": 0, "by_level": {}, "by_module": {}, "oldest_timestamp": None, "newest_timestamp": None}

        # Count by level
        by_level = {}
        by_module = {}

        for log in logs:
            by_level[log.level] = by_level.get(log.level, 0) + 1
            by_module[log.module] = by_module.get(log.module, 0) + 1

        return {
            "total_logs": len(logs),
            "by_level": by_level,
            "by_module": by_module,
            "oldest_timestamp": min(log.timestamp for log in logs).isoformat(),
            "newest_timestamp": max(log.timestamp for log in logs).isoformat(),
        }

    def clear_logs(self):
        """Clear all stored logs."""
        with self._lock:
            self._logs.clear()

    def log_with_context(self, level: str, message: str, context: dict[str, Any] | None = None, correlation_id: str | None = None):
        """
        Log a message with additional context for structured logging.

        Args:
            level: Log level (debug, info, warning, error, critical)
            message: Log message
            context: Additional context data
            correlation_id: Correlation ID for tracking related operations
        """
        extra = {}
        if context:
            extra.update(context)
        if correlation_id:
            extra["correlation_id"] = correlation_id

        logger_method = getattr(logger, level.lower())
        logger_method(message, **extra) if extra else logger_method(message)


# Global log manager instance
_log_manager: LogManager | None = None


def get_log_manager() -> LogManager:
    """Get the global log manager instance."""
    global _log_manager
    if _log_manager is None:
        _log_manager = LogManager()
        logger.info("Enhanced log manager initialized for dashboard display")
    return _log_manager


def log_with_context(level: Literal["error", "info", "warning"], message: str, context: dict[str, Any] | None = None, correlation_id: str | None = None):
    """Convenience function for structured logging."""
    get_log_manager().log_with_context(level, message, context, correlation_id)
