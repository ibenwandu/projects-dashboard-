"""TDD Phase 1: RED - Test-Driven Development for JobSearchBrainNode (Task 2a-3).

8 tests covering:
- Instantiation without scrape_fn
- Instantiation with injected scrape_fn
- execute() returns dict with required state keys
- step_count increments
- execution_history has entry
- context["agent_result"] has jobs_found key
- scrape failure gracefully returns jobs_found=0
- custom scrape_fn is called with query string
"""

import pytest
from unittest.mock import MagicMock, patch


class TestJobSearchBrainNode:
    """8 tests for JobSearchBrainNode with Playwright."""

    def test_instantiation_without_scrape_fn(self):
        """Test that JobSearchBrainNode can be instantiated without scrape_fn."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode
        node = JobSearchBrainNode()
        assert node is not None
        assert node._executor is not None

    def test_instantiation_with_injected_scrape_fn(self):
        """Test that JobSearchBrainNode accepts injected scrape_fn."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode

        mock_scrape = MagicMock(return_value=[])
        node = JobSearchBrainNode(scrape_fn=mock_scrape)

        assert node._scrape_fn == mock_scrape

    def test_execute_returns_dict_with_required_keys(self):
        """Test that execute() returns dict with required state keys."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode

        mock_scrape = MagicMock(return_value=[])
        node = JobSearchBrainNode(scrape_fn=mock_scrape)

        state = {"step_count": 0, "execution_history": [], "user_request": {"query": "test"}}
        result = node.execute(state)

        assert "step_count" in result
        assert "execution_history" in result
        assert "context" in result
        assert "current_agent" in result

    def test_step_count_increments(self):
        """Test that step_count is incremented."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode

        mock_scrape = MagicMock(return_value=[])
        node = JobSearchBrainNode(scrape_fn=mock_scrape)

        state = {"step_count": 0, "execution_history": [], "user_request": {"query": "test"}}
        result = node.execute(state)

        assert result["step_count"] == 1

    def test_execution_history_appended(self):
        """Test that execution_history is appended with agent entry."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode

        mock_scrape = MagicMock(return_value=[])
        node = JobSearchBrainNode(scrape_fn=mock_scrape)

        state = {"step_count": 0, "execution_history": [], "user_request": {"query": "test"}}
        result = node.execute(state)

        assert len(result["execution_history"]) == 1
        assert result["execution_history"][0]["agent"] == "JobSearchBrainNode"
        assert result["execution_history"][0]["step"] == 1

    def test_context_agent_result_has_jobs_found_key(self):
        """Test that context["agent_result"] has jobs_found key."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode

        mock_scrape = MagicMock(return_value=[])
        node = JobSearchBrainNode(scrape_fn=mock_scrape)

        state = {"step_count": 0, "execution_history": [], "user_request": {"query": "test"}}
        result = node.execute(state)

        assert "jobs_found" in result["context"]["agent_result"]
        assert result["context"]["agent_result"]["jobs_found"] == 0

    def test_scrape_failure_gracefully_returns_zero_jobs(self):
        """Test that scrape_fn exceptions are caught and jobs_found=0 returned."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode

        mock_scrape = MagicMock(side_effect=Exception("scrape error"))
        node = JobSearchBrainNode(scrape_fn=mock_scrape)

        state = {"step_count": 0, "execution_history": [], "user_request": {"query": "test"}}
        result = node.execute(state)

        # Should not raise, should return jobs_found=0
        assert result["context"]["agent_result"]["jobs_found"] == 0
        assert result["step_count"] == 1

    def test_custom_scrape_fn_called_with_query(self):
        """Test that custom scrape_fn is called with query string."""
        from emy.brain.nodes.job_search_node import JobSearchBrainNode

        mock_scrape = MagicMock(return_value=[{"title": "Engineer", "company": "Acme"}])
        node = JobSearchBrainNode(scrape_fn=mock_scrape)

        state = {
            "step_count": 0,
            "execution_history": [],
            "user_request": {"query": "Software Engineer Toronto"}
        }
        result = node.execute(state)

        mock_scrape.assert_called_once_with("Software Engineer Toronto")
        assert result["context"]["agent_result"]["jobs_found"] == 1
        assert result["context"]["agent_result"]["query"] == "Software Engineer Toronto"
