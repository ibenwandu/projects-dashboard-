"""
Agent Ecosystem Main Entry Point

This module provides the main entry point for the agent ecosystem,
allowing users to initialize and run the multi-agent system.
"""

import asyncio
import sys
from typing import Dict, Any, List, Optional
from pathlib import Path

from loguru import logger

from .utils.config import load_config, get_agent_config
from .utils.logger import setup_logging
from .utils.helpers import create_task, create_message
from .communication.message_bus import MessageBus
from .agents import (
    PrimaryAgent, ResearchAgent, AnalysisAgent, 
    WritingAgent, QualityControlAgent
)


class AgentEcosystem:
    """
    Main class for managing the agent ecosystem.
    
    This class coordinates all agents and provides a high-level interface
    for executing workflows and managing the multi-agent system.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the agent ecosystem.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = load_config(config_path)
        
        # Setup logging
        setup_logging(self.config.get('logging', {}))
        
        # Initialize components
        self.message_bus = None
        self.primary_agent = None
        self.sub_agents = {}
        self.is_running = False
        
        self.logger = logger.bind(component="AgentEcosystem")
        self.logger.info("Agent ecosystem initialized")
    
    async def start(self) -> None:
        """
        Start the agent ecosystem.
        """
        try:
            self.logger.info("Starting agent ecosystem...")
            
            # Initialize message bus
            self.message_bus = MessageBus(self.config.get('communication', {}))
            
            # Initialize primary agent
            primary_config = self.config.get('primary_agent', {})
            self.primary_agent = PrimaryAgent(
                name=primary_config.get('name', 'Coordinator'),
                config=primary_config
            )
            
            # Connect primary agent to message bus
            await self.primary_agent.set_message_bus(self.message_bus)
            
            # Initialize sub-agents
            await self._initialize_sub_agents()
            
            # Register sub-agents with primary agent
            await self._register_sub_agents()
            
            self.is_running = True
            self.logger.info("Agent ecosystem started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start agent ecosystem: {str(e)}")
            raise
    
    async def _initialize_sub_agents(self) -> None:
        """
        Initialize all sub-agents.
        """
        sub_agents_config = self.config.get('sub_agents', {})
        
        # Initialize Research Agent
        if sub_agents_config.get('research', {}).get('enabled', True):
            research_config = get_agent_config('research')
            self.sub_agents['research'] = ResearchAgent(
                name=research_config.get('name', 'Research Agent'),
                config=research_config
            )
        
        # Initialize Analysis Agent
        if sub_agents_config.get('analysis', {}).get('enabled', True):
            analysis_config = get_agent_config('analysis')
            self.sub_agents['analysis'] = AnalysisAgent(
                name=analysis_config.get('name', 'Analysis Agent'),
                config=analysis_config
            )
        
        # Initialize Writing Agent
        if sub_agents_config.get('writing', {}).get('enabled', True):
            writing_config = get_agent_config('writing')
            self.sub_agents['writing'] = WritingAgent(
                name=writing_config.get('name', 'Writing Agent'),
                config=writing_config
            )
        
        # Initialize Quality Control Agent
        if sub_agents_config.get('quality_control', {}).get('enabled', True):
            qc_config = get_agent_config('quality_control')
            self.sub_agents['quality_control'] = QualityControlAgent(
                name=qc_config.get('name', 'Quality Control Agent'),
                config=qc_config
            )
        
        self.logger.info(f"Initialized {len(self.sub_agents)} sub-agents")
    
    async def _register_sub_agents(self) -> None:
        """
        Register sub-agents with the primary agent.
        """
        for agent_type, agent in self.sub_agents.items():
            await self.primary_agent.register_sub_agent(agent.name, agent_type)
            self.logger.info(f"Registered {agent.name} ({agent_type}) with primary agent")
    
    async def execute_task(self, task_description: str, task_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Execute a task using the agent ecosystem.
        
        Args:
            task_description: Description of the task to execute
            task_type: Type of task (research, analysis, writing, quality_check, comprehensive)
            
        Returns:
            Task execution results
        """
        if not self.is_running:
            raise RuntimeError("Agent ecosystem is not running. Call start() first.")
        
        try:
            self.logger.info(f"Executing task: {task_description}")
            
            # Create workflow based on task type
            workflow = await self._create_workflow_for_task(task_description, task_type)
            
            # Execute workflow
            results = await self.primary_agent.execute_workflow(workflow.id)
            
            self.logger.info(f"Task completed successfully")
            return {
                'status': 'completed',
                'task_description': task_description,
                'task_type': task_type,
                'workflow_id': workflow.id,
                'results': results
            }
            
        except Exception as e:
            self.logger.error(f"Task execution failed: {str(e)}")
            return {
                'status': 'failed',
                'task_description': task_description,
                'task_type': task_type,
                'error': str(e)
            }
    
    async def _create_workflow_for_task(self, task_description: str, task_type: str):
        """
        Create a workflow for the given task.
        
        Args:
            task_description: Task description
            task_type: Type of task
            
        Returns:
            Created workflow
        """
        from .agents.primary_agent import WorkflowStep
        
        steps = []
        
        if task_type == "research":
            # Research-only workflow
            steps.append(WorkflowStep(
                name="Research Task",
                agent_type="research",
                description=f"Research: {task_description}",
                timeout=300
            ))
        
        elif task_type == "analysis":
            # Analysis-only workflow
            steps.append(WorkflowStep(
                name="Analysis Task",
                agent_type="analysis",
                description=f"Analyze: {task_description}",
                timeout=300
            ))
        
        elif task_type == "writing":
            # Writing-only workflow
            steps.append(WorkflowStep(
                name="Writing Task",
                agent_type="writing",
                description=f"Write: {task_description}",
                timeout=300
            ))
        
        elif task_type == "quality_check":
            # Quality check workflow
            steps.append(WorkflowStep(
                name="Quality Check Task",
                agent_type="quality_control",
                description=f"Quality check: {task_description}",
                timeout=300
            ))
        
        else:  # comprehensive
            # Full workflow with all agents
            steps.extend([
                WorkflowStep(
                    name="Research Phase",
                    agent_type="research",
                    description=f"Research: {task_description}",
                    timeout=300
                ),
                WorkflowStep(
                    name="Analysis Phase",
                    agent_type="analysis",
                    description=f"Analyze research results",
                    timeout=300
                ),
                WorkflowStep(
                    name="Writing Phase",
                    agent_type="writing",
                    description=f"Create content based on analysis",
                    timeout=300
                ),
                WorkflowStep(
                    name="Quality Control Phase",
                    agent_type="quality_control",
                    description=f"Validate and improve content",
                    timeout=300
                )
            ])
        
        # Create workflow
        workflow = await self.primary_agent.create_workflow(
            name=f"Task: {task_description[:50]}...",
            description=task_description,
            steps=steps
        )
        
        return workflow
    
    async def get_status(self) -> Dict[str, Any]:
        """
        Get the status of the agent ecosystem.
        
        Returns:
            Ecosystem status
        """
        if not self.is_running:
            return {
                'status': 'not_running',
                'message': 'Agent ecosystem is not running'
            }
        
        try:
            # Get primary agent status
            primary_status = self.primary_agent.get_ecosystem_status()
            
            # Get sub-agent statuses
            sub_agent_statuses = {}
            for agent_type, agent in self.sub_agents.items():
                sub_agent_statuses[agent_type] = agent.get_status()
            
            return {
                'status': 'running',
                'primary_agent': primary_status,
                'sub_agents': sub_agent_statuses,
                'message_bus': self.message_bus.get_metrics() if self.message_bus else None
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }
    
    async def stop(self) -> None:
        """
        Stop the agent ecosystem.
        """
        if not self.is_running:
            return
        
        try:
            self.logger.info("Stopping agent ecosystem...")
            
            # Shutdown sub-agents
            for agent_type, agent in self.sub_agents.items():
                await agent.shutdown()
                self.logger.info(f"Shutdown {agent.name}")
            
            # Shutdown primary agent
            if self.primary_agent:
                await self.primary_agent.shutdown()
                self.logger.info("Shutdown primary agent")
            
            # Shutdown message bus
            if self.message_bus:
                await self.message_bus.shutdown()
                self.logger.info("Shutdown message bus")
            
            self.is_running = False
            self.logger.info("Agent ecosystem stopped")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {str(e)}")
            raise


async def main():
    """
    Main function for running the agent ecosystem.
    """
    # Example usage
    ecosystem = AgentEcosystem()
    
    try:
        # Start the ecosystem
        await ecosystem.start()
        
        # Example task execution
        result = await ecosystem.execute_task(
            "Analyze market trends for AI companies",
            task_type="comprehensive"
        )
        
        print("Task Result:", result)
        
        # Get ecosystem status
        status = await ecosystem.get_status()
        print("Ecosystem Status:", status)
        
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        sys.exit(1)
    
    finally:
        # Stop the ecosystem
        await ecosystem.stop()


if __name__ == "__main__":
    # Run the main function
    asyncio.run(main())














