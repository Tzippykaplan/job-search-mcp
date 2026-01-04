"""Logging configuration for the MCP server."""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logging(level: str = "INFO", log_to_file: bool = True) -> logging.Logger:
    """
    Configure logging for the MCP server.
    
    Sets up both console and file logging with appropriate formatters and handlers.
    Console shows INFO+ messages, file captures DEBUG+ for detailed analysis.
    
    Args:
        level: Minimum logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_to_file: Whether to enable file logging with rotation.
    
    Returns:
        Configured root logger instance.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())
    
    # Clear any existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Format: timestamp | level | module | message
    formatter = logging.Formatter(
        fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler - INFO and above for clean real-time output.
    # Use stderr to avoid corrupting MCP stdio protocol on stdout.
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File handler - DEBUG and above for detailed analysis
    if log_to_file:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_dir / "mcp-server.log",
            maxBytes=10 * 1024 * 1024,  # 10MB per file
            backupCount=5,  # Keep 5 backup files (total 50MB)
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)
    
    root_logger.info("Logging configured", extra={
        "level": level,
        "file_logging": log_to_file,
        "log_dir": str(log_dir) if log_to_file else None
    })
    
    return root_logger
