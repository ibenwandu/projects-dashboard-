"""
Example Usage of Agent Ecosystem

This script demonstrates how to use the agent ecosystem for various tasks.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.main import AgentEcosystem


async def example_research_task():
    """Example of a research task."""
    print("=== Research Task Example ===")
    
    ecosystem = AgentEcosystem()
    
    try:
        await ecosystem.start()
        
        # Execute a research task
        result = await ecosystem.execute_task(
            "Research the latest developments in artificial intelligence",
            task_type="research"
        )
        
        print(f"Research Task Result: {result}")
        
    finally:
        await ecosystem.stop()


async def example_analysis_task():
    """Example of an analysis task."""
    print("=== Analysis Task Example ===")
    
    ecosystem = AgentEcosystem()
    
    try:
        await ecosystem.start()
        
        # Execute an analysis task
        result = await ecosystem.execute_task(
            "Analyze market trends for renewable energy companies",
            task_type="analysis"
        )
        
        print(f"Analysis Task Result: {result}")
        
    finally:
        await ecosystem.stop()


async def example_writing_task():
    """Example of a writing task."""
    print("=== Writing Task Example ===")
    
    ecosystem = AgentEcosystem()
    
    try:
        await ecosystem.start()
        
        # Execute a writing task
        result = await ecosystem.execute_task(
            "Write a comprehensive report on cybersecurity best practices",
            task_type="writing"
        )
        
        print(f"Writing Task Result: {result}")
        
    finally:
        await ecosystem.stop()


async def example_quality_check_task():
    """Example of a quality check task."""
    print("=== Quality Check Task Example ===")
    
    ecosystem = AgentEcosystem()
    
    try:
        await ecosystem.start()
        
        # Execute a quality check task
        result = await ecosystem.execute_task(
            "Validate the quality of a technical document",
            task_type="quality_check"
        )
        
        print(f"Quality Check Task Result: {result}")
        
    finally:
        await ecosystem.stop()


async def example_comprehensive_task():
    """Example of a comprehensive task using all agents."""
    print("=== Comprehensive Task Example ===")
    
    ecosystem = AgentEcosystem()
    
    try:
        await ecosystem.start()
        
        # Execute a comprehensive task
        result = await ecosystem.execute_task(
            "Create a comprehensive market analysis report for electric vehicles",
            task_type="comprehensive"
        )
        
        print(f"Comprehensive Task Result: {result}")
        
        # Get ecosystem status
        status = await ecosystem.get_status()
        print(f"Ecosystem Status: {status}")
        
    finally:
        await ecosystem.stop()


async def example_ecosystem_status():
    """Example of getting ecosystem status."""
    print("=== Ecosystem Status Example ===")
    
    ecosystem = AgentEcosystem()
    
    try:
        await ecosystem.start()
        
        # Get status before task
        status_before = await ecosystem.get_status()
        print(f"Status before task: {status_before}")
        
        # Execute a simple task
        result = await ecosystem.execute_task(
            "Simple test task",
            task_type="research"
        )
        
        # Get status after task
        status_after = await ecosystem.get_status()
        print(f"Status after task: {status_after}")
        
    finally:
        await ecosystem.stop()


async def main():
    """Main function to run all examples."""
    print("Agent Ecosystem Examples")
    print("=" * 50)
    
    # Run individual examples
    await example_research_task()
    print()
    
    await example_analysis_task()
    print()
    
    await example_writing_task()
    print()
    
    await example_quality_check_task()
    print()
    
    await example_comprehensive_task()
    print()
    
    await example_ecosystem_status()
    print()
    
    print("All examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())














