#!/usr/bin/env python3
"""
Structured logging utility for Scenario 04

Provides consistent logging across all modules.
"""

import logging
import os
from datetime import datetime
from typing import Optional


class ScenarioLogger:
    """
    Structured logger for scenario components.

    Provides different log methods for different event types.
    """

    def __init__(self, name: str, log_dir: str, level: str = "INFO", log_format: Optional[str] = None):
        """
        Initialize logger.

        Args:
            name: Logger name (usually module name)
            log_dir: Directory to store log files
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            log_format: Custom log format string
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.upper()))

        # Ensure log directory exists
        os.makedirs(log_dir, exist_ok=True)

        # Create file handler
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(log_dir, f"{name}_{timestamp}.log")

        fh = logging.FileHandler(log_file)
        fh.setLevel(getattr(logging, level.upper()))

        # Create formatter
        if log_format is None:
            log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

        formatter = logging.Formatter(log_format)
        fh.setFormatter(formatter)

        # Add handler
        self.logger.addHandler(fh)

        # Also log to console
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        self.logger.addHandler(ch)

    def debug(self, msg: str, **kwargs):
        """Log debug message"""
        self.logger.debug(msg, extra=kwargs)

    def info(self, msg: str, **kwargs):
        """Log info message"""
        self.logger.info(msg, extra=kwargs)

    def warning(self, msg: str, **kwargs):
        """Log warning message"""
        self.logger.warning(msg, extra=kwargs)

    def error(self, msg: str, **kwargs):
        """Log error message"""
        self.logger.error(msg, extra=kwargs)

    def exception(self, msg: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(msg, extra=kwargs)

    def network_event(self, event: str, **kwargs):
        """Log network-related event"""
        self.logger.info(f"[NETWORK] {event}", extra=kwargs)

    def mqtt_event(self, event: str, **kwargs):
        """Log MQTT-related event"""
        self.logger.info(f"[MQTT] {event}", extra=kwargs)

    def qos_event(self, event: str, **kwargs):
        """Log QoS-related event"""
        self.logger.info(f"[QOS] {event}", extra=kwargs)

    def controller_event(self, event: str, **kwargs):
        """Log controller-related event"""
        self.logger.info(f"[CONTROLLER] {event}", extra=kwargs)

    def flow_event(self, event: str, **kwargs):
        """Log flow-related event"""
        self.logger.info(f"[FLOW] {event}", extra=kwargs)

    def separator(self, char: str = "=", length: int = 70):
        """Log separator line"""
        self.logger.info(char * length)


def get_mininet_logger(log_level: str = "info"):
    """
    Get logger for Mininet output.

    Args:
        log_level: Mininet log level (info, debug, warning, error)

    Returns:
        Log level string for Mininet
    """
    return log_level.lower()
