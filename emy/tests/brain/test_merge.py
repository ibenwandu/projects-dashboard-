import pytest
from emy.brain.merge import merge_agent_results, aggregate_messages, aggregate_agent_outputs


def test_merge_agent_results_from_parallel_execution():
    """Test merging results from multiple agents."""
    base_results = {
        "TradingAgent": {"market_status": "bullish", "confidence": 0.8}
    }

    new_results = {
        "KnowledgeAgent": {"context": "US Fed meeting"},
        "ResearchAgent": {"analysis": "Rate hikes expected"}
    }

    merged = merge_agent_results(base_results, new_results)

    assert "TradingAgent" in merged
    assert "KnowledgeAgent" in merged
    assert "ResearchAgent" in merged
    assert merged["TradingAgent"]["market_status"] == "bullish"
    assert merged["KnowledgeAgent"]["context"] == "US Fed meeting"


def test_aggregate_messages_combines_lists():
    """Test aggregating audit messages from all agents."""
    messages = [
        {"agent": "Router", "message": "Starting workflow"}
    ]

    new_messages = [
        {"agent": "TradingAgent", "message": "Analysis complete"},
        {"agent": "KnowledgeAgent", "message": "Synthesis done"}
    ]

    aggregated = aggregate_messages(messages, new_messages)

    assert len(aggregated) == 3
    assert aggregated[0]["agent"] == "Router"
    assert aggregated[1]["agent"] == "TradingAgent"
    assert aggregated[2]["agent"] == "KnowledgeAgent"


def test_aggregate_agent_outputs_creates_summary():
    """Test creating a summary of all agent outputs."""
    agent_results = {
        "TradingAgent": {"insight": "Market is bullish"},
        "ResearchAgent": {"data": "Volume increasing"},
        "KnowledgeAgent": {"context": "Fed signals"}
    }

    summary = aggregate_agent_outputs(agent_results)

    assert summary["agent_count"] == 3
    assert "TradingAgent" in summary["agents"]
    assert len(summary["insights"]) == 3
    assert summary["insights"][0]["agent"] == "TradingAgent"
    assert summary["insights"][0]["insight"] == "Market is bullish"
