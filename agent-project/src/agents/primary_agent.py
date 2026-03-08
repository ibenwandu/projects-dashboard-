"""
Primary Agent (Coordinator)

This module implements the primary agent that coordinates all sub-agents
and manages the overall workflow of the multi-agent system.
"""

import asyncio
from typing import Any, Dict, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass

from loguru import logger

from agents.base_agent import BaseAgent, Task, Message, TaskPriority, AgentStatus
from communication.message_bus import MessageBus


@dataclass
class WorkflowStep:
    """Represents a step in a workflow."""
    name: str
    agent_type: str
    description: str
    dependencies: List[str] = None
    timeout: int = 300
    retry_attempts: int = 3
    required: bool = True


@dataclass
class Workflow:
    """Represents a complete workflow."""
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    created_at: datetime
    status: str = "pending"
    current_step: int = 0
    results: Dict[str, Any] = None


class PrimaryAgent(BaseAgent):
    """
    Primary Agent that coordinates all sub-agents and manages workflows.
    
    This agent is responsible for:
    - Task delegation and workflow management
    - Agent communication hub
    - Progress tracking and status monitoring
    - Error handling and recovery
    """
    
    def __init__(self, name: str = "Coordinator", config: Dict[str, Any] = None):
        """
        Initialize the primary agent.
        
        Args:
            name: Agent name
            config: Configuration dictionary
        """
        super().__init__(name, "primary", config)
        
        # Sub-agent registry
        self.sub_agents: Dict[str, str] = {}  # agent_name -> agent_type
        self.agent_status: Dict[str, AgentStatus] = {}
        self.agent_metrics: Dict[str, Dict[str, Any]] = {}
        
        # Workflow management
        self.workflows: Dict[str, Workflow] = {}
        self.active_workflows: Set[str] = set()
        
        # Message bus for communication
        self.message_bus: Optional[MessageBus] = None
        
        # Performance tracking
        self.workflow_metrics = {
            'workflows_started': 0,
            'workflows_completed': 0,
            'workflows_failed': 0,
            'average_completion_time': 0.0
        }
        
        self.logger.info("Primary agent initialized")
    
    async def register_sub_agent(self, agent_name: str, agent_type: str) -> bool:
        """
        Register a sub-agent with the primary agent.
        
        Args:
            agent_name: Name of the sub-agent
            agent_type: Type of the sub-agent
            
        Returns:
            True if registration successful
        """
        try:
            self.sub_agents[agent_name] = agent_type
            self.agent_status[agent_name] = AgentStatus.IDLE
            self.agent_metrics[agent_name] = {
                'tasks_completed': 0,
                'tasks_failed': 0,
                'last_activity': datetime.now()
            }
            
            self.logger.info(f"Sub-agent registered: {agent_name} ({agent_type})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register sub-agent {agent_name}: {str(e)}")
            return False
    
    async def unregister_sub_agent(self, agent_name: str) -> bool:
        """
        Unregister a sub-agent.
        
        Args:
            agent_name: Name of the sub-agent
            
        Returns:
            True if unregistration successful
        """
        try:
            if agent_name in self.sub_agents:
                del self.sub_agents[agent_name]
                del self.agent_status[agent_name]
                del self.agent_metrics[agent_name]
                
                self.logger.info(f"Sub-agent unregistered: {agent_name}")
                return True
            else:
                self.logger.warning(f"Sub-agent not found: {agent_name}")
                return False
                
        except Exception as e:
            self.logger.error(f"Failed to unregister sub-agent {agent_name}: {str(e)}")
            return False
    
    async def create_workflow(self, name: str, description: str, 
                            steps: List[WorkflowStep]) -> Workflow:
        """
        Create a new workflow.
        
        Args:
            name: Workflow name
            description: Workflow description
            steps: List of workflow steps
            
        Returns:
            Created workflow
        """
        workflow_id = f"workflow_{len(self.workflows) + 1}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            steps=steps,
            created_at=datetime.now(),
            results={}
        )
        
        self.workflows[workflow_id] = workflow
        self.logger.info(f"Workflow created: {name} (ID: {workflow_id})")
        
        return workflow
    
    async def execute_workflow(self, workflow_id: str) -> Dict[str, Any]:
        """
        Execute a workflow by coordinating sub-agents.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            Workflow results
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow not found: {workflow_id}")
        
        workflow = self.workflows[workflow_id]
        workflow.status = "running"
        self.active_workflows.add(workflow_id)
        self.workflow_metrics['workflows_started'] += 1
        
        start_time = datetime.now()
        self.logger.info(f"Starting workflow: {workflow.name} (ID: {workflow_id})")
        
        try:
            # Execute each step in the workflow
            for i, step in enumerate(workflow.steps):
                workflow.current_step = i
                self.logger.info(f"Executing step {i+1}/{len(workflow.steps)}: {step.name}")
                
                # Check if required agents are available
                if not await self._check_agent_availability(step.agent_type):
                    raise RuntimeError(f"Required agent type not available: {step.agent_type}")
                
                # Execute the step
                step_result = await self._execute_workflow_step(workflow, step)
                workflow.results[step.name] = step_result
                
                # Check for step failure
                if step.required and step_result.get('status') == 'failed':
                    raise RuntimeError(f"Required step failed: {step.name}")
            
            # Workflow completed successfully
            workflow.status = "completed"
            completion_time = (datetime.now() - start_time).total_seconds()
            self.workflow_metrics['workflows_completed'] += 1
            
            # Update average completion time
            total_completed = self.workflow_metrics['workflows_completed']
            current_avg = self.workflow_metrics['average_completion_time']
            self.workflow_metrics['average_completion_time'] = (
                (current_avg * (total_completed - 1) + completion_time) / total_completed
            )
            
            self.logger.info(f"Workflow completed: {workflow.name} in {completion_time:.2f}s")
            
        except Exception as e:
            workflow.status = "failed"
            self.workflow_metrics['workflows_failed'] += 1
            self.logger.error(f"Workflow failed: {workflow.name} - {str(e)}")
            raise
        
        finally:
            self.active_workflows.discard(workflow_id)
        
        return workflow.results
    
    async def _execute_workflow_step(self, workflow: Workflow, step: WorkflowStep) -> Dict[str, Any]:
        """
        Execute a single workflow step.
        
        Args:
            workflow: Current workflow
            step: Step to execute
            
        Returns:
            Step result
        """
        # Find available agent for this step
        agent_name = await self._find_available_agent(step.agent_type)
        if not agent_name:
            return {'status': 'failed', 'error': f'No available agent for type: {step.agent_type}'}
        
        # Create task for the agent
        task = Task(
            name=step.name,
            description=step.description,
            priority=TaskPriority.HIGH if step.required else TaskPriority.NORMAL,
            data={
                'workflow_id': workflow.id,
                'step_name': step.name,
                'step_data': step.__dict__,
                'previous_results': workflow.results
            }
        )
        
        # Send task to agent
        message = await self.send_message(
            recipient=agent_name,
            message_type="task_request",
            content=task,
            priority=task.priority
        )
        
        # Wait for response with timeout
        try:
            response = await asyncio.wait_for(
                self._wait_for_agent_response(agent_name, task.id),
                timeout=step.timeout
            )
            
            return {
                'status': 'completed',
                'agent': agent_name,
                'result': response.get('result'),
                'execution_time': response.get('execution_time', 0)
            }
            
        except asyncio.TimeoutError:
            return {
                'status': 'failed',
                'error': f'Step timed out after {step.timeout}s',
                'agent': agent_name
            }
        except Exception as e:
            return {
                'status': 'failed',
                'error': str(e),
                'agent': agent_name
            }
    
    async def _find_available_agent(self, agent_type: str) -> Optional[str]:
        """
        Find an available agent of the specified type.
        
        Args:
            agent_type: Type of agent to find
            
        Returns:
            Agent name if found, None otherwise
        """
        for agent_name, type_name in self.sub_agents.items():
            if type_name == agent_type and self.agent_status[agent_name] == AgentStatus.IDLE:
                return agent_name
        return None
    
    async def _check_agent_availability(self, agent_type: str) -> bool:
        """
        Check if any agent of the specified type is available.
        
        Args:
            agent_type: Type of agent to check
            
        Returns:
            True if available, False otherwise
        """
        return await self._find_available_agent(agent_type) is not None
    
    async def _wait_for_agent_response(self, agent_name: str, task_id: str) -> Dict[str, Any]:
        """
        Wait for a response from a specific agent.
        
        Args:
            agent_name: Name of the agent
            task_id: ID of the task
            
        Returns:
            Agent response
        """
        # This is a simplified implementation
        # In a real system, you would implement proper message waiting
        await asyncio.sleep(1)  # Simulate waiting
        
        return {
            'result': f"Mock result from {agent_name} for task {task_id}",
            'execution_time': 1.5
        }
    
    async def process_task(self, task: Task) -> Any:
        """
        Process a task - handles workflow execution requests.
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        if task.name == "execute_workflow":
            workflow_id = task.data.get('workflow_id')
            return await self.execute_workflow(workflow_id)
        elif task.name == "get_status":
            return self.get_ecosystem_status()
        elif task.name == "register_agent":
            agent_name = task.data.get('agent_name')
            agent_type = task.data.get('agent_type')
            return await self.register_sub_agent(agent_name, agent_type)
        else:
            raise ValueError(f"Unknown task type: {task.name}")
    
    async def handle_message(self, message: Message) -> Any:
        """
        Handle incoming messages from sub-agents.
        
        Args:
            message: Message to handle
            
        Returns:
            Response to message
        """
        if message.message_type == "status_update":
            # Update agent status
            agent_name = message.sender
            if agent_name in self.agent_status:
                self.agent_status[agent_name] = AgentStatus(message.content.get('status'))
                self.agent_metrics[agent_name]['last_activity'] = datetime.now()
                
                # Update metrics
                if 'metrics' in message.content:
                    self.agent_metrics[agent_name].update(message.content['metrics'])
                
                self.logger.debug(f"Status update from {agent_name}: {message.content.get('status')}")
            
            return {'status': 'acknowledged'}
        
        elif message.message_type == "task_completed":
            # Handle task completion notification
            task_id = message.content.get('task_id')
            agent_name = message.sender
            
            self.logger.info(f"Task completed by {agent_name}: {task_id}")
            return {'status': 'acknowledged'}
        
        elif message.message_type == "task_failed":
            # Handle task failure notification
            task_id = message.content.get('task_id')
            error = message.content.get('error')
            agent_name = message.sender
            
            self.logger.error(f"Task failed by {agent_name}: {task_id} - {error}")
            return {'status': 'acknowledged'}
        
        else:
            self.logger.warning(f"Unknown message type: {message.message_type}")
            return {'status': 'unknown_message_type'}
    
    def get_ecosystem_status(self) -> Dict[str, Any]:
        """
        Get the status of the entire agent ecosystem.
        
        Returns:
            Ecosystem status dictionary
        """
        return {
            'primary_agent': self.get_status(),
            'sub_agents': {
                name: {
                    'type': agent_type,
                    'status': self.agent_status.get(name, 'unknown').value,
                    'metrics': self.agent_metrics.get(name, {})
                }
                for name, agent_type in self.sub_agents.items()
            },
            'workflows': {
                'total': len(self.workflows),
                'active': len(self.active_workflows),
                'metrics': self.workflow_metrics
            },
            'message_bus': self.message_bus.get_metrics() if self.message_bus else None
        }
    
    async def set_message_bus(self, message_bus: MessageBus) -> None:
        """
        Set the message bus for communication.
        
        Args:
            message_bus: Message bus instance
        """
        self.message_bus = message_bus
        self.logger.info("Message bus connected")
    
    async def shutdown(self) -> None:
        """Shutdown the primary agent gracefully."""
        self.logger.info("Primary agent shutting down")
        
        # Wait for active workflows to complete
        if self.active_workflows:
            self.logger.info(f"Waiting for {len(self.active_workflows)} active workflows to complete")
            await asyncio.sleep(2)
        
        # Shutdown sub-agents
        for agent_name in list(self.sub_agents.keys()):
            await self.unregister_sub_agent(agent_name)
        
        await super().shutdown()
