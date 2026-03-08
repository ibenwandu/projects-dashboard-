#!/usr/bin/env python3
"""
Minimal Test Script for Agent Ecosystem

This script tests if the basic installation works by importing core modules.
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def test_imports():
    """Test importing core modules."""
    print("Testing core module imports...")
    
    try:
        # Test basic imports
        import asyncio
        print("✓ asyncio imported successfully")
        
        import aiohttp
        print("✓ aiohttp imported successfully")
        
        import requests
        print("✓ requests imported successfully")
        
        import yaml
        print("✓ pyyaml imported successfully")
        
        import pandas as pd
        print("✓ pandas imported successfully")
        
        import numpy as np
        print("✓ numpy imported successfully")
        
        from bs4 import BeautifulSoup
        print("✓ beautifulsoup4 imported successfully")
        
        from textblob import TextBlob
        print("✓ textblob imported successfully")
        
        from loguru import logger
        print("✓ loguru imported successfully")
        
        print("\n✓ All core dependencies imported successfully!")
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_agent_modules():
    """Test importing agent modules."""
    print("\nTesting agent module imports...")
    
    try:
        # Test agent imports
        from agents.base_agent import BaseAgent, Task, Message
        print("✓ BaseAgent and data classes imported successfully")
        
        from agents.primary_agent import PrimaryAgent
        print("✓ PrimaryAgent imported successfully")
        
        from communication.message_bus import MessageBus
        print("✓ MessageBus imported successfully")
        
        from utils.config import load_config
        print("✓ Config utilities imported successfully")
        
        print("✓ All agent modules imported successfully!")
        return True
        
    except ImportError as e:
        print(f"✗ Agent module import error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality."""
    print("\nTesting basic functionality...")
    
    try:
        # Test creating a simple task
        from agents.base_agent import Task, TaskPriority
        
        task = Task(
            name="test_task",
            description="A test task",
            priority=TaskPriority.NORMAL
        )
        print("✓ Task creation works")
        
        # Test message bus
        from communication.message_bus import MessageBus
        from agents.base_agent import Message
        
        message_bus = MessageBus()
        print("✓ MessageBus creation works")
        
        # Test config loading
        from utils.config import load_config
        config = load_config()
        print("✓ Config loading works")
        
        print("✓ Basic functionality tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Functionality test error: {e}")
        return False

def main():
    """Run all tests."""
    print("Agent Ecosystem Minimal Test")
    print("=" * 40)
    
    # Test core imports
    if not test_imports():
        print("\n❌ Core imports failed!")
        return False
    
    # Test agent modules
    if not test_agent_modules():
        print("\n❌ Agent module imports failed!")
        return False
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality tests failed!")
        return False
    
    print("\n🎉 All tests passed! Installation is working correctly.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)














