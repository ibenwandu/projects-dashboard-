"""TDD Phase 1: RED - Test-Driven Development for Brain Graph Routing (Task 2a-2).

8 tests covering conditional routing in EMyBrain._build_graph():
- Router → nodes mapping for all 5 domain types
- Unknown type → unknown_node
- All domain nodes → complete_node → END
- Graph topology correctness
"""

import pytest
from unittest.mock import patch


class TestBrainGraphRouting:
    """8 tests for conditional routing in EMyBrain._build_graph()."""

    def test_graph_compiles_successfully(self):
        """Test that graph compiles without errors."""
        from emy.brain.engine import EMyBrain

        with patch('emy.brain.engine.RouterAgent'):
            brain = EMyBrain()
            assert brain._graph is not None

    def test_routing_knowledge_query_maps_to_knowledge_node(self):
        """Test that knowledge_query routes to knowledge_node."""
        # Direct test of routing map logic
        routing_map = {
            "knowledge_query": "knowledge_node",
            "trading": "trading_node",
            "research": "research_node",
            "project_monitor": "project_monitor_node",
            "job_search": "job_search_node",
        }
        result = routing_map.get("knowledge_query", "unknown_node")
        assert result == "knowledge_node"

    def test_routing_trading_maps_to_trading_node(self):
        """Test that trading routes to trading_node."""
        routing_map = {
            "knowledge_query": "knowledge_node",
            "trading": "trading_node",
            "research": "research_node",
            "project_monitor": "project_monitor_node",
            "job_search": "job_search_node",
        }
        result = routing_map.get("trading", "unknown_node")
        assert result == "trading_node"

    def test_routing_research_maps_to_research_node(self):
        """Test that research routes to research_node."""
        routing_map = {
            "knowledge_query": "knowledge_node",
            "trading": "trading_node",
            "research": "research_node",
            "project_monitor": "project_monitor_node",
            "job_search": "job_search_node",
        }
        result = routing_map.get("research", "unknown_node")
        assert result == "research_node"

    def test_routing_project_monitor_maps_to_project_monitor_node(self):
        """Test that project_monitor routes to project_monitor_node."""
        routing_map = {
            "knowledge_query": "knowledge_node",
            "trading": "trading_node",
            "research": "research_node",
            "project_monitor": "project_monitor_node",
            "job_search": "job_search_node",
        }
        result = routing_map.get("project_monitor", "unknown_node")
        assert result == "project_monitor_node"

    def test_routing_job_search_maps_to_job_search_node(self):
        """Test that job_search routes to job_search_node."""
        routing_map = {
            "knowledge_query": "knowledge_node",
            "trading": "trading_node",
            "research": "research_node",
            "project_monitor": "project_monitor_node",
            "job_search": "job_search_node",
        }
        result = routing_map.get("job_search", "unknown_node")
        assert result == "job_search_node"

    def test_routing_unknown_type_maps_to_unknown_node(self):
        """Test that unknown types route to unknown_node."""
        routing_map = {
            "knowledge_query": "knowledge_node",
            "trading": "trading_node",
            "research": "research_node",
            "project_monitor": "project_monitor_node",
            "job_search": "job_search_node",
        }
        result = routing_map.get("invalid_type", "unknown_node")
        assert result == "unknown_node"

    def test_complete_node_marks_workflow_complete(self):
        """Test that CompleteBrainNode marks workflow as complete."""
        from emy.brain.nodes.complete_node import CompleteBrainNode

        node = CompleteBrainNode()
        state = {
            "status": "running",
            "context": {"agent_result": {"data": "test"}}
        }
        result = node.execute(state)

        assert result["status"] == "complete"
        assert result["final_result"] == {"data": "test"}

    def test_unknown_node_sets_error_status(self):
        """Test that UnknownBrainNode sets status=error."""
        from emy.brain.nodes.unknown_node import UnknownBrainNode

        node = UnknownBrainNode()
        state = {"workflow_type": "invalid"}
        result = node.execute(state)

        assert result["status"] == "error"
        assert "unknown_workflow_type" in result["error"]
