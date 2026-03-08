"""
Base Agent Class

This module provides the foundational class for all agents in the ecosystem.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from loguru import logger


class AgentStatus(Enum):
    """Agent status enumeration."""
    IDLE = "idle"
    BUSY = "busy"
    ERROR = "error"
    OFFLINE = "offline"


class TaskPriority(Enum):
    """Task priority enumeration."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Task:
    """Task data class for representing agent tasks."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    status: str = "pending"
    data: Dict[str, Any] = field(default_factory=dict)
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class Message:
    """Message data class for inter-agent communication."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""
    message_type: str = ""
    content: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    priority: TaskPriority = TaskPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """
    Base class for all agents in the ecosystem.
    
    This class provides common functionality including:
    - Task management
    - Message handling
    - Status tracking
    - Error handling
    - Logging
    """
    
    def __init__(self, name: str, agent_type: str, config: Dict[str, Any] = None):
        """
        Initialize the base agent.
        
        Args:
            name: Agent name
            agent_type: Type of agent
            config: Configuration dictionary
        """
        self.name = name
        self.agent_type = agent_type
        self.config = config or {}
        self.status = AgentStatus.IDLE
        self.tasks: List[Task] = []
        self.message_queue: List[Message] = []
        self.error_count = 0
        self.max_errors = self.config.get('max_errors', 5)
        self.logger = logger.bind(agent=name, agent_type=agent_type)
        
        # Performance metrics
        self.metrics = {
            'tasks_completed': 0,
            'tasks_failed': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'uptime_start': datetime.now(),
            'total_processing_time': 0.0
        }
        
        self.logger.info(f"Agent {name} ({agent_type}) initialized")
    
    @abstractmethod
    async def process_task(self, task: Task) -> Any:
        """
        Process a task - to be implemented by subclasses.
        
        Args:
            task: Task to process
            
        Returns:
            Task result
        """
        pass
    
    @abstractmethod
    async def handle_message(self, message: Message) -> Any:
        """
        Handle incoming message - to be implemented by subclasses.
        
        Args:
            message: Message to handle
            
        Returns:
            Response to message
        """
        pass
    
    async def execute_task(self, task: Task) -> Task:
        """
        Execute a task with proper error handling and logging.
        
        Args:
            task: Task to execute
            
        Returns:
            Updated task with result
        """
        try:
            self.status = AgentStatus.BUSY
            task.started_at = datetime.now()
            task.status = "running"
            
            self.logger.info(f"Starting task: {task.name} (ID: {task.id})")
            
            # Process the task
            result = await self.process_task(task)
            
            # Update task with result
            task.result = result
            task.completed_at = datetime.now()
            task.status = "completed"
            
            # Update metrics
            processing_time = (task.completed_at - task.started_at).total_seconds()
            self.metrics['tasks_completed'] += 1
            self.metrics['total_processing_time'] += processing_time
            
            self.logger.info(f"Task completed: {task.name} in {processing_time:.2f}s")
            
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now()
            
            self.metrics['tasks_failed'] += 1
            self.error_count += 1
            
            self.logger.error(f"Task failed: {task.name} - {str(e)}")
            
            if self.error_count >= self.max_errors:
                self.status = AgentStatus.ERROR
                self.logger.error(f"Agent {self.name} reached max error count")
        
        finally:
            if self.status != AgentStatus.ERROR:
                self.status = AgentStatus.IDLE
        
        return task
    
    async def send_message(self, recipient: str, message_type: str, 
                          content: Any, priority: TaskPriority = TaskPriority.NORMAL) -> Message:
        """
        Send a message to another agent.
        
        Args:
            recipient: Recipient agent name
            message_type: Type of message
            content: Message content
            priority: Message priority
            
        Returns:
            Sent message
        """
        message = Message(
            sender=self.name,
            recipient=recipient,
            message_type=message_type,
            content=content,
            priority=priority
        )
        
        self.message_queue.append(message)
        self.metrics['messages_sent'] += 1
        
        self.logger.debug(f"Message sent to {recipient}: {message_type}")
        return message
    
    async def receive_message(self, message: Message) -> Any:
        """
        Receive and handle a message.
        
        Args:
            message: Received message
            
        Returns:
            Response to message
        """
        self.metrics['messages_received'] += 1
        self.logger.debug(f"Message received from {message.sender}: {message.message_type}")
        
        return await self.handle_message(message)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status and metrics.
        
        Returns:
            Status dictionary
        """
        uptime = datetime.now() - self.metrics['uptime_start']
        
        return {
            'name': self.name,
            'type': self.agent_type,
            'status': self.status.value,
            'error_count': self.error_count,
            'uptime_seconds': uptime.total_seconds(),
            'metrics': self.metrics.copy(),
            'current_tasks': len([t for t in self.tasks if t.status == "running"]),
            'pending_tasks': len([t for t in self.tasks if t.status == "pending"]),
            'message_queue_size': len(self.message_queue)
        }
    
    def add_task(self, task: Task) -> None:
        """
        Add a task to the agent's task queue.
        
        Args:
            task: Task to add
        """
        self.tasks.append(task)
        self.logger.info(f"Task added: {task.name} (Priority: {task.priority.name})")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """
        Get a task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            Task if found, None otherwise
        """
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def clear_completed_tasks(self) -> None:
        """Clear completed tasks from memory."""
        self.tasks = [t for t in self.tasks if t.status not in ["completed", "failed"]]
        self.logger.debug("Cleared completed tasks")
    
    async def shutdown(self) -> None:
        """Shutdown the agent gracefully."""
        self.status = AgentStatus.OFFLINE
        self.logger.info(f"Agent {self.name} shutting down")
        
        # Wait for running tasks to complete
        running_tasks = [t for t in self.tasks if t.status == "running"]
        if running_tasks:
            self.logger.info(f"Waiting for {len(running_tasks)} running tasks to complete")
            # In a real implementation, you might want to implement task cancellation
            await asyncio.sleep(1)
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', status={self.status.value})"














