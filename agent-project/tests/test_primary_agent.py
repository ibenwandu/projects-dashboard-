"""
Tests for Primary Agent

This module contains tests for the primary agent functionality.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.agents.primary_agent import PrimaryAgent, WorkflowStep, Workflow
from src.agents.base_agent import Task, Message, TaskPriority


class TestPrimaryAgent:
    """Test cases for PrimaryAgent class."""
    
    @pytest.fixture
    def primary_agent(self):
        """Create a primary agent instance for testing."""
        return PrimaryAgent(name="TestCoordinator", config={})
    
    @pytest.fixture
    def sample_workflow_steps(self):
        """Create sample workflow steps for testing."""
        return [
            WorkflowStep(
                name="Test Step 1",
                agent_type="research",
                description="Test research step",
                timeout=60
            ),
            WorkflowStep(
                name="Test Step 2",
                agent_type="analysis",
                description="Test analysis step",
                timeout=60
            )
        ]
    
    @pytest.mark.asyncio
    async def test_primary_agent_initialization(self, primary_agent):
        """Test primary agent initialization."""
        assert primary_agent.name == "TestCoordinator"
        assert primary_agent.agent_type == "primary"
        assert primary_agent.status.value == "idle"
        assert len(primary_agent.sub_agents) == 0
    
    @pytest.mark.asyncio
    async def test_register_sub_agent(self, primary_agent):
        """Test registering a sub-agent."""
        result = await primary_agent.register_sub_agent("TestAgent", "research")
        
        assert result is True
        assert "TestAgent" in primary_agent.sub_agents
        assert primary_agent.sub_agents["TestAgent"] == "research"
        assert primary_agent.agent_status["TestAgent"].value == "idle"
    
    @pytest.mark.asyncio
    async def test_unregister_sub_agent(self, primary_agent):
        """Test unregistering a sub-agent."""
        # First register an agent
        await primary_agent.register_sub_agent("TestAgent", "research")
        
        # Then unregister it
        result = await primary_agent.unregister_sub_agent("TestAgent")
        
        assert result is True
        assert "TestAgent" not in primary_agent.sub_agents
        assert "TestAgent" not in primary_agent.agent_status
    
    @pytest.mark.asyncio
    async def test_create_workflow(self, primary_agent, sample_workflow_steps):
        """Test creating a workflow."""
        workflow = await primary_agent.create_workflow(
            name="Test Workflow",
            description="Test workflow description",
            steps=sample_workflow_steps
        )
        
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Test workflow description"
        assert len(workflow.steps) == 2
        assert workflow.id in primary_agent.workflows
    
    @pytest.mark.asyncio
    async def test_process_task_execute_workflow(self, primary_agent, sample_workflow_steps):
        """Test processing execute_workflow task."""
        # Create a workflow first
        workflow = await primary_agent.create_workflow(
            name="Test Workflow",
            description="Test workflow description",
            steps=sample_workflow_steps
        )
        
        # Create task to execute workflow
        task = Task(
            name="execute_workflow",
            data={'workflow_id': workflow.id}
        )
        
        # Mock the execute_workflow method
        primary_agent.execute_workflow = AsyncMock(return_value={'result': 'success'})
        
        result = await primary_agent.process_task(task)
        
        assert result == {'result': 'success'}
        primary_agent.execute_workflow.assert_called_once_with(workflow.id)
    
    @pytest.mark.asyncio
    async def test_process_task_get_status(self, primary_agent):
        """Test processing get_status task."""
        task = Task(name="get_status")
        
        result = await primary_agent.process_task(task)
        
        assert 'primary_agent' in result
        assert 'sub_agents' in result
        assert 'workflows' in result
    
    @pytest.mark.asyncio
    async def test_process_task_register_agent(self, primary_agent):
        """Test processing register_agent task."""
        task = Task(
            name="register_agent",
            data={'agent_name': 'TestAgent', 'agent_type': 'research'}
        )
        
        result = await primary_agent.process_task(task)
        
        assert result is True
        assert "TestAgent" in primary_agent.sub_agents
    
    @pytest.mark.asyncio
    async def test_process_task_unknown_type(self, primary_agent):
        """Test processing unknown task type."""
        task = Task(name="unknown_task")
        
        with pytest.raises(ValueError, match="Unknown task type: unknown_task"):
            await primary_agent.process_task(task)
    
    @pytest.mark.asyncio
    async def test_handle_message_status_update(self, primary_agent):
        """Test handling status update message."""
        # Register an agent first
        await primary_agent.register_sub_agent("TestAgent", "research")
        
        message = Message(
            sender="TestAgent",
            message_type="status_update",
            content={'status': 'busy', 'metrics': {'tasks_completed': 5}}
        )
        
        result = await primary_agent.handle_message(message)
        
        assert result == {'status': 'acknowledged'}
        assert primary_agent.agent_status["TestAgent"].value == "busy"
        assert primary_agent.agent_metrics["TestAgent"]["tasks_completed"] == 5
    
    @pytest.mark.asyncio
    async def test_handle_message_task_completed(self, primary_agent):
        """Test handling task completed message."""
        message = Message(
            sender="TestAgent",
            message_type="task_completed",
            content={'task_id': 'task123'}
        )
        
        result = await primary_agent.handle_message(message)
        
        assert result == {'status': 'acknowledged'}
    
    @pytest.mark.asyncio
    async def test_handle_message_task_failed(self, primary_agent):
        """Test handling task failed message."""
        message = Message(
            sender="TestAgent",
            message_type="task_failed",
            content={'task_id': 'task123', 'error': 'Test error'}
        )
        
        result = await primary_agent.handle_message(message)
        
        assert result == {'status': 'acknowledged'}
    
    @pytest.mark.asyncio
    async def test_handle_message_unknown_type(self, primary_agent):
        """Test handling unknown message type."""
        message = Message(
            sender="TestAgent",
            message_type="unknown_message_type",
            content={}
        )
        
        result = await primary_agent.handle_message(message)
        
        assert result == {'status': 'unknown_message_type'}
    
    @pytest.mark.asyncio
    async def test_get_ecosystem_status(self, primary_agent):
        """Test getting ecosystem status."""
        # Register a sub-agent
        await primary_agent.register_sub_agent("TestAgent", "research")
        
        status = primary_agent.get_ecosystem_status()
        
        assert 'primary_agent' in status
        assert 'sub_agents' in status
        assert 'workflows' in status
        assert 'TestAgent' in status['sub_agents']
    
    @pytest.mark.asyncio
    async def test_shutdown(self, primary_agent):
        """Test agent shutdown."""
        # Register a sub-agent
        await primary_agent.register_sub_agent("TestAgent", "research")
        
        await primary_agent.shutdown()
        
        assert primary_agent.status.value == "offline"
        assert len(primary_agent.sub_agents) == 0


class TestWorkflowStep:
    """Test cases for WorkflowStep class."""
    
    def test_workflow_step_creation(self):
        """Test creating a workflow step."""
        step = WorkflowStep(
            name="Test Step",
            agent_type="research",
            description="Test description",
            timeout=120,
            retry_attempts=3,
            required=True
        )
        
        assert step.name == "Test Step"
        assert step.agent_type == "research"
        assert step.description == "Test description"
        assert step.timeout == 120
        assert step.retry_attempts == 3
        assert step.required is True
    
    def test_workflow_step_defaults(self):
        """Test workflow step with default values."""
        step = WorkflowStep(
            name="Test Step",
            agent_type="research",
            description="Test description"
        )
        
        assert step.dependencies is None
        assert step.timeout == 300
        assert step.retry_attempts == 3
        assert step.required is True


class TestWorkflow:
    """Test cases for Workflow class."""
    
    def test_workflow_creation(self, sample_workflow_steps):
        """Test creating a workflow."""
        workflow = Workflow(
            id="test_workflow_1",
            name="Test Workflow",
            description="Test workflow description",
            steps=sample_workflow_steps,
            created_at=None
        )
        
        assert workflow.id == "test_workflow_1"
        assert workflow.name == "Test Workflow"
        assert workflow.description == "Test workflow description"
        assert len(workflow.steps) == 2
        assert workflow.status == "pending"
        assert workflow.current_step == 0
        assert workflow.results is None














