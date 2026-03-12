"""
Logging Configuration

This module handles logging setup and configuration for the agent ecosystem.
"""

import os
import sys
from pathlib import Path
from loguru import logger
from typing import Dict, Any

from .config import get_logging_config


def setup_logging(config: Dict[str, Any] = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        config: Logging configuration dictionary
    """
    if config is None:
        config = get_logging_config()
    
    # Remove default logger
    logger.remove()
    
    # Get log level
    log_level = config.get('level', 'INFO')
    
    # Get log format
    log_format = config.get('format', 
        "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}")
    
    # Setup console logging
    logger.add(
        sys.stdout,
        format=log_format,
        level=log_level,
        colorize=True
    )
    
    # Setup file logging if specified
    log_file = config.get('file')
    if log_file:
        # Create logs directory if it doesn't exist
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Get file logging settings
        max_file_size = config.get('max_file_size', '10MB')
        rotation = config.get('rotation', '1 day')
        
        logger.add(
            log_file,
            format=log_format,
            level=log_level,
            rotation=rotation,
            retention='30 days',
            compression='zip'
        )
    
    logger.info("Logging setup completed")


def get_logger(name: str = None) -> logger:
    """
    Get a logger instance.
    
    Args:
        name: Logger name
        
    Returns:
        Logger instance
    """
    if name:
        return logger.bind(name=name)
    return logger


def set_log_level(level: str) -> None:
    """
    Set the log level.
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Remove existing handlers
    logger.remove()
    
    # Add new handlers with updated level
    logger.add(sys.stdout, level=level, colorize=True)
    
    # Re-add file handler if it exists
    config = get_logging_config()
    log_file = config.get('file')
    if log_file:
        log_format = config.get('format', 
            "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}")
        max_file_size = config.get('max_file_size', '10MB')
        rotation = config.get('rotation', '1 day')
        
        logger.add(
            log_file,
            format=log_format,
            level=level,
            rotation=rotation,
            retention='30 days',
            compression='zip'
        )
    
    logger.info(f"Log level set to {level}")


def log_function_call(func_name: str, args: tuple = None, kwargs: dict = None):
    """
    Decorator to log function calls.
    
    Args:
        func_name: Function name
        args: Function arguments
        kwargs: Function keyword arguments
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            logger.debug(f"Calling {func_name} with args={args}, kwargs={kwargs}")
            try:
                result = func(*args, **kwargs)
                logger.debug(f"{func_name} completed successfully")
                return result
            except Exception as e:
                logger.error(f"{func_name} failed with error: {str(e)}")
                raise
        return wrapper
    return decorator


def log_agent_activity(agent_name: str, activity: str, details: dict = None):
    """
    Log agent activity.
    
    Args:
        agent_name: Name of the agent
        activity: Activity description
        details: Additional details
    """
    if details:
        logger.info(f"Agent {agent_name}: {activity} - {details}")
    else:
        logger.info(f"Agent {agent_name}: {activity}")


def log_workflow_progress(workflow_id: str, step: str, status: str, details: dict = None):
    """
    Log workflow progress.
    
    Args:
        workflow_id: Workflow ID
        step: Current step
        status: Step status
        details: Additional details
    """
    if details:
        logger.info(f"Workflow {workflow_id} - Step {step}: {status} - {details}")
    else:
        logger.info(f"Workflow {workflow_id} - Step {step}: {status}")


def log_performance_metrics(component: str, metrics: dict):
    """
    Log performance metrics.
    
    Args:
        component: Component name
        metrics: Performance metrics
    """
    logger.info(f"Performance metrics for {component}: {metrics}")


def log_error(error: Exception, context: str = None, details: dict = None):
    """
    Log an error with context.
    
    Args:
        error: Exception that occurred
        context: Error context
        details: Additional details
    """
    if context and details:
        logger.error(f"Error in {context}: {str(error)} - {details}")
    elif context:
        logger.error(f"Error in {context}: {str(error)}")
    else:
        logger.error(f"Error: {str(error)}")














