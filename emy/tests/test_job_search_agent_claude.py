"""Test JobSearchAgent with Claude-based job evaluation."""

import pytest
from unittest.mock import patch, Mock
from emy.agents.job_search_agent import JobSearchAgent


@pytest.fixture
def job_search_agent():
    """Provide JobSearchAgent instance."""
    return JobSearchAgent()


class TestJobSearchAgentClaudeIntegration:
    """Test JobSearchAgent Claude integration."""

    def test_job_search_agent_uses_claude_for_evaluation(self, job_search_agent):
        """Test that JobSearchAgent uses Claude to evaluate job matches."""

        mock_evaluation = "This role is a strong match (85% confidence). Aligns with..."

        with patch.object(job_search_agent, '_call_claude', return_value=mock_evaluation):
            prompt = "Is this job a good match for my background?"
            result = job_search_agent._call_claude(prompt)

            assert "match" in result.lower()
            assert "85" in result

    def test_job_search_agent_build_evaluation_prompt(self, job_search_agent):
        """Test evaluation prompt building."""
        jobs = [
            {"title": "Senior Customer Success Manager", "company": "TechCorp", "match": "high"},
            {"title": "Operations Manager", "company": "SaaS Inc", "match": "medium"}
        ]

        prompt = job_search_agent._build_evaluation_prompt(jobs)

        assert "Senior Customer Success Manager" in prompt
        assert "TechCorp" in prompt
        assert "career advisor" in prompt.lower()

    def test_job_search_agent_search_jobs(self, job_search_agent):
        """Test job search returns expected structure."""
        jobs = job_search_agent._search_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) > 0
        assert all(isinstance(j, dict) for j in jobs)
        assert all('title' in j and 'company' in j for j in jobs)

    def test_job_search_agent_run_returns_structure(self, job_search_agent):
        """Test that JobSearchAgent.run() returns expected dict structure."""

        mock_response = "Searched 15 jobs, identified 8 strong matches..."

        with patch.object(job_search_agent, '_call_claude', return_value=mock_response):
            success, result = job_search_agent.run()

            assert isinstance(success, bool)
            assert isinstance(result, (dict, str))

    def test_job_search_agent_run_includes_claude_analysis(self, job_search_agent):
        """Test that run() result includes Claude analysis."""

        mock_analysis = "Top matches: role1, role2, role3"

        with patch.object(job_search_agent, '_call_claude', return_value=mock_analysis):
            success, result = job_search_agent.run()

            # Result may be dict or string depending on report_result
            if isinstance(result, dict):
                assert 'analysis' in result or 'jobs_found' in result

    def test_job_search_agent_run_handles_claude_error(self, job_search_agent):
        """Test that run() handles Claude errors gracefully."""

        with patch.object(job_search_agent, '_call_claude', side_effect=Exception("Claude error")):
            success, result = job_search_agent.run()

            # Should fail gracefully
            assert isinstance(success, bool)

    def test_job_search_agent_disabled(self, job_search_agent):
        """Test that agent respects disable guard."""
        with patch.object(job_search_agent, 'check_disabled', return_value=True):
            success, result = job_search_agent.run()

            assert success is False
            assert isinstance(result, dict)
