#!/usr/bin/env python3
"""
Simple Test Script for Agent Ecosystem

This script tests the basic functionality using absolute imports.
"""

import sys
import os
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent
src_dir = current_dir / "src"
sys.path.insert(0, str(src_dir))

def test_basic_imports():
    """Test basic module imports."""
    print("Testing basic imports...")
    
    try:
        # Test core dependencies
        import asyncio
        import aiohttp
        import requests
        import yaml
        import pandas as pd
        import numpy as np
        from bs4 import BeautifulSoup
        from textblob import TextBlob
        from loguru import logger
        
        print("✓ All core dependencies imported successfully!")
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False

def test_agent_imports():
    """Test agent module imports."""
    print("\nTesting agent imports...")
    
    try:
        # Test base agent
        from agents.base_agent import BaseAgent, Task, Message, TaskPriority, AgentStatus
        print("✓ BaseAgent imported successfully")
        
        # Test primary agent
        from agents.primary_agent import PrimaryAgent, WorkflowStep, Workflow
        print("✓ PrimaryAgent imported successfully")
        
        # Test communication
        from communication.message_bus import MessageBus
        print("✓ MessageBus imported successfully")
        
        # Test utilities
        from utils.config import load_config
        print("✓ Config utilities imported successfully")
        
        print("✓ All agent modules imported successfully!")
        return True
    except ImportError as e:
        print(f"✗ Agent import error: {e}")
        return False

def test_basic_functionality():
    """Test basic functionality."""
    print("\nTesting basic functionality...")
    
    try:
        # Test creating a task
        from agents.base_agent import Task, TaskPriority
        
        task = Task(
            name="test_task",
            description="A test task",
            priority=TaskPriority.NORMAL
        )
        print("✓ Task creation works")
        
        # Test creating a workflow step
        from agents.primary_agent import WorkflowStep
        
        step = WorkflowStep(
            name="test_step",
            agent_type="research",
            description="A test step"
        )
        print("✓ WorkflowStep creation works")
        
        # Test message bus
        from communication.message_bus import MessageBus
        
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
        import traceback
        traceback.print_exc()
        return False

def test_agent_creation():
    """Test creating agents."""
    print("\nTesting agent creation...")
    
    try:
        # Test creating primary agent
        from agents.primary_agent import PrimaryAgent
        
        primary_agent = PrimaryAgent(name="TestCoordinator")
        print("✓ PrimaryAgent creation works")
        
        # Test creating research agent
        from agents.research_agent import ResearchAgent
        
        research_agent = ResearchAgent(name="TestResearch")
        print("✓ ResearchAgent creation works")
        
        # Test creating analysis agent
        from agents.analysis_agent import AnalysisAgent
        
        analysis_agent = AnalysisAgent(name="TestAnalysis")
        print("✓ AnalysisAgent creation works")
        
        # Test creating writing agent
        from agents.writing_agent import WritingAgent
        
        writing_agent = WritingAgent(name="TestWriting")
        print("✓ WritingAgent creation works")
        
        # Test creating quality control agent
        from agents.quality_control_agent import QualityControlAgent
        
        qc_agent = QualityControlAgent(name="TestQC")
        print("✓ QualityControlAgent creation works")
        
        print("✓ All agent creation tests passed!")
        return True
    except Exception as e:
        print(f"✗ Agent creation test error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Agent Ecosystem Simple Test")
    print("=" * 40)
    
    # Test basic imports
    if not test_basic_imports():
        print("\n❌ Basic imports failed!")
        return False
    
    # Test agent imports
    if not test_agent_imports():
        print("\n❌ Agent imports failed!")
        return False
    
    # Test basic functionality
    if not test_basic_functionality():
        print("\n❌ Basic functionality failed!")
        return False
    
    # Test agent creation
    if not test_agent_creation():
        print("\n❌ Agent creation failed!")
        return False
    
    print("\n🎉 All tests passed! The agent ecosystem is working correctly.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)














