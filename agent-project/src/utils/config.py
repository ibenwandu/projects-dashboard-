"""
Configuration Management

This module handles loading and managing configuration for the agent ecosystem.
"""

import os
import yaml
from typing import Any, Dict, Optional
from pathlib import Path

# Global configuration cache
_config_cache: Optional[Dict[str, Any]] = None


def load_config(config_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
    """
    global _config_cache
    
    if _config_cache is not None:
        return _config_cache
    
    if config_path is None:
        # Default config path
        config_path = Path(__file__).parent.parent.parent / "config" / "config.yaml"
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            config = yaml.safe_load(file)
        
        # Process environment variables
        config = _process_environment_variables(config)
        
        # Cache the configuration
        _config_cache = config
        
        return config
        
    except Exception as e:
        raise RuntimeError(f"Failed to load configuration: {str(e)}")


def get_config(section: Optional[str] = None) -> Any:
    """
    Get configuration value or section.
    
    Args:
        section: Configuration section to retrieve
        
    Returns:
        Configuration value or section
    """
    config = load_config()
    
    if section is None:
        return config
    
    if section not in config:
        raise KeyError(f"Configuration section not found: {section}")
    
    return config[section]


def _process_environment_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process environment variables in configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Processed configuration
    """
    def _process_value(value):
        if isinstance(value, str) and value.startswith('${') and value.endswith('}'):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        elif isinstance(value, dict):
            return {k: _process_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [_process_value(v) for v in value]
        else:
            return value
    
    return _process_value(config)


def reload_config() -> Dict[str, Any]:
    """
    Reload configuration from file.
    
    Returns:
        Updated configuration dictionary
    """
    global _config_cache
    _config_cache = None
    return load_config()


def get_agent_config(agent_type: str) -> Dict[str, Any]:
    """
    Get configuration for a specific agent type.
    
    Args:
        agent_type: Type of agent
        
    Returns:
        Agent configuration
    """
    config = load_config()
    
    if 'sub_agents' not in config:
        return {}
    
    return config['sub_agents'].get(agent_type, {})


def get_database_config() -> Dict[str, Any]:
    """
    Get database configuration.
    
    Returns:
        Database configuration
    """
    return get_config('database')


def get_logging_config() -> Dict[str, Any]:
    """
    Get logging configuration.
    
    Returns:
        Logging configuration
    """
    return get_config('logging')


def get_external_services_config() -> Dict[str, Any]:
    """
    Get external services configuration.
    
    Returns:
        External services configuration
    """
    return get_config('external_services')














