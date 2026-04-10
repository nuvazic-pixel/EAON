"""
EAON 2.0 — Structured Logging Setup
====================================
JSON-formatted logs with structlog for production observability.
"""

import sys
import logging
from typing import Optional
from pathlib import Path

import structlog
from structlog.types import Processor


def setup_logging(
    level: str = "INFO",
    format: str = "json",
    log_file: Optional[str] = None,
    app_name: str = "EAON",
    version: str = "2.0.0",
) -> structlog.BoundLogger:
    """
    Configure structlog with JSON or console output.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Output format ('json' or 'console')
        log_file: Optional file path for log output
        app_name: Application name for log context
        version: Application version for log context
    
    Returns:
        Configured structlog logger
    """
    
    # Shared processors for all outputs
    shared_processors: list[Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    
    # Format-specific processors
    if format == "json":
        final_processors: list[Processor] = [
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Console format with colors
        final_processors = [
            structlog.dev.ConsoleRenderer(colors=True),
        ]
    
    # Configure structlog
    structlog.configure(
        processors=shared_processors + final_processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Also configure stdlib logging (for third-party libs)
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=_get_handlers(log_file),
    )
    
    # Silence noisy loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    
    # Create base logger with app context
    logger = structlog.get_logger()
    logger = logger.bind(app=app_name, version=version)
    
    return logger


def _get_handlers(log_file: Optional[str]) -> list[logging.Handler]:
    """Build logging handlers list."""
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
    
    if log_file:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handlers.append(logging.FileHandler(log_file))
    
    return handlers


def get_logger(name: Optional[str] = None) -> structlog.BoundLogger:
    """
    Get a logger instance, optionally bound to a component name.
    
    Args:
        name: Optional component name to bind
    
    Returns:
        Structlog bound logger
    """
    logger = structlog.get_logger()
    if name:
        logger = logger.bind(component=name)
    return logger


class LogContext:
    """Context manager for adding temporary log context."""
    
    def __init__(self, **kwargs):
        self.context = kwargs
        self._token = None
    
    def __enter__(self):
        self._token = structlog.contextvars.bind_contextvars(**self.context)
        return self
    
    def __exit__(self, *args):
        if self._token:
            structlog.contextvars.unbind_contextvars(*self.context.keys())


def log_event(
    logger: structlog.BoundLogger,
    event: str,
    level: str = "info",
    **kwargs
) -> None:
    """
    Log a structured event.
    
    Args:
        logger: The logger instance
        event: Event name/description
        level: Log level
        **kwargs: Additional context fields
    """
    log_method = getattr(logger, level.lower(), logger.info)
    log_method(event, **kwargs)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SPECIALIZED LOGGERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AuditLogger:
    """
    Immutable audit logger for security events.
    Logs are append-only and include cryptographic context.
    """
    
    def __init__(self, logger: Optional[structlog.BoundLogger] = None):
        self.logger = (logger or get_logger()).bind(audit=True)
    
    def log_decision(
        self,
        action: str,
        score: int,
        reasons: list[str],
        src_ip: Optional[str] = None,
        dst_ip: Optional[str] = None,
        intel_summary: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> None:
        """Log a security decision."""
        self.logger.info(
            "security_decision",
            action=action,
            score=score,
            reasons=reasons,
            src_ip=src_ip,
            dst_ip=dst_ip,
            intel_summary=intel_summary,
            user_id=user_id,
        )
    
    def log_intel_lookup(
        self,
        ip: str,
        source: str,
        result: dict,
        cache_hit: bool = False,
        latency_ms: float = 0,
    ) -> None:
        """Log an intel lookup."""
        self.logger.debug(
            "intel_lookup",
            ip=ip,
            source=source,
            result_summary=self._summarize(result),
            cache_hit=cache_hit,
            latency_ms=round(latency_ms, 2),
        )
    
    def log_notification(
        self,
        channel: str,
        success: bool,
        target: Optional[str] = None,
        error: Optional[str] = None,
    ) -> None:
        """Log a notification attempt."""
        self.logger.info(
            "notification_sent",
            channel=channel,
            success=success,
            target=target,
            error=error,
        )
    
    def log_mode_change(
        self,
        old_mode: str,
        new_mode: str,
        reason: str,
    ) -> None:
        """Log orchestrator mode change."""
        self.logger.warning(
            "mode_change",
            old_mode=old_mode,
            new_mode=new_mode,
            reason=reason,
        )
    
    @staticmethod
    def _summarize(data: dict) -> dict:
        """Create a summary of complex data for logging."""
        if not data:
            return {}
        return {
            "keys": list(data.keys())[:10],
            "size": len(str(data)),
        }


class MetricsLogger:
    """Logger for performance metrics and telemetry."""
    
    def __init__(self, logger: Optional[structlog.BoundLogger] = None):
        self.logger = (logger or get_logger()).bind(metrics=True)
    
    def log_latency(
        self,
        operation: str,
        latency_ms: float,
        success: bool = True,
    ) -> None:
        """Log operation latency."""
        self.logger.debug(
            "latency",
            operation=operation,
            latency_ms=round(latency_ms, 2),
            success=success,
        )
    
    def log_throughput(
        self,
        operation: str,
        count: int,
        period_seconds: float,
    ) -> None:
        """Log throughput metric."""
        rate = count / period_seconds if period_seconds > 0 else 0
        self.logger.info(
            "throughput",
            operation=operation,
            count=count,
            period_seconds=period_seconds,
            rate_per_second=round(rate, 2),
        )
    
    def log_cache_stats(
        self,
        hits: int,
        misses: int,
        size: int,
    ) -> None:
        """Log cache statistics."""
        total = hits + misses
        hit_rate = (hits / total * 100) if total > 0 else 0
        self.logger.info(
            "cache_stats",
            hits=hits,
            misses=misses,
            size=size,
            hit_rate_percent=round(hit_rate, 2),
        )
