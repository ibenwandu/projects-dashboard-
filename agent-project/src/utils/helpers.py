"""
Helper Functions

This module contains helper functions for the agent ecosystem.
"""

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from agents.base_agent import Task, Message, TaskPriority


def create_task(name: str, description: str = "", data: Dict[str, Any] = None, 
                priority: TaskPriority = TaskPriority.NORMAL) -> Task:
    """
    Create a new task.
    
    Args:
        name: Task name
        description: Task description
        data: Task data
        priority: Task priority
        
    Returns:
        New task instance
    """
    return Task(
        name=name,
        description=description,
        data=data or {},
        priority=priority
    )


def create_message(sender: str, recipient: str, message_type: str, 
                  content: Any = None, priority: TaskPriority = TaskPriority.NORMAL) -> Message:
    """
    Create a new message.
    
    Args:
        sender: Sender agent name
        recipient: Recipient agent name
        message_type: Type of message
        content: Message content
        priority: Message priority
        
    Returns:
        New message instance
    """
    return Message(
        sender=sender,
        recipient=recipient,
        message_type=message_type,
        content=content,
        priority=priority
    )


def generate_workflow_id() -> str:
    """
    Generate a unique workflow ID.
    
    Returns:
        Unique workflow ID
    """
    return f"workflow_{uuid.uuid4().hex[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"


def validate_agent_name(name: str) -> bool:
    """
    Validate agent name.
    
    Args:
        name: Agent name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not name or not isinstance(name, str):
        return False
    
    # Check for valid characters
    import re
    if not re.match(r'^[a-zA-Z0-9_-]+$', name):
        return False
    
    # Check length
    if len(name) < 1 or len(name) > 50:
        return False
    
    return True


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename for safe file system operations.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    import string
    
    # Remove or replace invalid characters
    valid_chars = f'-_.() {string.ascii_letters}{string.digits}'
    sanitized = ''.join(c for c in filename if c in valid_chars)
    
    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = 'unnamed_file'
    
    return sanitized


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_file_size(bytes_size: int) -> str:
    """
    Format file size in bytes to human-readable string.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f}{unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f}PB"


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two dictionaries, with dict2 taking precedence.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    result.update(dict2)
    return result


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries, with dict2 taking precedence.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Deep merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def flatten_dict(d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
    """
    Flatten a nested dictionary.
    
    Args:
        d: Dictionary to flatten
        parent_key: Parent key prefix
        sep: Separator for nested keys
        
    Returns:
        Flattened dictionary
    """
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        lst: List to chunk
        chunk_size: Size of each chunk
        
    Returns:
        List of chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def safe_get_nested(d: Dict[str, Any], keys: List[str], default: Any = None) -> Any:
    """
    Safely get a nested dictionary value.
    
    Args:
        d: Dictionary to search
        keys: List of keys to traverse
        default: Default value if key not found
        
    Returns:
        Value at the specified path or default
    """
    current = d
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    return current


def retry_on_exception(func, max_retries: int = 3, delay: float = 1.0, 
                      exceptions: tuple = (Exception,)):
    """
    Decorator to retry function on exception.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
        exceptions: Tuple of exceptions to catch
        
    Returns:
        Decorated function
    """
    import time
    
    def wrapper(*args, **kwargs):
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                if attempt < max_retries:
                    time.sleep(delay)
                    continue
                else:
                    raise last_exception
        
        return None
    
    return wrapper


def timeout_handler(timeout_seconds: float = 30.0):
    """
    Decorator to add timeout to function execution.
    
    Args:
        timeout_seconds: Timeout in seconds
        
    Returns:
        Decorated function
    """
    import signal
    import functools
    
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            def timeout_signal_handler(signum, frame):
                raise TimeoutError(f"Function {func.__name__} timed out after {timeout_seconds} seconds")
            
            # Set up signal handler
            old_handler = signal.signal(signal.SIGALRM, timeout_signal_handler)
            signal.alarm(int(timeout_seconds))
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # Restore signal handler
                signal.alarm(0)
                signal.signal(signal.SIGALRM, old_handler)
        
        return wrapper
    return decorator


def calculate_percentage(part: float, total: float) -> float:
    """
    Calculate percentage.
    
    Args:
        part: Part value
        total: Total value
        
    Returns:
        Percentage value
    """
    if total == 0:
        return 0.0
    return (part / total) * 100.0


def calculate_average(values: List[float]) -> float:
    """
    Calculate average of a list of values.
    
    Args:
        values: List of numeric values
        
    Returns:
        Average value
    """
    if not values:
        return 0.0
    return sum(values) / len(values)


def calculate_median(values: List[float]) -> float:
    """
    Calculate median of a list of values.
    
    Args:
        values: List of numeric values
        
    Returns:
        Median value
    """
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    n = len(sorted_values)
    
    if n % 2 == 0:
        return (sorted_values[n//2 - 1] + sorted_values[n//2]) / 2
    else:
        return sorted_values[n//2]


def is_valid_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.
    
    Args:
        url: URL to validate
        
    Returns:
        True if valid, False otherwise
    """
    import re
    pattern = r'^https?://(?:[-\w.])+(?:[:\d]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:#(?:[\w.])*)?)?$'
    return bool(re.match(pattern, url))
