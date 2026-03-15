"""Tests for Emy Brain configuration."""

import pytest
import os
import importlib
import sys


def test_config_loads_from_environment():
    """Test that config reads environment variables."""
    # Save original environment
    original_env = {
        'BRAIN_HOST': os.environ.get('BRAIN_HOST'),
        'BRAIN_PORT': os.environ.get('BRAIN_PORT'),
        'ENV': os.environ.get('ENV'),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL'),
        'BRAIN_DB_PATH': os.environ.get('BRAIN_DB_PATH'),
    }

    try:
        # Set test environment
        os.environ['BRAIN_HOST'] = '127.0.0.1'
        os.environ['BRAIN_PORT'] = '9001'
        os.environ['ENV'] = 'testing'
        os.environ['LOG_LEVEL'] = 'DEBUG'
        os.environ['BRAIN_DB_PATH'] = '/tmp/test.db'

        # Reimport config to pick up env vars
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']

        import emy.brain.config as config_module

        # Verify values
        assert config_module.BRAIN_HOST == '127.0.0.1'
        assert config_module.BRAIN_PORT == 9001
        assert config_module.ENV == 'testing'
        assert config_module.LOG_LEVEL_STR == 'DEBUG'
        assert str(config_module.BRAIN_DB_PATH) == '/tmp/test.db'

    finally:
        # Restore original environment
        for var, val in original_env.items():
            if val is not None:
                os.environ[var] = val
            else:
                os.environ.pop(var, None)

        # Reload config with original env
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']


def test_config_has_sensible_defaults():
    """Test that config has sensible defaults when env vars not set."""
    # Save original environment
    original_env = {
        'BRAIN_HOST': os.environ.get('BRAIN_HOST'),
        'BRAIN_PORT': os.environ.get('BRAIN_PORT'),
        'ENV': os.environ.get('ENV'),
        'BRAIN_DB_PATH': os.environ.get('BRAIN_DB_PATH'),
        'LOG_LEVEL': os.environ.get('LOG_LEVEL'),
        'RATE_LIMIT_REQUESTS': os.environ.get('RATE_LIMIT_REQUESTS'),
        'QUEUE_BATCH_SIZE': os.environ.get('QUEUE_BATCH_SIZE'),
        'QUEUE_POLL_INTERVAL': os.environ.get('QUEUE_POLL_INTERVAL'),
        'WS_HEARTBEAT_INTERVAL': os.environ.get('WS_HEARTBEAT_INTERVAL'),
        'RATE_LIMIT_WINDOW': os.environ.get('RATE_LIMIT_WINDOW'),
        'SENTRY_ENVIRONMENT': os.environ.get('SENTRY_ENVIRONMENT'),
        'CORS_ORIGINS': os.environ.get('CORS_ORIGINS'),
        'SENTRY_DSN': os.environ.get('SENTRY_DSN'),
    }

    try:
        # Clear env vars
        for var in original_env.keys():
            os.environ.pop(var, None)

        # Reimport config
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']

        import emy.brain.config as config_module

        # Verify defaults exist and are sensible
        assert config_module.BRAIN_HOST is not None
        assert config_module.BRAIN_PORT > 0
        assert config_module.ENV in ['development', 'production']
        assert config_module.LOG_LEVEL_STR in ['DEBUG', 'INFO', 'WARNING', 'ERROR']
        assert config_module.QUEUE_BATCH_SIZE > 0
        assert config_module.QUEUE_POLL_INTERVAL > 0
        assert config_module.RATE_LIMIT_REQUESTS > 0
        assert config_module.RATE_LIMIT_WINDOW > 0
        assert config_module.WS_HEARTBEAT_INTERVAL > 0

    finally:
        # Restore original environment
        for var, val in original_env.items():
            if val is not None:
                os.environ[var] = val
            else:
                os.environ.pop(var, None)

        # Reload config with original env
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']


def test_config_deployment_flags():
    """Test that deployment flags are set correctly."""
    # Save original environment
    original_env = os.environ.get('ENV')

    try:
        # Test production flag
        os.environ['ENV'] = 'production'
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']

        import emy.brain.config as config_module

        assert config_module.IS_PRODUCTION is True
        assert config_module.IS_DEVELOPMENT is False
        assert config_module.DEBUG is False

        # Test development flag
        os.environ['ENV'] = 'development'
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']

        import emy.brain.config as config_module

        assert config_module.IS_PRODUCTION is False
        assert config_module.IS_DEVELOPMENT is True
        assert config_module.DEBUG is True

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ['ENV'] = original_env
        else:
            os.environ.pop('ENV', None)

        # Reload config with original env
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']


def test_config_cors_origins_parsing():
    """Test that CORS origins are parsed correctly."""
    original_env = os.environ.get('CORS_ORIGINS')

    try:
        # Test single origin
        os.environ['CORS_ORIGINS'] = 'https://example.com'
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']

        import emy.brain.config as config_module

        assert 'https://example.com' in config_module.CORS_ORIGINS

        # Test multiple origins
        os.environ['CORS_ORIGINS'] = 'https://example.com,https://other.com,http://localhost:3000'
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']

        import emy.brain.config as config_module

        assert len(config_module.CORS_ORIGINS) == 3
        assert 'https://example.com' in config_module.CORS_ORIGINS
        assert 'https://other.com' in config_module.CORS_ORIGINS
        assert 'http://localhost:3000' in config_module.CORS_ORIGINS

    finally:
        # Restore original environment
        if original_env is not None:
            os.environ['CORS_ORIGINS'] = original_env
        else:
            os.environ.pop('CORS_ORIGINS', None)

        # Reload config with original env
        if 'emy.brain.config' in sys.modules:
            del sys.modules['emy.brain.config']
