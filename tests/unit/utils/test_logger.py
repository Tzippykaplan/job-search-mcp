"""Unit tests for logging configuration."""

import logging
from pathlib import Path
from job_mcp.utils.logger import setup_logging


def test_logging_setup_creates_handlers():
    """Test that setup_logging creates console and file handlers."""
    # Clear any existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Setup logging
    logger = setup_logging(level="INFO", log_to_file=True)
    
    # Should have 2 handlers: console + file
    assert len(logger.handlers) == 2
    
    # Check handler types
    handler_types = [type(h).__name__ for h in logger.handlers]
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" in handler_types


def test_logging_setup_without_file():
    """Test that setup_logging works without file logging."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    # Setup logging without file
    logger = setup_logging(level="INFO", log_to_file=False)
    
    # Should have only 1 handler: console
    assert len(logger.handlers) == 1
    assert type(logger.handlers[0]).__name__ == "StreamHandler"


def test_logging_setup_creates_log_directory():
    """Test that setup_logging creates logs directory."""
    setup_logging(level="INFO", log_to_file=True)
    
    log_dir = Path("logs")
    assert log_dir.exists()
    assert log_dir.is_dir()


def test_logging_levels_configured():
    """Test that logging levels are properly configured."""
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    
    logger = setup_logging(level="DEBUG", log_to_file=False)
    
    # Root logger should be at DEBUG level
    assert logger.level == logging.DEBUG
    
    # Console handler should be at INFO level
    console_handler = logger.handlers[0]
    assert console_handler.level == logging.INFO
