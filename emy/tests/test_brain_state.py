"""Tests for WorkflowState and LangGraph scaffold.

Test Coverage:
1. WorkflowState default values
2. WorkflowState serialization roundtrip (to_dict/from_dict)
3. Status transitions
4. Engine instantiation
5. Graph compilation
6. execute_workflow returns dict
"""

import pytest
import asyncio
from emy.brain.state import WorkflowState
from emy.brain.engine import EMyBrain


class TestWorkflowState:
    """Tests for WorkflowState dataclass."""

    def test_default_values(self):
        """Test WorkflowState initializes with correct defaults."""
        state = WorkflowState(user_request={"query": "test"})

        assert state.user_request == {"query": "test"}
        assert state.workflow_type == ""
        assert state.current_agent == ""
        assert state.step_count == 0
        assert state.context == {}
        assert state.execution_history == []
        assert state.final_result == {}
        assert state.status == "running"
        assert state.error is None
        assert state.checkpoint == {}

    def test_to_dict_serialization(self):
        """Test to_dict converts state to dictionary."""
        state = WorkflowState(
            user_request={"query": "test"},
            workflow_type="knowledge_query",
            step_count=1,
        )
        state_dict = state.to_dict()

        assert isinstance(state_dict, dict)
        assert state_dict["user_request"] == {"query": "test"}
        assert state_dict["workflow_type"] == "knowledge_query"
        assert state_dict["step_count"] == 1
        assert state_dict["status"] == "running"

    def test_from_dict_deserialization(self):
        """Test from_dict reconstructs state from dictionary."""
        data = {
            "user_request": {"query": "test"},
            "workflow_type": "job_search",
            "step_count": 2,
            "status": "complete",
        }
        state = WorkflowState.from_dict(data)

        assert state.user_request == {"query": "test"}
        assert state.workflow_type == "job_search"
        assert state.step_count == 2
        assert state.status == "complete"

    def test_roundtrip_serialization(self):
        """Test to_dict -> from_dict roundtrip preserves state."""
        original = WorkflowState(
            user_request={"query": "test"},
            workflow_type="trading",
            step_count=3,
            context={"key": "value"},
            status="complete",
        )

        # Roundtrip
        state_dict = original.to_dict()
        restored = WorkflowState.from_dict(state_dict)

        assert restored.user_request == original.user_request
        assert restored.workflow_type == original.workflow_type
        assert restored.step_count == original.step_count
        assert restored.context == original.context
        assert restored.status == original.status

    def test_status_transitions(self):
        """Test status can transition through running -> complete -> error."""
        state = WorkflowState(user_request={"test": "data"})
        assert state.status == "running"

        # Update to complete
        state_dict = state.to_dict()
        state_dict["status"] = "complete"
        state = WorkflowState.from_dict(state_dict)
        assert state.status == "complete"

        # Update to error
        state_dict = state.to_dict()
        state_dict["status"] = "error"
        state_dict["error"] = "Test error"
        state = WorkflowState.from_dict(state_dict)
        assert state.status == "error"
        assert state.error == "Test error"

    def test_execution_history_append(self):
        """Test execution_history accumulates step results."""
        state = WorkflowState(user_request={"test": "data"})
        state_dict = state.to_dict()
        state_dict["execution_history"].append(
            {"step": 1, "agent": "RouterAgent", "result": "job_search"}
        )
        state = WorkflowState.from_dict(state_dict)

        assert len(state.execution_history) == 1
        assert state.execution_history[0]["agent"] == "RouterAgent"


class TestEMyBrainScaffold:
    """Tests for EMyBrain engine initialization and scaffold."""

    def test_brain_instantiation(self):
        """Test EMyBrain initializes without db or memory_store."""
        brain = EMyBrain()
        assert brain.db is None
        assert brain.memory_store is None

    def test_brain_instantiation_with_db(self):
        """Test EMyBrain accepts optional db parameter."""
        mock_db = object()  # Placeholder
        brain = EMyBrain(db=mock_db)
        assert brain.db is mock_db

    def test_graph_compiled(self):
        """Test EMyBrain compiles graph successfully."""
        brain = EMyBrain()
        assert brain._graph is not None
        # Graph should have invoke method (compiled CompiledGraph)
        assert hasattr(brain._graph, "invoke")

    def test_router_node_increments_step_count(self):
        """Test router node increments step_count."""
        brain = EMyBrain()
        initial_state = {"step_count": 5}
        updated = brain._router_node(initial_state)
        assert updated["step_count"] == 6

    def test_router_node_handles_missing_step_count(self):
        """Test router node defaults step_count to 0 if missing."""
        brain = EMyBrain()
        initial_state = {}
        updated = brain._router_node(initial_state)
        assert updated["step_count"] == 1

    @pytest.mark.asyncio
    async def test_execute_workflow_returns_dict(self):
        """Test execute_workflow returns dict with required fields."""
        brain = EMyBrain()
        result = await brain.execute_workflow(
            workflow_id="wf_test_001",
            request={"query": "test query"},
        )

        assert isinstance(result, dict)
        assert "workflow_id" in result
        assert "status" in result
        assert "workflow_type" in result
        assert "output" in result
        assert "steps" in result

    @pytest.mark.asyncio
    async def test_execute_workflow_returns_pending_state(self):
        """Test execute_workflow returns with status complete (scaffold default)."""
        brain = EMyBrain()
        result = await brain.execute_workflow(
            workflow_id="wf_scaffold_test",
            request={"test": "data"},
        )

        assert result["workflow_id"] == "wf_scaffold_test"
        assert result["status"] == "complete"
        assert result["workflow_type"] == "unknown"  # Default scaffold type
        assert result["steps"] >= 1

    @pytest.mark.asyncio
    async def test_execute_workflow_error_handling(self):
        """Test execute_workflow returns error status on exception."""
        brain = EMyBrain()

        # Mock graph to raise exception
        async def mock_invoke_error(state):
            raise ValueError("Test graph error")

        brain._graph.invoke = mock_invoke_error

        result = await brain.execute_workflow(
            workflow_id="wf_error_test",
            request={"query": "test"},
        )

        assert result["status"] == "error"
        assert result["workflow_id"] == "wf_error_test"
        assert "error" in result

    @pytest.mark.asyncio
    async def test_execute_workflow_preserves_request(self):
        """Test execute_workflow includes original request in execution."""
        brain = EMyBrain()
        request = {"query": "find jobs", "location": "Toronto"}
        result = await brain.execute_workflow(
            workflow_id="wf_req_test",
            request=request,
        )

        # Result should indicate workflow executed
        assert result["workflow_id"] == "wf_req_test"
        assert result["steps"] >= 1
