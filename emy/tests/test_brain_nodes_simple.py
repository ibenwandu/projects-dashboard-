"""TDD Phase 1: RED - Test-Driven Development for Brain Nodes (Task 2a-1).

18 tests covering:
- KnowledgeBrainNode (4)
- TradingBrainNode (4)
- ResearchBrainNode (4)
- ProjectMonitorBrainNode (4)
- CompleteBrainNode (1)
- UnknownBrainNode (1)
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestKnowledgeBrainNode:
    """4 tests for KnowledgeBrainNode adapter."""

    def test_instantiation(self):
        """Test that KnowledgeBrainNode can be instantiated."""
        from emy.brain.nodes.knowledge_node import KnowledgeBrainNode
        node = KnowledgeBrainNode()
        assert node is not None

    def test_success_path_increments_step_count(self):
        """Test that successful execution increments step_count."""
        from emy.brain.nodes.knowledge_node import KnowledgeBrainNode

        with patch('emy.brain.nodes.knowledge_node.KnowledgeAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"response": "test data"})
            mock_agent_class.return_value = mock_agent

            node = KnowledgeBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert result["step_count"] == 1

    def test_success_path_appends_execution_history(self):
        """Test that execution_history is appended with agent name and success."""
        from emy.brain.nodes.knowledge_node import KnowledgeBrainNode

        with patch('emy.brain.nodes.knowledge_node.KnowledgeAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"response": "test data"})
            mock_agent_class.return_value = mock_agent

            node = KnowledgeBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert len(result["execution_history"]) == 1
            assert result["execution_history"][0]["agent"] == "KnowledgeAgent"
            assert result["execution_history"][0]["success"] is True
            assert result["execution_history"][0]["step"] == 1

    def test_failure_path_does_not_propagate(self):
        """Test that agent exceptions are caught and error captured in result."""
        from emy.brain.nodes.knowledge_node import KnowledgeBrainNode

        with patch('emy.brain.nodes.knowledge_node.KnowledgeAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = Exception("test error")
            mock_agent_class.return_value = mock_agent

            node = KnowledgeBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            # Should not raise, should capture error
            assert result["step_count"] == 1
            assert result["context"]["agent_result"]["error"] == "test error"


class TestTradingBrainNode:
    """4 tests for TradingBrainNode adapter."""

    def test_instantiation(self):
        """Test that TradingBrainNode can be instantiated."""
        from emy.brain.nodes.trading_node import TradingBrainNode
        node = TradingBrainNode()
        assert node is not None

    def test_success_path_increments_step_count(self):
        """Test that successful execution increments step_count."""
        from emy.brain.nodes.trading_node import TradingBrainNode

        with patch('emy.brain.nodes.trading_node.TradingAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"analysis": "test"})
            mock_agent_class.return_value = mock_agent

            node = TradingBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert result["step_count"] == 1

    def test_success_path_appends_execution_history(self):
        """Test that execution_history is appended with agent name and success."""
        from emy.brain.nodes.trading_node import TradingBrainNode

        with patch('emy.brain.nodes.trading_node.TradingAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"analysis": "test"})
            mock_agent_class.return_value = mock_agent

            node = TradingBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert len(result["execution_history"]) == 1
            assert result["execution_history"][0]["agent"] == "TradingAgent"
            assert result["execution_history"][0]["success"] is True

    def test_failure_path_does_not_propagate(self):
        """Test that agent exceptions are caught and error captured."""
        from emy.brain.nodes.trading_node import TradingBrainNode

        with patch('emy.brain.nodes.trading_node.TradingAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = Exception("trading error")
            mock_agent_class.return_value = mock_agent

            node = TradingBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert result["context"]["agent_result"]["error"] == "trading error"


class TestResearchBrainNode:
    """4 tests for ResearchBrainNode adapter."""

    def test_instantiation(self):
        """Test that ResearchBrainNode can be instantiated."""
        from emy.brain.nodes.research_node import ResearchBrainNode
        node = ResearchBrainNode()
        assert node is not None

    def test_success_path_increments_step_count(self):
        """Test that successful execution increments step_count."""
        from emy.brain.nodes.research_node import ResearchBrainNode

        with patch('emy.brain.nodes.research_node.ResearchAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"feasibility_score": 0.8})
            mock_agent_class.return_value = mock_agent

            node = ResearchBrainNode()
            state = {"step_count": 0, "execution_history": [], "user_request": {"project_name": "test"}}
            result = node.execute(state)

            assert result["step_count"] == 1

    def test_extracts_project_name_from_user_request(self):
        """Test that project_name is extracted from user_request and passed to agent."""
        from emy.brain.nodes.research_node import ResearchBrainNode

        with patch('emy.brain.nodes.research_node.ResearchAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"feasibility_score": 0.8})
            mock_agent_class.return_value = mock_agent

            node = ResearchBrainNode()
            state = {"step_count": 0, "execution_history": [], "user_request": {"project_name": "test_project"}}
            result = node.execute(state)

            mock_agent.run.assert_called_once_with(project_name="test_project")

    def test_failure_path_does_not_propagate(self):
        """Test that agent exceptions are caught and error captured."""
        from emy.brain.nodes.research_node import ResearchBrainNode

        with patch('emy.brain.nodes.research_node.ResearchAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = Exception("research error")
            mock_agent_class.return_value = mock_agent

            node = ResearchBrainNode()
            state = {"step_count": 0, "execution_history": [], "user_request": {"project_name": "test"}}
            result = node.execute(state)

            assert result["context"]["agent_result"]["error"] == "research error"


class TestProjectMonitorBrainNode:
    """4 tests for ProjectMonitorBrainNode adapter."""

    def test_instantiation(self):
        """Test that ProjectMonitorBrainNode can be instantiated."""
        from emy.brain.nodes.project_monitor_node import ProjectMonitorBrainNode
        node = ProjectMonitorBrainNode()
        assert node is not None

    def test_success_path_increments_step_count(self):
        """Test that successful execution increments step_count."""
        from emy.brain.nodes.project_monitor_node import ProjectMonitorBrainNode

        with patch('emy.brain.nodes.project_monitor_node.ProjectMonitorAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"all_healthy": True})
            mock_agent_class.return_value = mock_agent

            node = ProjectMonitorBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert result["step_count"] == 1

    def test_success_path_appends_execution_history(self):
        """Test that execution_history is appended with agent name and success."""
        from emy.brain.nodes.project_monitor_node import ProjectMonitorBrainNode

        with patch('emy.brain.nodes.project_monitor_node.ProjectMonitorAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = (True, {"all_healthy": True})
            mock_agent_class.return_value = mock_agent

            node = ProjectMonitorBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert len(result["execution_history"]) == 1
            assert result["execution_history"][0]["agent"] == "ProjectMonitorAgent"

    def test_failure_path_does_not_propagate(self):
        """Test that agent exceptions are caught and error captured."""
        from emy.brain.nodes.project_monitor_node import ProjectMonitorBrainNode

        with patch('emy.brain.nodes.project_monitor_node.ProjectMonitorAgent') as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.side_effect = Exception("monitor error")
            mock_agent_class.return_value = mock_agent

            node = ProjectMonitorBrainNode()
            state = {"step_count": 0, "execution_history": []}
            result = node.execute(state)

            assert result["context"]["agent_result"]["error"] == "monitor error"


class TestCompleteBrainNode:
    """1 test for CompleteBrainNode."""

    def test_sets_status_complete_and_final_result(self):
        """Test that CompleteBrainNode sets status=complete and final_result."""
        from emy.brain.nodes.complete_node import CompleteBrainNode

        node = CompleteBrainNode()
        state = {"context": {"agent_result": {"data": "test"}}}
        result = node.execute(state)

        assert result["status"] == "complete"
        assert result["final_result"] == {"data": "test"}


class TestUnknownBrainNode:
    """1 test for UnknownBrainNode."""

    def test_sets_status_error_with_unknown_workflow_type(self):
        """Test that UnknownBrainNode sets status=error with appropriate message."""
        from emy.brain.nodes.unknown_node import UnknownBrainNode

        node = UnknownBrainNode()
        state = {"workflow_type": "invalid_type"}
        result = node.execute(state)

        assert result["status"] == "error"
        assert "unknown_workflow_type" in result["error"]
        assert "invalid_type" in result["error"]
