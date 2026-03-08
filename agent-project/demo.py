#!/usr/bin/env python3
"""
Agent Ecosystem Demonstration

This script demonstrates the agent ecosystem in action with a simple workflow.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from agents.primary_agent import PrimaryAgent, WorkflowStep
from agents.research_agent import ResearchAgent
from agents.analysis_agent import AnalysisAgent
from agents.writing_agent import WritingAgent
from agents.quality_control_agent import QualityControlAgent
from communication.message_bus import MessageBus
from utils.config import load_config

async def demo_simple_workflow():
    """Demonstrate a simple workflow with the agent ecosystem."""
    print("🤖 Agent Ecosystem Demonstration")
    print("=" * 50)
    
    # Initialize the message bus
    message_bus = MessageBus()
    print("✓ Message bus initialized")
    
    # Create agents
    primary_agent = PrimaryAgent(name="Coordinator")
    research_agent = ResearchAgent(name="Researcher")
    analysis_agent = AnalysisAgent(name="Analyst")
    writing_agent = WritingAgent(name="Writer")
    qc_agent = QualityControlAgent(name="QualityControl")
    
    print("✓ All agents created")
    
    # Register sub-agents with the primary agent
    await primary_agent.register_sub_agent("Researcher", "research")
    await primary_agent.register_sub_agent("Analyst", "analysis")
    await primary_agent.register_sub_agent("Writer", "writing")
    await primary_agent.register_sub_agent("QualityControl", "quality_control")
    
    print("✓ Sub-agents registered")
    
    # Create a simple workflow
    workflow_steps = [
        WorkflowStep(
            name="Research AI Trends",
            agent_type="research",
            description="Research current trends in artificial intelligence"
        ),
        WorkflowStep(
            name="Analyze Data",
            agent_type="analysis",
            description="Analyze the research data and identify key insights"
        ),
        WorkflowStep(
            name="Generate Report",
            agent_type="writing",
            description="Generate a comprehensive report based on the analysis"
        ),
        WorkflowStep(
            name="Quality Check",
            agent_type="quality_control",
            description="Validate the final report for quality and completeness"
        )
    ]
    
    # Create and execute the workflow
    workflow = await primary_agent.create_workflow(
        name="AI Trends Analysis",
        description="Analyze current AI trends and generate a report",
        steps=workflow_steps
    )
    
    print(f"✓ Workflow created: {workflow.name}")
    print(f"  Steps: {len(workflow.steps)}")
    
    # Simulate workflow execution (in a real scenario, this would be async)
    print("\n🔄 Simulating workflow execution...")
    
    for i, step in enumerate(workflow.steps, 1):
        print(f"  Step {i}: {step.name} ({step.agent_type})")
        await asyncio.sleep(0.5)  # Simulate processing time
    
    print("✓ Workflow simulation completed")
    
    # Show agent status
    print("\n📊 Agent Status:")
    for agent_name, agent_type in primary_agent.sub_agents.items():
        status = primary_agent.agent_status.get(agent_name, "Unknown")
        print(f"  {agent_name} ({agent_type}): {status}")
    
    print("\n🎉 Demonstration completed successfully!")
    return True

async def demo_individual_agents():
    """Demonstrate individual agent capabilities."""
    print("\n🔧 Individual Agent Capabilities Demo")
    print("=" * 50)
    
    # Research Agent Demo
    print("\n📚 Research Agent Demo:")
    research_agent = ResearchAgent(name="DemoResearcher")
    
    # Create a research task
    from agents.base_agent import Task, TaskPriority
    
    research_task = Task(
        name="web_scrape",
        description="Scrape information about Python programming",
        priority=TaskPriority.HIGH,
        data={"url": "https://python.org", "max_pages": 1}
    )
    
    print(f"  Task: {research_task.name}")
    print(f"  Description: {research_task.description}")
    
    # Analysis Agent Demo
    print("\n📊 Analysis Agent Demo:")
    analysis_agent = AnalysisAgent(name="DemoAnalyst")
    
    analysis_task = Task(
        name="statistical_analysis",
        description="Analyze sample data for patterns",
        priority=TaskPriority.NORMAL,
        data={"data_type": "numerical", "sample_size": 100}
    )
    
    print(f"  Task: {analysis_task.name}")
    print(f"  Description: {analysis_task.description}")
    
    # Writing Agent Demo
    print("\n✍️ Writing Agent Demo:")
    writing_agent = WritingAgent(name="DemoWriter")
    
    writing_task = Task(
        name="generate_content",
        description="Generate a technical report",
        priority=TaskPriority.NORMAL,
        data={"content_type": "report", "format": "markdown"}
    )
    
    print(f"  Task: {writing_task.name}")
    print(f"  Description: {writing_task.description}")
    
    # Quality Control Agent Demo
    print("\n✅ Quality Control Agent Demo:")
    qc_agent = QualityControlAgent(name="DemoQC")
    
    qc_task = Task(
        name="validate_output",
        description="Validate a sample document",
        priority=TaskPriority.HIGH,
        data={"validation_type": "completeness", "threshold": 0.8}
    )
    
    print(f"  Task: {qc_task.name}")
    print(f"  Description: {qc_task.description}")
    
    print("\n✓ Individual agent demonstrations completed!")

async def main():
    """Main demonstration function."""
    try:
        # Load configuration
        config = load_config()
        print("✓ Configuration loaded")
        
        # Run demonstrations
        await demo_simple_workflow()
        await demo_individual_agents()
        
        print("\n🎯 Agent Ecosystem is ready for use!")
        print("\nNext steps:")
        print("1. Configure your API keys in the .env file")
        print("2. Run 'python example.py' for more examples")
        print("3. Run 'python -m src.main' for the main application")
        
    except Exception as e:
        print(f"❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
